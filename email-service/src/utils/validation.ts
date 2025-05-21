/**
 * Validation utilities for the Email Service
 * 
 * This module provides functions for validating email formats, document types,
 * attachment sizes, and other input data to ensure data integrity and prevent
 * processing of invalid or malicious content.
 */

import path from 'path';
import { IEmailAttachment } from '../types/email';

// Constants for validation

/**
 * Maximum attachment size in bytes (70MB)
 * Based on common industry standards for email attachments
 */
export const MAX_ATTACHMENT_SIZE = 70 * 1024 * 1024; // 70MB

/**
 * Minimum attachment size in bytes (10 bytes)
 * To prevent empty or corrupted files
 */
export const MIN_ATTACHMENT_SIZE = 10; // 10 bytes

/**
 * Supported document file extensions
 */
export const SUPPORTED_EXTENSIONS = [
  '.pdf',  // PDF documents
  '.tiff', '.tif', // TIFF images
  '.png',  // PNG images
  '.jpg', '.jpeg', // JPEG images
];

/**
 * Supported MIME types for document attachments
 */
export const SUPPORTED_MIME_TYPES = [
  'application/pdf', // PDF
  'image/tiff', // TIFF
  'image/png',  // PNG
  'image/jpeg', // JPEG
];

/**
 * Allowed email domains for processing
 * Can be configured based on business requirements
 */
export const ALLOWED_EMAIL_DOMAINS: string[] = [
  // This can be populated from configuration
  // Default is to accept all domains
];

/**
 * Email regex pattern for basic validation
 * Follows RFC 5322 standard for email validation
 */
export const EMAIL_REGEX = /^[a-zA-Z0-9.!#$%&'*+/=?^_`{|}~-]+@[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(?:\.[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)*$/;

/**
 * Validates if a string is a properly formatted email address
 * @param email - The email address to validate
 * @returns True if the email format is valid, false otherwise
 */
export function validateEmailFormat(email: string): boolean {
  if (!email || typeof email !== 'string') {
    return false;
  }
  
  return EMAIL_REGEX.test(email);
}

/**
 * Validates if an email domain is allowed for processing
 * @param email - The email address to validate
 * @returns True if the email domain is allowed or if no restrictions are set, false otherwise
 */
export function validateEmailDomain(email: string): boolean {
  if (!validateEmailFormat(email)) {
    return false;
  }
  
  // If no allowed domains are specified, accept all domains
  if (ALLOWED_EMAIL_DOMAINS.length === 0) {
    return true;
  }
  
  const domain = email.split('@')[1].toLowerCase();
  return ALLOWED_EMAIL_DOMAINS.some(allowedDomain => 
    domain === allowedDomain.toLowerCase() || domain.endsWith(`.${allowedDomain.toLowerCase()}`)
  );
}

/**
 * Validates if a file extension is supported
 * @param filename - The filename to validate
 * @returns True if the file extension is supported, false otherwise
 */
export function validateFileExtension(filename: string): boolean {
  if (!filename || typeof filename !== 'string') {
    return false;
  }
  
  const ext = path.extname(filename).toLowerCase();
  return SUPPORTED_EXTENSIONS.includes(ext);
}

/**
 * Validates if a MIME type is supported
 * @param mimeType - The MIME type to validate
 * @returns True if the MIME type is supported, false otherwise
 */
export function validateMimeType(mimeType: string): boolean {
  if (!mimeType || typeof mimeType !== 'string') {
    return false;
  }
  
  return SUPPORTED_MIME_TYPES.some(supportedType => 
    mimeType.toLowerCase() === supportedType.toLowerCase() || 
    mimeType.toLowerCase().startsWith(`${supportedType.toLowerCase()};`)
  );
}

/**
 * Validates if an attachment size is within acceptable limits
 * @param size - The size of the attachment in bytes
 * @returns True if the size is within limits, false otherwise
 */
export function validateAttachmentSize(size: number): boolean {
  return size >= MIN_ATTACHMENT_SIZE && size <= MAX_ATTACHMENT_SIZE;
}

/**
 * Comprehensive validation for email attachments
 * Checks file extension, MIME type, and size
 * @param attachment - The email attachment to validate
 * @returns An object with validation result and reason if invalid
 */
export function validateAttachment(attachment: IEmailAttachment): { 
  isValid: boolean; 
  reason?: string;
} {
  // Check if attachment exists
  if (!attachment) {
    return { isValid: false, reason: 'Attachment is undefined or null' };
  }

  // Check file extension
  if (!validateFileExtension(attachment.filename)) {
    return { 
      isValid: false, 
      reason: `Unsupported file extension. Supported types: ${SUPPORTED_EXTENSIONS.join(', ')}` 
    };
  }

  // Check MIME type
  if (!validateMimeType(attachment.contentType)) {
    return { 
      isValid: false, 
      reason: `Unsupported MIME type: ${attachment.contentType}. Supported types: ${SUPPORTED_MIME_TYPES.join(', ')}` 
    };
  }

  // Check file size
  if (!validateAttachmentSize(attachment.size)) {
    if (attachment.size < MIN_ATTACHMENT_SIZE) {
      return { 
        isValid: false, 
        reason: `Attachment size too small: ${attachment.size} bytes. Minimum size: ${MIN_ATTACHMENT_SIZE} bytes` 
      };
    } else {
      return { 
        isValid: false, 
        reason: `Attachment size too large: ${attachment.size} bytes. Maximum size: ${MAX_ATTACHMENT_SIZE} bytes` 
      };
    }
  }

  return { isValid: true };
}

/**
 * Comprehensive validation for email addresses
 * Checks format and domain restrictions
 * @param email - The email address to validate
 * @returns An object with validation result and reason if invalid
 */
export function validateEmail(email: string): { 
  isValid: boolean; 
  reason?: string;
} {
  // Check email format
  if (!validateEmailFormat(email)) {
    return { 
      isValid: false, 
      reason: 'Invalid email format' 
    };
  }

  // Check email domain
  if (!validateEmailDomain(email)) {
    return { 
      isValid: false, 
      reason: `Email domain not allowed. Allowed domains: ${ALLOWED_EMAIL_DOMAINS.length > 0 ? ALLOWED_EMAIL_DOMAINS.join(', ') : 'All domains (no restrictions)'}` 
    };
  }

  return { isValid: true };
}

/**
 * Validates if a string contains potentially malicious content
 * This is a basic implementation that should be enhanced with more sophisticated checks
 * @param content - The string content to validate
 * @returns True if the content appears safe, false if potentially malicious
 */
export function validateContentSafety(content: string): boolean {
  if (!content || typeof content !== 'string') {
    return false;
  }
  
  // Check for common script injection patterns
  const suspiciousPatterns = [
    /<script[^>]*>[\s\S]*?<\/script>/i,
    /javascript:/i,
    /eval\s*\(/i,
    /on\w+\s*=/i,
    /\bdata:(?:text\/html|application\/javascript)/i
  ];
  
  return !suspiciousPatterns.some(pattern => pattern.test(content));
}

/**
 * Validates if a subject line contains spam indicators
 * @param subject - The email subject to validate
 * @returns True if the subject appears legitimate, false if it contains spam indicators
 */
export function validateSubjectForSpam(subject: string): boolean {
  if (!subject || typeof subject !== 'string') {
    return true; // Empty subjects are allowed
  }
  
  // Common spam subject patterns
  const spamPatterns = [
    /\b(?:viagra|cialis|\$\$\$|\bfree money\b|\bwin \$|\bcasino\b|\blottery\b|\bprize\b.*\bwon\b)/i,
    /^(?:Re:|Fwd:)\s*(?:Re:|Fwd:)\s*(?:Re:|Fwd:)/i, // Excessive Re: or Fwd: prefixes
    /^\s*(?:urgent|important)\s*:/i, // Subjects starting with "urgent:" or "important:"
    /[!$*]{3,}/  // Multiple exclamation marks or dollar signs
  ];
  
  return !spamPatterns.some(pattern => pattern.test(subject));
}

/**
 * Checks if an email appears to be an auto-reply or out-of-office message
 * @param subject - The email subject
 * @param headers - Optional email headers
 * @returns True if the email appears to be an auto-reply, false otherwise
 */
export function isAutoReply(subject: string, headers?: Record<string, string>): boolean {
  if (!subject) {
    return false;
  }
  
  // Common auto-reply subject patterns
  const autoReplySubjectPatterns = [
    /^\s*(?:out\s*of\s*office|ooo|auto\s*reply|automatic\s*reply|away\s*from\s*office)/i,
    /^\s*(?:vacation\s*(?:response|reply)|thank\s*you\s*for\s*your\s*email)/i
  ];
  
  // Check subject patterns
  if (autoReplySubjectPatterns.some(pattern => pattern.test(subject))) {
    return true;
  }
  
  // Check headers if provided
  if (headers) {
    // Common auto-reply headers
    const autoReplyHeaders = [
      'auto-submitted',
      'x-auto-response-suppress',
      'x-autorespond',
      'x-autoreply'
    ];
    
    for (const header of autoReplyHeaders) {
      if (headers[header] && 
          headers[header].toLowerCase() !== 'no') {
        return true;
      }
    }
  }
  
  return false;
}

/**
 * Validates if an email sender is from a trusted domain
 * @param senderEmail - The sender's email address
 * @param trustedDomains - Array of trusted domains
 * @returns True if the sender is from a trusted domain, false otherwise
 */
export function isTrustedSender(senderEmail: string, trustedDomains: string[] = []): boolean {
  if (!validateEmailFormat(senderEmail)) {
    return false;
  }
  
  // If no trusted domains are specified, return false (require explicit trust)
  if (trustedDomains.length === 0) {
    return false;
  }
  
  const domain = senderEmail.split('@')[1].toLowerCase();
  return trustedDomains.some(trustedDomain => 
    domain === trustedDomain.toLowerCase() || domain.endsWith(`.${trustedDomain.toLowerCase()}`)
  );
}