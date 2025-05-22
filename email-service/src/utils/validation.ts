/**
 * Email Service Validation Utilities
 * 
 * This module provides validation functions for email formats, document types,
 * attachment sizes, and other input data to ensure data integrity and prevent
 * processing of invalid or malicious content.
 */

/**
 * Maximum allowed attachment size in bytes
 * Default: 10MB (10 * 1024 * 1024 bytes)
 */
export const MAX_ATTACHMENT_SIZE = 10 * 1024 * 1024; // 10MB

/**
 * Supported document MIME types
 */
export const SUPPORTED_MIME_TYPES = [
  'application/pdf',           // PDF
  'image/tiff',                // TIFF
  'image/png',                 // PNG
  'image/jpeg',                // JPEG/JPG
];

/**
 * Supported document file extensions
 */
export const SUPPORTED_FILE_EXTENSIONS = [
  '.pdf',
  '.tiff',
  '.tif',
  '.png',
  '.jpg',
  '.jpeg',
];

/**
 * Potentially dangerous file extensions that should be blocked
 */
export const DANGEROUS_FILE_EXTENSIONS = [
  '.exe', '.bat', '.cmd', '.com', '.js', '.jse', '.vbs', '.vbe', '.wsf', '.wsh',
  '.msc', '.msi', '.msp', '.scr', '.hta', '.jar', '.ps1', '.reg', '.dll', '.pif'
];

/**
 * Regular expression for validating email format
 * This regex follows RFC 5322 standards for email validation
 */
export const EMAIL_REGEX = /^(?=.{1,254}$)(?=.{1,64}@)[-!#$%&'*+/0-9=?A-Z^_`a-z{|}~]+(\.[-!#$%&'*+/0-9=?A-Z^_`a-z{|}~]+)*@[A-Za-z0-9]([A-Za-z0-9-]{0,61}[A-Za-z0-9])?(\.[A-Za-z0-9]([A-Za-z0-9-]{0,61}[A-Za-z0-9])?)*$/;

/**
 * Validates an email address format
 * 
 * @param email - The email address to validate
 * @returns True if the email format is valid, false otherwise
 */
export function isValidEmailFormat(email: string): boolean {
  if (!email || typeof email !== 'string') {
    return false;
  }
  
  return EMAIL_REGEX.test(email);
}

/**
 * Validates an email domain
 * 
 * @param email - The email address to validate the domain for
 * @param allowedDomains - Optional array of allowed domains
 * @returns True if the domain is valid, false otherwise
 */
export function isValidEmailDomain(email: string, allowedDomains?: string[]): boolean {
  if (!isValidEmailFormat(email)) {
    return false;
  }
  
  const domain = email.split('@')[1].toLowerCase();
  
  // If allowedDomains is provided, check if the domain is in the list
  if (allowedDomains && allowedDomains.length > 0) {
    return allowedDomains.some(allowedDomain => 
      domain === allowedDomain.toLowerCase() || domain.endsWith(`.${allowedDomain.toLowerCase()}`)
    );
  }
  
  // Basic domain validation - must have at least one dot and valid TLD
  const parts = domain.split('.');
  if (parts.length < 2) {
    return false;
  }
  
  // Check if the TLD is at least 2 characters
  const tld = parts[parts.length - 1];
  return tld.length >= 2;
}

/**
 * Gets the MIME type from a file extension
 * 
 * @param extension - The file extension (with or without leading dot)
 * @returns The corresponding MIME type or null if not recognized
 */
export function getMimeTypeFromExtension(extension: string): string | null {
  // Ensure extension has a leading dot
  const ext = extension.startsWith('.') ? extension.toLowerCase() : `.${extension.toLowerCase()}`;
  
  const mimeTypeMap: Record<string, string> = {
    '.pdf': 'application/pdf',
    '.tiff': 'image/tiff',
    '.tif': 'image/tiff',
    '.png': 'image/png',
    '.jpg': 'image/jpeg',
    '.jpeg': 'image/jpeg'
  };
  
  return mimeTypeMap[ext] || null;
}

/**
 * Gets the file extension from a MIME type
 * 
 * @param mimeType - The MIME type
 * @returns The corresponding file extension (with leading dot) or null if not recognized
 */
export function getExtensionFromMimeType(mimeType: string): string | null {
  const mimeToExtMap: Record<string, string> = {
    'application/pdf': '.pdf',
    'image/tiff': '.tiff',
    'image/png': '.png',
    'image/jpeg': '.jpg'
  };
  
  return mimeToExtMap[mimeType.toLowerCase()] || null;
}

/**
 * Validates if a file's MIME type is supported
 * 
 * @param mimeType - The MIME type to validate
 * @returns True if the MIME type is supported, false otherwise
 */
export function isValidMimeType(mimeType: string): boolean {
  return SUPPORTED_MIME_TYPES.includes(mimeType.toLowerCase());
}

/**
 * Validates if a file extension is supported
 * 
 * @param filename - The filename or extension to validate
 * @returns True if the file extension is supported, false otherwise
 */
export function isValidFileExtension(filename: string): boolean {
  const extension = filename.includes('.') 
    ? `.${filename.split('.').pop()?.toLowerCase()}` 
    : `.${filename.toLowerCase()}`;
  
  return SUPPORTED_FILE_EXTENSIONS.includes(extension);
}

/**
 * Checks if a file extension is potentially dangerous
 * 
 * @param filename - The filename or extension to check
 * @returns True if the file extension is potentially dangerous, false otherwise
 */
export function isDangerousFileExtension(filename: string): boolean {
  const extension = filename.includes('.') 
    ? `.${filename.split('.').pop()?.toLowerCase()}` 
    : `.${filename.toLowerCase()}`;
  
  return DANGEROUS_FILE_EXTENSIONS.includes(extension);
}

/**
 * Validates if a file size is within the allowed limit
 * 
 * @param fileSize - The file size in bytes
 * @param maxSize - Optional maximum size in bytes (defaults to MAX_ATTACHMENT_SIZE)
 * @returns True if the file size is valid, false otherwise
 */
export function isValidFileSize(fileSize: number, maxSize: number = MAX_ATTACHMENT_SIZE): boolean {
  return fileSize > 0 && fileSize <= maxSize;
}

/**
 * Formats a file size in bytes to a human-readable string
 * 
 * @param bytes - The file size in bytes
 * @param decimals - Number of decimal places (default: 2)
 * @returns A human-readable string representation of the file size
 */
export function formatFileSize(bytes: number, decimals: number = 2): string {
  if (bytes === 0) return '0 Bytes';
  
  const k = 1024;
  const dm = decimals < 0 ? 0 : decimals;
  const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB'];
  
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  
  return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + ' ' + sizes[i];
}

/**
 * Validates if a file name contains suspicious patterns
 * 
 * @param filename - The filename to validate
 * @returns True if the filename is suspicious, false otherwise
 */
export function hasSuspiciousFilename(filename: string): boolean {
  // Check for double extensions which might be used to disguise file types
  // e.g., malicious.jpg.exe might appear as an image but is actually executable
  const parts = filename.split('.');
  if (parts.length > 2) {
    const lastExt = `.${parts.pop()?.toLowerCase()}`;
    if (DANGEROUS_FILE_EXTENSIONS.includes(lastExt)) {
      return true;
    }
  }
  
  // Check for unusual characters in filename
  const suspiciousChars = /[\\\/<>:"\|\?\*]/;
  if (suspiciousChars.test(filename)) {
    return true;
  }
  
  // Check for very long filenames which might be used to obfuscate the extension
  if (filename.length > 255) {
    return true;
  }
  
  return false;
}

/**
 * Comprehensive file validation
 * Checks file size, extension, MIME type, and suspicious patterns
 * 
 * @param filename - The name of the file
 * @param fileSize - The size of the file in bytes
 * @param mimeType - The MIME type of the file
 * @returns An object with validation result and error message if invalid
 */
export function validateFile(
  filename: string, 
  fileSize: number, 
  mimeType: string
): { valid: boolean; error?: string } {
  // Check file size
  if (!isValidFileSize(fileSize)) {
    return { 
      valid: false, 
      error: `File size exceeds the maximum allowed size of ${formatFileSize(MAX_ATTACHMENT_SIZE)}.` 
    };
  }
  
  // Check for dangerous file extensions
  if (isDangerousFileExtension(filename)) {
    return { 
      valid: false, 
      error: 'File type is not allowed due to security restrictions.' 
    };
  }
  
  // Check for suspicious filename patterns
  if (hasSuspiciousFilename(filename)) {
    return { 
      valid: false, 
      error: 'File name contains suspicious patterns and has been rejected.' 
    };
  }
  
  // Check if file extension is supported
  if (!isValidFileExtension(filename)) {
    return { 
      valid: false, 
      error: `Unsupported file type. Allowed types: ${SUPPORTED_FILE_EXTENSIONS.join(', ')}.` 
    };
  }
  
  // Check if MIME type is supported
  if (!isValidMimeType(mimeType)) {
    return { 
      valid: false, 
      error: `Unsupported MIME type. Allowed types: ${SUPPORTED_MIME_TYPES.join(', ')}.` 
    };
  }
  
  // Check if file extension matches the MIME type
  const extension = filename.includes('.') 
    ? `.${filename.split('.').pop()?.toLowerCase()}` 
    : `.${filename.toLowerCase()}`;
  
  const expectedMimeType = getMimeTypeFromExtension(extension);
  if (expectedMimeType && expectedMimeType.toLowerCase() !== mimeType.toLowerCase()) {
    return { 
      valid: false, 
      error: 'File extension does not match the actual file content type.' 
    };
  }
  
  return { valid: true };
}

/**
 * Validates an email message for processing
 * 
 * @param from - The sender's email address
 * @param subject - The email subject
 * @param hasAttachments - Whether the email has attachments
 * @param allowedDomains - Optional array of allowed sender domains
 * @returns An object with validation result and error message if invalid
 */
export function validateEmailMessage(
  from: string,
  subject: string,
  hasAttachments: boolean,
  allowedDomains?: string[]
): { valid: boolean; error?: string } {
  // Validate sender email format
  if (!isValidEmailFormat(from)) {
    return {
      valid: false,
      error: 'Invalid sender email format.'
    };
  }
  
  // Validate sender domain if allowedDomains is provided
  if (allowedDomains && !isValidEmailDomain(from, allowedDomains)) {
    return {
      valid: false,
      error: 'Email from unauthorized domain.'
    };
  }
  
  // Check if subject exists
  if (!subject || subject.trim() === '') {
    return {
      valid: false,
      error: 'Email subject cannot be empty.'
    };
  }
  
  // Check if email has attachments (if required)
  if (!hasAttachments) {
    return {
      valid: false,
      error: 'Email must contain at least one attachment.'
    };
  }
  
  return { valid: true };
}