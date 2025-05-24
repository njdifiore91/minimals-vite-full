import { Request, Response, NextFunction } from 'express';
import jwt from 'jsonwebtoken';
import fs from 'fs';
import path from 'path';
import { promisify } from 'util';

// Define interfaces for the middleware
export interface JwtPayload {
  sub: string;
  roles: string[];
  exp: number;
  iat: number;
  iss: string;
  aud: string;
}

export interface AuthOptions {
  /**
   * Array of roles that are allowed to access the route
   */
  allowedRoles?: string[];
  
  /**
   * Path to the directory containing public keys for JWT verification
   * Keys should be named in the format: public_key_1.pem, public_key_2.pem, etc.
   */
  publicKeyDir?: string;
  
  /**
   * Whether to skip authentication for this route
   */
  skipAuth?: boolean;
  
  /**
   * Custom error messages
   */
  errorMessages?: {
    missingToken?: string;
    invalidToken?: string;
    expiredToken?: string;
    insufficientPermissions?: string;
  };
}

// Default configuration
const DEFAULT_OPTIONS: AuthOptions = {
  allowedRoles: [],
  publicKeyDir: process.env.JWT_PUBLIC_KEY_DIR || path.join(process.cwd(), 'keys'),
  skipAuth: false,
  errorMessages: {
    missingToken: 'Authentication token is missing',
    invalidToken: 'Invalid authentication token',
    expiredToken: 'Authentication token has expired',
    insufficientPermissions: 'Insufficient permissions to access this resource',
  },
};

// Define role constants
export const ROLES = {
  OPERATIONS_STAFF: 'operations_staff',
  SYSTEM_ADMIN: 'system_admin',
};

/**
 * Loads all public keys from the specified directory
 * @param keyDir Directory containing public keys
 * @returns Map of key IDs to public keys
 */
async function loadPublicKeys(keyDir: string): Promise<Map<string, string>> {
  const readdir = promisify(fs.readdir);
  const readFile = promisify(fs.readFile);
  const keys = new Map<string, string>();
  
  try {
    const files = await readdir(keyDir);
    const keyFiles = files.filter(file => file.startsWith('public_key_') && file.endsWith('.pem'));
    
    for (const file of keyFiles) {
      const keyId = file.replace('public_key_', '').replace('.pem', '');
      const keyPath = path.join(keyDir, file);
      const keyContent = await readFile(keyPath, 'utf8');
      keys.set(keyId, keyContent);
    }
    
    return keys;
  } catch (error) {
    console.error('Error loading public keys:', error);
    throw new Error('Failed to load JWT public keys');
  }
}

/**
 * Extracts the JWT token from the request
 * @param req Express request object
 * @returns JWT token or null if not found
 */
function extractToken(req: Request): string | null {
  if (req.headers.authorization && req.headers.authorization.startsWith('Bearer ')) {
    return req.headers.authorization.substring(7);
  }
  return null;
}

/**
 * Verifies the JWT token using the appropriate public key
 * @param token JWT token
 * @param publicKeys Map of key IDs to public keys
 * @returns Decoded JWT payload
 */
async function verifyToken(token: string, publicKeys: Map<string, string>): Promise<JwtPayload> {
  // Extract the key ID from the token header
  const decoded = jwt.decode(token, { complete: true });
  if (!decoded || typeof decoded === 'string' || !decoded.header) {
    throw new Error('Invalid token format');
  }
  
  const keyId = decoded.header.kid || '1'; // Default to key ID 1 if not specified
  const publicKey = publicKeys.get(keyId);
  
  if (!publicKey) {
    throw new Error(`Public key with ID ${keyId} not found`);
  }
  
  try {
    // Verify the token using the appropriate public key
    const verifyAsync = promisify<string, string, jwt.VerifyOptions, JwtPayload>(jwt.verify as any);
    const payload = await verifyAsync(token, publicKey, {
      algorithms: ['RS256'], // Only allow RS256 algorithm
      issuer: process.env.JWT_ISSUER || 'dollarfunding.com',
      audience: process.env.JWT_AUDIENCE || 'mca-application',
    });
    
    return payload;
  } catch (error) {
    if (error instanceof jwt.TokenExpiredError) {
      throw new Error('Token expired');
    } else if (error instanceof jwt.JsonWebTokenError) {
      throw new Error('Invalid token');
    } else {
      throw error;
    }
  }
}

/**
 * Checks if the user has the required roles
 * @param userRoles User's roles from the JWT payload
 * @param allowedRoles Roles allowed to access the resource
 * @returns True if the user has at least one of the allowed roles
 */
function hasRequiredRoles(userRoles: string[], allowedRoles: string[]): boolean {
  // If no roles are required, allow access
  if (!allowedRoles || allowedRoles.length === 0) {
    return true;
  }
  
  // System Admin role has access to everything
  if (userRoles.includes(ROLES.SYSTEM_ADMIN)) {
    return true;
  }
  
  // Check if the user has at least one of the allowed roles
  return userRoles.some(role => allowedRoles.includes(role));
}

/**
 * Creates an authentication middleware with the specified options
 * @param options Authentication options
 * @returns Express middleware function
 */
export function createAuthMiddleware(options: AuthOptions = {}) {
  // Merge options with defaults
  const config: AuthOptions = { ...DEFAULT_OPTIONS, ...options };
  
  // Initialize public keys cache
  let publicKeysPromise: Promise<Map<string, string>> | null = null;
  let lastKeyLoadTime = 0;
  const KEY_CACHE_TTL = 3600000; // 1 hour in milliseconds
  
  /**
   * Gets the public keys, loading them if necessary
   * @returns Map of key IDs to public keys
   */
  async function getPublicKeys(): Promise<Map<string, string>> {
    const now = Date.now();
    
    // Load keys if they haven't been loaded yet or if the cache has expired
    if (!publicKeysPromise || now - lastKeyLoadTime > KEY_CACHE_TTL) {
      lastKeyLoadTime = now;
      publicKeysPromise = loadPublicKeys(config.publicKeyDir!);
    }
    
    return publicKeysPromise;
  }
  
  // Return the middleware function
  return async (req: Request, res: Response, next: NextFunction) => {
    try {
      // Skip authentication if configured to do so
      if (config.skipAuth) {
        return next();
      }
      
      // Extract the token from the request
      const token = extractToken(req);
      if (!token) {
        return res.status(401).json({
          error: 'Unauthorized',
          message: config.errorMessages?.missingToken || DEFAULT_OPTIONS.errorMessages!.missingToken,
          code: 'AUTH_MISSING_TOKEN',
        });
      }
      
      // Get the public keys
      const publicKeys = await getPublicKeys();
      
      // Verify the token
      let payload: JwtPayload;
      try {
        payload = await verifyToken(token, publicKeys);
      } catch (error: any) {
        if (error.message === 'Token expired') {
          return res.status(401).json({
            error: 'Unauthorized',
            message: config.errorMessages?.expiredToken || DEFAULT_OPTIONS.errorMessages!.expiredToken,
            code: 'AUTH_EXPIRED_TOKEN',
          });
        } else {
          return res.status(401).json({
            error: 'Unauthorized',
            message: config.errorMessages?.invalidToken || DEFAULT_OPTIONS.errorMessages!.invalidToken,
            code: 'AUTH_INVALID_TOKEN',
          });
        }
      }
      
      // Check if the token has expired
      const now = Math.floor(Date.now() / 1000);
      if (payload.exp && payload.exp < now) {
        return res.status(401).json({
          error: 'Unauthorized',
          message: config.errorMessages?.expiredToken || DEFAULT_OPTIONS.errorMessages!.expiredToken,
          code: 'AUTH_EXPIRED_TOKEN',
        });
      }
      
      // Check if the user has the required roles
      if (!hasRequiredRoles(payload.roles, config.allowedRoles || [])) {
        return res.status(403).json({
          error: 'Forbidden',
          message: config.errorMessages?.insufficientPermissions || DEFAULT_OPTIONS.errorMessages!.insufficientPermissions,
          code: 'AUTH_INSUFFICIENT_PERMISSIONS',
        });
      }
      
      // Attach the user information to the request for use in route handlers
      (req as any).user = {
        id: payload.sub,
        roles: payload.roles,
      };
      
      // Continue to the next middleware or route handler
      next();
    } catch (error) {
      // Handle unexpected errors
      console.error('Authentication middleware error:', error);
      res.status(500).json({
        error: 'Internal Server Error',
        message: 'An unexpected error occurred during authentication',
        code: 'AUTH_INTERNAL_ERROR',
      });
    }
  };
}

/**
 * Middleware that requires the user to have the Operations Staff role
 */
export const requireOperationsStaff = createAuthMiddleware({
  allowedRoles: [ROLES.OPERATIONS_STAFF, ROLES.SYSTEM_ADMIN],
});

/**
 * Middleware that requires the user to have the System Admin role
 */
export const requireSystemAdmin = createAuthMiddleware({
  allowedRoles: [ROLES.SYSTEM_ADMIN],
});

/**
 * Middleware that requires authentication but doesn't check roles
 */
export const requireAuth = createAuthMiddleware();

// Export default middleware factory
export default createAuthMiddleware;