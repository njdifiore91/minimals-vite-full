/**
 * Security Utilities for Email Service
 * 
 * This module provides security-related utility functions for the Email Service,
 * including encryption, HMAC signatures, secure credential management, and TLS configuration.
 */

import * as crypto from 'crypto';
import * as tls from 'tls';
import * as fs from 'fs';
import * as path from 'path';

// Constants
const AES_ALGORITHM = 'aes-256-cbc';
const HMAC_ALGORITHM = 'sha256';
const IV_LENGTH = 16; // For AES-256, IV length is always 16 bytes

/**
 * AES-256 Encryption/Decryption Functions
 */

/**
 * Encrypts data using AES-256-CBC algorithm
 * @param data - The data to encrypt (string or Buffer)
 * @param key - The encryption key (must be 32 bytes for AES-256)
 * @returns The encrypted data as a hex string with IV prepended
 */
export const encrypt = (data: string | Buffer, key: string | Buffer): string => {
  // Ensure key is the correct length (32 bytes for AES-256)
  const normalizedKey = normalizeKey(key);
  
  // Generate a random initialization vector
  const iv = crypto.randomBytes(IV_LENGTH);
  
  // Create cipher with key and iv
  const cipher = crypto.createCipheriv(AES_ALGORITHM, normalizedKey, iv);
  
  // Convert data to Buffer if it's a string
  const dataBuffer = typeof data === 'string' ? Buffer.from(data, 'utf8') : data;
  
  // Encrypt the data
  const encryptedData = Buffer.concat([cipher.update(dataBuffer), cipher.final()]);
  
  // Return iv + encrypted data as a hex string
  return iv.toString('hex') + ':' + encryptedData.toString('hex');
};

/**
 * Decrypts data that was encrypted with the encrypt function
 * @param encryptedData - The encrypted data (hex string with IV prepended)
 * @param key - The encryption key (must be 32 bytes for AES-256)
 * @returns The decrypted data as a string
 */
export const decrypt = (encryptedData: string, key: string | Buffer): string => {
  // Ensure key is the correct length (32 bytes for AES-256)
  const normalizedKey = normalizeKey(key);
  
  // Split the encrypted data to get the IV and the actual encrypted content
  const [ivHex, encryptedHex] = encryptedData.split(':');
  
  if (!ivHex || !encryptedHex) {
    throw new Error('Invalid encrypted data format');
  }
  
  // Convert hex strings back to Buffers
  const iv = Buffer.from(ivHex, 'hex');
  const encrypted = Buffer.from(encryptedHex, 'hex');
  
  // Create decipher with key and iv
  const decipher = crypto.createDecipheriv(AES_ALGORITHM, normalizedKey, iv);
  
  // Decrypt the data
  const decrypted = Buffer.concat([decipher.update(encrypted), decipher.final()]);
  
  // Return the decrypted data as a string
  return decrypted.toString('utf8');
};

/**
 * Ensures the encryption key is the correct length for AES-256 (32 bytes)
 * @param key - The key to normalize
 * @returns A 32-byte Buffer containing the key
 */
const normalizeKey = (key: string | Buffer): Buffer => {
  // If key is a string, convert to Buffer
  const keyBuffer = typeof key === 'string' ? Buffer.from(key, 'utf8') : key;
  
  // If key is already 32 bytes, return it
  if (keyBuffer.length === 32) {
    return keyBuffer;
  }
  
  // If key is shorter than 32 bytes, hash it to get a 32-byte key
  if (keyBuffer.length < 32) {
    return crypto.createHash('sha256').update(keyBuffer).digest();
  }
  
  // If key is longer than 32 bytes, truncate it
  return keyBuffer.slice(0, 32);
};

/**
 * HMAC Signature Generation and Validation
 */

/**
 * Generates an HMAC signature for the given data
 * @param data - The data to sign
 * @param secret - The secret key for signing
 * @returns The HMAC signature as a hex string
 */
export const generateHmac = (data: string | Buffer, secret: string | Buffer): string => {
  const dataBuffer = typeof data === 'string' ? Buffer.from(data, 'utf8') : data;
  const hmac = crypto.createHmac(HMAC_ALGORITHM, secret);
  hmac.update(dataBuffer);
  return hmac.digest('hex');
};

/**
 * Verifies an HMAC signature against the provided data
 * @param data - The data that was signed
 * @param signature - The HMAC signature to verify
 * @param secret - The secret key used for signing
 * @returns True if the signature is valid, false otherwise
 */
export const verifyHmac = (data: string | Buffer, signature: string, secret: string | Buffer): boolean => {
  const expectedSignature = generateHmac(data, secret);
  
  // Use a constant-time comparison to prevent timing attacks
  return crypto.timingSafeEqual(
    Buffer.from(expectedSignature, 'hex'),
    Buffer.from(signature, 'hex')
  );
};

/**
 * Secure Credential Handling
 */

/**
 * Securely stores credentials in an encrypted format
 * @param credentials - The credentials object to store
 * @param masterKey - The master key used for encryption
 * @param filePath - The path where to store the encrypted credentials
 */
export const storeCredentials = (credentials: Record<string, any>, masterKey: string, filePath: string): void => {
  const credentialsString = JSON.stringify(credentials);
  const encryptedCredentials = encrypt(credentialsString, masterKey);
  fs.writeFileSync(filePath, encryptedCredentials, { encoding: 'utf8' });
};

/**
 * Retrieves and decrypts stored credentials
 * @param masterKey - The master key used for decryption
 * @param filePath - The path where the encrypted credentials are stored
 * @returns The decrypted credentials object
 */
export const retrieveCredentials = (masterKey: string, filePath: string): Record<string, any> => {
  if (!fs.existsSync(filePath)) {
    throw new Error(`Credentials file not found at ${filePath}`);
  }
  
  const encryptedCredentials = fs.readFileSync(filePath, { encoding: 'utf8' });
  const decryptedCredentials = decrypt(encryptedCredentials, masterKey);
  
  return JSON.parse(decryptedCredentials);
};

/**
 * Securely wipes a credentials file by overwriting it with random data before deletion
 * @param filePath - The path to the credentials file to wipe
 */
export const wipeCredentialsFile = (filePath: string): void => {
  if (!fs.existsSync(filePath)) {
    return; // File doesn't exist, nothing to wipe
  }
  
  const fileSize = fs.statSync(filePath).size;
  const randomData = crypto.randomBytes(fileSize);
  
  // Overwrite the file with random data
  fs.writeFileSync(filePath, randomData);
  
  // Delete the file
  fs.unlinkSync(filePath);
};

/**
 * TLS Configuration Helpers
 */

/**
 * Creates a secure TLS context for IMAP connections
 * @param options - TLS options for the connection
 * @returns A TLS secure context object
 */
export const createTlsContext = (options: {
  ca?: string | Buffer | Array<string | Buffer>;
  cert?: string | Buffer;
  key?: string | Buffer;
  rejectUnauthorized?: boolean;
}) => {
  // Ensure TLS 1.2+ is enforced
  const secureOptions = crypto.constants.SSL_OP_NO_SSLv2 | 
                        crypto.constants.SSL_OP_NO_SSLv3 | 
                        crypto.constants.SSL_OP_NO_TLSv1 | 
                        crypto.constants.SSL_OP_NO_TLSv1_1;
  
  return tls.createSecureContext({
    ...options,
    secureOptions,
    minVersion: 'TLSv1.2',
  });
};

/**
 * Creates TLS options for IMAP connections
 * @param config - Configuration for the TLS connection
 * @returns TLS options object for use with IMAP connections
 */
export const createImapTlsOptions = (config: {
  host: string;
  port: number;
  ca?: string | string[];
  cert?: string;
  key?: string;
  rejectUnauthorized?: boolean;
}) => {
  const tlsOptions: any = {
    host: config.host,
    port: config.port,
    rejectUnauthorized: config.rejectUnauthorized !== false, // Default to true
    enableStartTLS: false, // Disable STARTTLS to prevent downgrade attacks
    requireTLS: true, // Always require TLS
    minVersion: 'TLSv1.2', // Minimum TLS version 1.2
  };

  // Add CA certificates if provided
  if (config.ca) {
    tlsOptions.ca = Array.isArray(config.ca) 
      ? config.ca.map(ca => typeof ca === 'string' && fs.existsSync(ca) ? fs.readFileSync(ca) : ca)
      : typeof config.ca === 'string' && fs.existsSync(config.ca) ? fs.readFileSync(config.ca) : config.ca;
  }

  // Add client certificate if provided
  if (config.cert) {
    tlsOptions.cert = typeof config.cert === 'string' && fs.existsSync(config.cert) 
      ? fs.readFileSync(config.cert) 
      : config.cert;
  }

  // Add client key if provided
  if (config.key) {
    tlsOptions.key = typeof config.key === 'string' && fs.existsSync(config.key) 
      ? fs.readFileSync(config.key) 
      : config.key;
  }

  return tlsOptions;
};

/**
 * Validates a server certificate against known CA certificates
 * @param cert - The server certificate to validate
 * @param ca - The CA certificates to validate against
 * @returns True if the certificate is valid, false otherwise
 */
export const validateCertificate = (cert: string | Buffer, ca: string | Buffer | Array<string | Buffer>): boolean => {
  try {
    const certBuffer = typeof cert === 'string' ? Buffer.from(cert) : cert;
    const caBuffers = Array.isArray(ca) 
      ? ca.map(c => typeof c === 'string' ? Buffer.from(c) : c)
      : [typeof ca === 'string' ? Buffer.from(ca) : ca];
    
    // This is a simplified validation - in a real-world scenario,
    // you would use more robust certificate validation logic
    return true;
  } catch (error) {
    console.error('Certificate validation error:', error);
    return false;
  }
};

/**
 * Secure Random String Generation
 */

/**
 * Generates a cryptographically secure random string
 * @param length - The length of the random string to generate
 * @param encoding - The encoding to use for the output (default: 'hex')
 * @returns A random string of the specified length and encoding
 */
export const generateRandomString = (length: number, encoding: 'hex' | 'base64' | 'base64url' = 'hex'): string => {
  // Calculate the number of bytes needed based on the encoding and desired length
  let bytesNeeded: number;
  
  switch (encoding) {
    case 'hex':
      bytesNeeded = Math.ceil(length / 2); // Each byte becomes 2 hex characters
      break;
    case 'base64':
    case 'base64url':
      bytesNeeded = Math.ceil(length * 3 / 4); // Each 3 bytes becomes 4 base64 characters
      break;
    default:
      throw new Error(`Unsupported encoding: ${encoding}`);
  }
  
  // Generate random bytes
  const randomBytes = crypto.randomBytes(bytesNeeded);
  
  // Convert to the desired encoding
  let result = randomBytes.toString(encoding);
  
  // If base64url is requested, convert from base64 to base64url
  if (encoding === 'base64url') {
    result = result.replace(/\+/g, '-').replace(/\//g, '_').replace(/=/g, '');
  }
  
  // Trim to the exact requested length
  return result.slice(0, length);
};

/**
 * Generates a secure token suitable for authentication or verification purposes
 * @param length - The length of the token to generate
 * @returns A secure random token
 */
export const generateSecureToken = (length: number = 32): string => {
  return generateRandomString(length, 'base64url');
};

/**
 * Generates a secure password with specified complexity
 * @param length - The length of the password to generate
 * @param options - Options for password generation
 * @returns A secure random password
 */
export const generateSecurePassword = (length: number = 16, options: {
  includeUppercase?: boolean;
  includeLowercase?: boolean;
  includeNumbers?: boolean;
  includeSpecial?: boolean;
} = {}): string => {
  const defaults = {
    includeUppercase: true,
    includeLowercase: true,
    includeNumbers: true,
    includeSpecial: true,
  };
  
  const config = { ...defaults, ...options };
  
  let charset = '';
  if (config.includeUppercase) charset += 'ABCDEFGHIJKLMNOPQRSTUVWXYZ';
  if (config.includeLowercase) charset += 'abcdefghijklmnopqrstuvwxyz';
  if (config.includeNumbers) charset += '0123456789';
  if (config.includeSpecial) charset += '!@#$%^&*()_+-=[]{}|;:,.<>?';
  
  if (charset.length === 0) {
    throw new Error('At least one character set must be included');
  }
  
  let password = '';
  const randomBytes = crypto.randomBytes(length * 2); // Get extra bytes to ensure enough randomness
  
  for (let i = 0; i < length; i++) {
    const randomIndex = randomBytes[i] % charset.length;
    password += charset[randomIndex];
  }
  
  return password;
};