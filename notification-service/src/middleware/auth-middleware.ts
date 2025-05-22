import { Request, Response, NextFunction } from 'express';
import jwt from 'jsonwebtoken';
import fs from 'fs';
import path from 'path';
import { promisify } from 'util';

// Define interfaces for the middleware
interface JwtPayload {
  sub: string;
  role: string;
  exp: number;
  iat: number;
  iss?: string;
  aud?: string;
  [key: string]: any;
}

interface AuthMiddlewareOptions {
  /** Array of roles allowed to access the route */
  roles?: string[];
  /** Path to the directory containing public keys */
  publicKeyDir?: string;
  /** Whether authentication is required (defaults to true) */
  credentialsRequired?: boolean;
  /** Name of the property in the request object where the payload is set */
  requestProperty?: string;
  /** JWT issuer to validate */
  issuer?: string;
  /** JWT audience to validate */
  audience?: string;
  /** JWT algorithm to use (defaults to RS256) */
  algorithms?: string[];
}

// Extend Express Request interface to include auth property
declare global {
  namespace Express {
    interface Request {
      auth?: JwtPayload;
    }
  }
}

/**
 * Error class for authentication errors
 */
class AuthenticationError extends Error {
  statusCode: number;
  code: string;

  constructor(message: string, statusCode: number = 401, code: string = 'authentication_error') {
    super(message);
    this.name = 'AuthenticationError';
    this.statusCode = statusCode;
    this.code = code;
  }
}

/**
 * Loads all public keys from the specified directory
 * @param publicKeyDir Directory containing public key files
 * @returns Array of public keys
 */
async function loadPublicKeys(publicKeyDir: string): Promise<string[]> {
  try {
    const readdir = promisify(fs.readdir);
    const readFile = promisify(fs.readFile);
    
    const files = await readdir(publicKeyDir);
    const keyFiles = files.filter(file => file.endsWith('.pub') || file.endsWith('.pem'));
    
    const keys = await Promise.all(
      keyFiles.map(async (file) => {
        const keyPath = path.join(publicKeyDir, file);
        return readFile(keyPath, 'utf8');
      })
    );
    
    if (keys.length === 0) {
      throw new Error('No public keys found in directory');
    }
    
    return keys;
  } catch (error) {
    console.error('Error loading public keys:', error);
    throw new Error('Failed to load public keys');
  }
}

/**
 * Verifies a JWT token with multiple public keys
 * @param token JWT token to verify
 * @param publicKeys Array of public keys to try
 * @param options Verification options
 * @returns Decoded token payload
 */
async function verifyTokenWithKeys(
  token: string,
  publicKeys: string[],
  options: jwt.VerifyOptions
): Promise<JwtPayload> {
  const verify = promisify<string, string, jwt.VerifyOptions, any>(jwt.verify);
  
  // Try each public key until one works or all fail
  let lastError: Error | null = null;
  
  for (const publicKey of publicKeys) {
    try {
      const decoded = await verify(token, publicKey, options);
      return decoded as JwtPayload;
    } catch (error) {
      lastError = error as Error;
      // Continue to the next key if this one failed
    }
  }
  
  // If we get here, all keys failed
  if (lastError) {
    if (lastError.name === 'TokenExpiredError') {
      throw new AuthenticationError('Token expired', 401, 'token_expired');
    } else if (lastError.name === 'JsonWebTokenError') {
      throw new AuthenticationError('Invalid token', 401, 'invalid_token');
    } else if (lastError.name === 'NotBeforeError') {
      throw new AuthenticationError('Token not active', 401, 'token_not_active');
    }
    throw new AuthenticationError(lastError.message, 401, 'token_verification_error');
  }
  
  throw new AuthenticationError('Token verification failed', 401, 'token_verification_error');
}

/**
 * Extracts the token from the request
 * @param req Express request object
 * @returns JWT token string or null if not found
 */
function getTokenFromRequest(req: Request): string | null {
  if (req.headers.authorization && req.headers.authorization.split(' ')[0] === 'Bearer') {
    return req.headers.authorization.split(' ')[1];
  }
  
  if (req.query && req.query.token) {
    return req.query.token as string;
  }
  
  return null;
}

/**
 * Validates if the user has the required role
 * @param userRole User's role from the token
 * @param requiredRoles Array of roles allowed to access the route
 * @returns True if the user has permission, false otherwise
 */
function validateRole(userRole: string, requiredRoles?: string[]): boolean {
  if (!requiredRoles || requiredRoles.length === 0) {
    return true; // No role requirements
  }
  
  // System Admin has access to everything
  if (userRole === 'System Admin') {
    return true;
  }
  
  return requiredRoles.includes(userRole);
}

/**
 * Creates an authentication middleware for Express
 * @param options Authentication middleware options
 * @returns Express middleware function
 */
export function createAuthMiddleware(options: AuthMiddlewareOptions = {}) {
  const {
    roles,
    publicKeyDir = process.env.JWT_PUBLIC_KEY_DIR || path.resolve(__dirname, '../../config/jwt-keys'),
    credentialsRequired = true,
    requestProperty = 'auth',
    issuer = process.env.JWT_ISSUER,
    audience = process.env.JWT_AUDIENCE,
    algorithms = ['RS256'],
  } = options;
  
  // Load public keys once when middleware is created
  let publicKeysPromise: Promise<string[]>;
  
  return async (req: Request, res: Response, next: NextFunction) => {
    try {
      // Initialize public keys if not already done
      if (!publicKeysPromise) {
        publicKeysPromise = loadPublicKeys(publicKeyDir);
      }
      
      // Get the token from the request
      const token = getTokenFromRequest(req);
      
      // If no token is provided
      if (!token) {
        if (credentialsRequired) {
          throw new AuthenticationError('No authorization token was found', 401, 'credentials_required');
        } else {
          return next();
        }
      }
      
      // Load public keys
      const publicKeys = await publicKeysPromise;
      
      // Verify the token
      const decoded = await verifyTokenWithKeys(token, publicKeys, {
        algorithms,
        issuer,
        audience,
      });
      
      // Check if the token has the required role
      if (!validateRole(decoded.role, roles)) {
        throw new AuthenticationError('Insufficient permissions', 403, 'insufficient_permissions');
      }
      
      // Set the decoded token on the request object
      (req as any)[requestProperty] = decoded;
      
      next();
    } catch (error) {
      if (error instanceof AuthenticationError) {
        return res.status(error.statusCode).json({
          error: {
            code: error.code,
            message: error.message,
          },
        });
      }
      
      // For unexpected errors
      console.error('Authentication middleware error:', error);
      return res.status(500).json({
        error: {
          code: 'internal_server_error',
          message: 'An internal server error occurred',
        },
      });
    }
  };
}

/**
 * Middleware for routes that require Operations Staff role
 */
export const requireOperationsStaff = createAuthMiddleware({
  roles: ['Operations Staff', 'System Admin'],
});

/**
 * Middleware for routes that require System Admin role
 */
export const requireSystemAdmin = createAuthMiddleware({
  roles: ['System Admin'],
});

/**
 * Middleware that requires authentication but no specific role
 */
export const requireAuth = createAuthMiddleware();

/**
 * Default export for the auth middleware factory function
 */
export default createAuthMiddleware;