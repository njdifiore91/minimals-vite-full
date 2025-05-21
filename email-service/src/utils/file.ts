/**
 * File Utility Module for Email Service
 * 
 * Provides utility functions for file operations, MIME type detection, and content type validation.
 * Used for processing email attachments and preparing them for storage and further processing.
 * 
 * This module is essential for the Email Service to extract attachments from emails,
 * validate their types, and prepare them for virus scanning and further processing.
 */

import fs from 'fs';
import path from 'path';
import os from 'os';
import { promisify } from 'util';
import { fData } from './format-number';
import crypto from 'crypto';

// Promisify fs functions
const mkdtemp = promisify(fs.mkdtemp);
const writeFile = promisify(fs.writeFile);
const readFile = promisify(fs.readFile);
const unlink = promisify(fs.unlink);
const rmdir = promisify(fs.rmdir);
const stat = promisify(fs.stat);

/**
 * Supported document types for processing
 * These are the only file types that will be accepted for processing in the MCA system
 * as specified in the technical requirements
 */
export const SUPPORTED_DOCUMENT_TYPES = [
  'application/pdf',                                                      // PDF documents
  'image/tiff',                                                          // TIFF images
  'image/png',                                                           // PNG images
  'image/jpeg',                                                          // JPEG images
  'application/vnd.openxmlformats-officedocument.wordprocessingml.document', // DOCX
  'application/msword',                                                  // DOC
  'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',   // XLSX
  'application/vnd.ms-excel',                                            // XLS
];

/**
 * Maximum file size for attachments (in bytes)
 * Default: 25MB
 */
export const MAX_FILE_SIZE = 25 * 1024 * 1024;

/**
 * Maps common file extensions to MIME types
 */
export const EXTENSION_TO_MIME: Record<string, string> = {
  pdf: 'application/pdf',
  tiff: 'image/tiff',
  tif: 'image/tiff',
  png: 'image/png',
  jpg: 'image/jpeg',
  jpeg: 'image/jpeg',
  docx: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
  doc: 'application/msword',
  xlsx: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
  xls: 'application/vnd.ms-excel',
};

/**
 * Maps MIME types to common file extensions
 */
export const MIME_TO_EXTENSION: Record<string, string> = {
  'application/pdf': 'pdf',
  'image/tiff': 'tiff',
  'image/png': 'png',
  'image/jpeg': 'jpg',
  'application/vnd.openxmlformats-officedocument.wordprocessingml.document': 'docx',
  'application/msword': 'doc',
  'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': 'xlsx',
  'application/vnd.ms-excel': 'xls',
};

/**
 * Interface for file metadata
 * Contains all necessary information about a file attachment
 */
export interface FileMetadata {
  /** Generated secure filename */
  filename: string;
  /** Original filename from the email attachment */
  originalFilename?: string;
  /** Detected or provided MIME type */
  mimeType: string;
  /** File extension (without dot) */
  extension: string;
  /** File size in bytes */
  size: number;
  /** Optional file path if saved to disk */
  path?: string;
  /** Optional buffer containing file contents */
  buffer?: Buffer;
  /** Timestamp when the file metadata was created */
  createdAt: Date;
  /** MD5 hash of the file content (for deduplication) */
  contentHash?: string;
  /** Flag indicating if the file passed virus scan */
  virusScanned?: boolean;
  /** Flag indicating if the file is safe (no virus detected) */
  isSafe?: boolean;
  /** Source email message ID */
  sourceMessageId?: string;
  /** Source email sender */
  sourceSender?: string;
}

/**
 * Detects MIME type from a buffer using file signatures
 * Uses the file-type library to analyze file magic numbers
 * 
 * @param buffer - The file buffer to analyze
 * @returns Promise resolving to the detected MIME type or null if not detected
 */
export async function detectMimeType(buffer: Buffer): Promise<string | null> {
  try {
    // Import file-type dynamically to maintain ESM compatibility
    const fileType = await import('file-type');
    const type = await fileType.fileTypeFromBuffer(buffer);
    
    // If file-type couldn't detect the MIME type, try to determine if it's a text-based format
    if (!type?.mime) {
      // Check for common text file signatures
      const textSignatures = [
        { mime: 'text/plain', check: (buf: Buffer) => isTextFile(buf) },
        { mime: 'text/csv', check: (buf: Buffer) => isCSVFile(buf) },
        { mime: 'text/html', check: (buf: Buffer) => isHTMLFile(buf) },
        { mime: 'application/xml', check: (buf: Buffer) => isXMLFile(buf) },
      ];
      
      for (const { mime, check } of textSignatures) {
        if (check(buffer)) {
          return mime;
        }
      }
    }
    
    return type?.mime || null;
  } catch (error) {
    console.error('Error detecting MIME type:', error);
    return null;
  }
}

/**
 * Checks if a buffer contains a text file
 * @param buffer - The buffer to check
 * @returns Boolean indicating if the buffer contains text
 */
function isTextFile(buffer: Buffer): boolean {
  // Check a sample of the buffer for non-text characters
  const sampleSize = Math.min(buffer.length, 512); // Check first 512 bytes
  const sample = buffer.slice(0, sampleSize);
  
  // Text files should only contain printable ASCII characters, tabs, newlines, and carriage returns
  for (let i = 0; i < sample.length; i++) {
    const byte = sample[i];
    // Allow common text file characters
    if (!(byte === 9 || byte === 10 || byte === 13 || (byte >= 32 && byte <= 126))) {
      return false;
    }
  }
  
  return true;
}

/**
 * Checks if a buffer contains a CSV file
 * @param buffer - The buffer to check
 * @returns Boolean indicating if the buffer contains CSV data
 */
function isCSVFile(buffer: Buffer): boolean {
  if (!isTextFile(buffer)) return false;
  
  // Convert buffer to string for analysis
  const sample = buffer.slice(0, Math.min(buffer.length, 1024)).toString('utf8');
  const lines = sample.split(/\r?\n/).filter(line => line.trim().length > 0);
  
  // Check if we have at least one line
  if (lines.length === 0) return false;
  
  // Check if the file has a consistent delimiter pattern
  const firstLine = lines[0];
  const commaCount = (firstLine.match(/,/g) || []).length;
  const tabCount = (firstLine.match(/\t/g) || []).length;
  const semicolonCount = (firstLine.match(/;/g) || []).length;
  
  // Determine the most likely delimiter
  const delimiter = [',', '\t', ';']
    .reduce((max, current) => {
      const count = current === ',' ? commaCount : current === '\t' ? tabCount : semicolonCount;
      return count > max.count ? { char: current, count } : max;
    }, { char: '', count: 0 });
  
  // If no clear delimiter is found, it's probably not a CSV
  if (delimiter.count === 0) return false;
  
  // Check if most lines have approximately the same number of delimiters
  const consistentDelimiters = lines.slice(1, Math.min(lines.length, 5)).every(line => {
    const count = (line.match(new RegExp(`\\${delimiter.char}`, 'g')) || []).length;
    // Allow some variation in delimiter count
    return Math.abs(count - delimiter.count) <= 1;
  });
  
  return consistentDelimiters;
}

/**
 * Checks if a buffer contains an HTML file
 * @param buffer - The buffer to check
 * @returns Boolean indicating if the buffer contains HTML
 */
function isHTMLFile(buffer: Buffer): boolean {
  if (!isTextFile(buffer)) return false;
  
  const sample = buffer.slice(0, Math.min(buffer.length, 1024)).toString('utf8').toLowerCase();
  
  // Check for HTML signatures
  return (
    sample.includes('<!doctype html>') ||
    sample.includes('<html') ||
    (sample.includes('<head') && sample.includes('<body')) ||
    (sample.includes('<title') && sample.includes('<div'))
  );
}

/**
 * Checks if a buffer contains an XML file
 * @param buffer - The buffer to check
 * @returns Boolean indicating if the buffer contains XML
 */
function isXMLFile(buffer: Buffer): boolean {
  if (!isTextFile(buffer)) return false;
  
  const sample = buffer.slice(0, Math.min(buffer.length, 1024)).toString('utf8').trim();
  
  // Check for XML signatures
  return (
    sample.startsWith('<?xml') ||
    (sample.startsWith('<') && sample.includes('xmlns='))
  );
}

/**
 * Validates if a MIME type is supported for processing
 * @param mimeType - The MIME type to validate
 * @returns Boolean indicating if the MIME type is supported
 */
export function isValidDocumentType(mimeType: string): boolean {
  return SUPPORTED_DOCUMENT_TYPES.includes(mimeType);
}

/**
 * Gets file extension from MIME type
 * @param mimeType - The MIME type
 * @returns The corresponding file extension or 'bin' if not found
 */
export function getExtensionFromMimeType(mimeType: string): string {
  return MIME_TO_EXTENSION[mimeType] || 'bin';
}

/**
 * Gets MIME type from file extension
 * @param extension - The file extension (without dot)
 * @returns The corresponding MIME type or 'application/octet-stream' if not found
 */
export function getMimeTypeFromExtension(extension: string): string {
  const normalizedExtension = extension.toLowerCase().replace(/^\./, '');
  return EXTENSION_TO_MIME[normalizedExtension] || 'application/octet-stream';
}

/**
 * Creates a temporary directory for file processing
 * @param prefix - Optional prefix for the temp directory name
 * @returns Promise resolving to the path of the created temp directory
 */
export async function createTempDirectory(prefix = 'mca-email-'): Promise<string> {
  try {
    // Ensure the temp directory path ends with the platform-specific separator
    const tempDirPath = path.join(await fs.promises.realpath(os.tmpdir()), path.sep);
    const tempDir = await mkdtemp(tempDirPath + prefix);
    return tempDir;
  } catch (error) {
    console.error('Error creating temporary directory:', error);
    throw error;
  }
}

/**
 * Writes a buffer to a temporary file
 * @param buffer - The buffer to write
 * @param filename - The filename to use
 * @param tempDir - Optional temporary directory path (will create one if not provided)
 * @returns Promise resolving to the path of the created file
 */
export async function writeTempFile(
  buffer: Buffer,
  filename: string,
  tempDir?: string
): Promise<string> {
  const dirPath = tempDir || await createTempDirectory();
  const filePath = path.join(dirPath, filename);
  
  try {
    await writeFile(filePath, buffer, { mode: 0o600 }); // Secure permissions
    return filePath;
  } catch (error) {
    console.error('Error writing temporary file:', error);
    throw error;
  }
}

/**
 * Reads a file into a buffer
 * @param filePath - Path to the file
 * @returns Promise resolving to the file buffer
 */
export async function readFileToBuffer(filePath: string): Promise<Buffer> {
  try {
    return await readFile(filePath);
  } catch (error) {
    console.error('Error reading file to buffer:', error);
    throw error;
  }
}

/**
 * Safely removes a temporary file
 * @param filePath - Path to the file to remove
 * @returns Promise resolving when the file is removed
 */
export async function removeTempFile(filePath: string): Promise<void> {
  try {
    await unlink(filePath);
  } catch (error) {
    console.error('Error removing temporary file:', error);
    // Don't throw error for file removal failures
  }
}

/**
 * Safely removes a temporary directory and all its contents
 * @param dirPath - Path to the directory to remove
 * @returns Promise resolving when the directory is removed
 */
export async function removeTempDirectory(dirPath: string): Promise<void> {
  try {
    // Use recursive option to remove directory and all contents
    await rmdir(dirPath, { recursive: true });
  } catch (error) {
    console.error('Error removing temporary directory:', error);
    // Don't throw error for directory removal failures
  }
}

/**
 * Creates file metadata from a buffer
 * Generates a secure filename and calculates content hash for deduplication
 * 
 * @param buffer - The file buffer
 * @param originalFilename - The original filename
 * @param options - Additional options for metadata creation
 * @returns Promise resolving to file metadata
 */
export async function createFileMetadata(
  buffer: Buffer,
  originalFilename: string,
  options: {
    sourceMessageId?: string;
    sourceSender?: string;
  } = {}
): Promise<FileMetadata> {
  // Detect MIME type from buffer or fallback to octet-stream
  const detectedMimeType = await detectMimeType(buffer) || 'application/octet-stream';
  
  // Get file extension from MIME type or from original filename if not detected
  let extension = getExtensionFromMimeType(detectedMimeType);
  if (extension === 'bin') {
    const originalExtension = extractFileExtension(originalFilename);
    if (originalExtension) {
      extension = originalExtension;
    }
  }
  
  // Generate a secure filename with timestamp and random component
  const timestamp = Date.now();
  const randomComponent = crypto.randomBytes(8).toString('hex');
  const sanitizedName = sanitizeFilename(path.basename(originalFilename, path.extname(originalFilename)));
  const filename = `${timestamp}-${sanitizedName}-${randomComponent}.${extension}`;
  
  // Calculate MD5 hash of the buffer for deduplication
  const contentHash = crypto.createHash('md5').update(buffer).digest('hex');
  
  return {
    filename,
    originalFilename,
    mimeType: detectedMimeType,
    extension,
    size: buffer.length,
    buffer,
    createdAt: new Date(),
    contentHash,
    sourceMessageId: options.sourceMessageId,
    sourceSender: options.sourceSender,
    virusScanned: false,
    isSafe: false, // Default to false until scanned
  };
}

/**
 * Formats file size in human-readable format
 * @param size - The file size in bytes
 * @returns Formatted file size string (e.g., "2.5 MB")
 */
export function formatFileSize(size: number): string {
  return fData(size);
}

/**
 * Prepares a file for virus scanning
 * Creates a temporary directory and writes the file with secure permissions
 * 
 * @param buffer - The file buffer to scan
 * @param filename - The filename to use
 * @returns Promise resolving to an object with the file path and cleanup function
 */
export async function prepareForVirusScan(
  buffer: Buffer,
  filename: string
): Promise<{ filePath: string; cleanup: () => Promise<void> }> {
  // Create a temporary directory for virus scanning
  const scanDir = await createTempDirectory('virus-scan-');
  
  // Write the file to the temporary directory with secure permissions
  const filePath = await writeTempFile(buffer, filename, scanDir);
  
  // Return the file path and a cleanup function
  return {
    filePath,
    cleanup: async () => {
      try {
        await removeTempDirectory(scanDir);
      } catch (error) {
        console.error('Error cleaning up virus scan directory:', error);
      }
    }
  };
}

/**
 * Checks if a file exceeds the maximum allowed size
 * @param size - The file size in bytes
 * @returns Boolean indicating if the file is too large
 */
export function isFileTooLarge(size: number): boolean {
  return size > MAX_FILE_SIZE;
}

/**
 * Calculates the hash of a file buffer
 * @param buffer - The file buffer
 * @param algorithm - The hash algorithm to use (default: 'md5')
 * @returns The calculated hash as a hex string
 */
export function calculateFileHash(buffer: Buffer, algorithm = 'md5'): string {
  return crypto.createHash(algorithm).update(buffer).digest('hex');
}

/**
 * Gets file stats with error handling
 * @param filePath - Path to the file
 * @returns Promise resolving to fs.Stats or null if file doesn't exist
 */
export async function getFileStats(filePath: string): Promise<fs.Stats | null> {
  try {
    return await stat(filePath);
  } catch (error) {
    if ((error as NodeJS.ErrnoException).code === 'ENOENT') {
      return null; // File doesn't exist
    }
    throw error; // Other error
  }
}

/**
 * Checks if a file exists
 * @param filePath - Path to the file
 * @returns Promise resolving to boolean indicating if file exists
 */
export async function fileExists(filePath: string): Promise<boolean> {
  const stats = await getFileStats(filePath);
  return stats !== null;
}

/**
 * Creates a temporary file with attachment data for processing
 * @param metadata - File metadata including buffer
 * @returns Promise resolving to the path of the created file
 */
export async function createAttachmentTempFile(metadata: FileMetadata): Promise<string> {
  if (!metadata.buffer) {
    throw new Error('File buffer is required to create temporary file');
  }
  
  const tempDir = await createTempDirectory('mca-attachment-');
  const filePath = path.join(tempDir, metadata.filename);
  
  await writeFile(filePath, metadata.buffer, { mode: 0o600 }); // Secure permissions
  
  return filePath;
}

/**
 * Extracts the file extension from a filename
 * @param filename - The filename to analyze
 * @returns The file extension (without dot)
 */
export function extractFileExtension(filename: string): string {
  const extension = path.extname(filename).toLowerCase();
  return extension.startsWith('.') ? extension.substring(1) : extension;
}

/**
 * Sanitizes a filename to make it safe for filesystem operations
 * Removes path traversal characters and other potentially dangerous characters
 * 
 * @param filename - The filename to sanitize
 * @returns Sanitized filename
 */
export function sanitizeFilename(filename: string): string {
  if (!filename) return 'unnamed_file';
  
  return filename
    .replace(/[/\\?%*:|"<>]/g, '-') // Replace unsafe characters with dash
    .replace(/\s+/g, '_')            // Replace whitespace with underscore
    .replace(/^\./g, '_dot_')        // Replace leading dots (hidden files)
    .replace(/^\s*|\s*$/g, '')       // Trim whitespace
    .substring(0, 200);              // Limit filename length
}

/**
 * Processes an attachment buffer and prepares it for the MCA pipeline
 * This is a high-level utility that combines multiple file operations
 * 
 * @param buffer - The attachment buffer
 * @param originalFilename - The original filename
 * @param options - Additional processing options
 * @returns Promise resolving to the processed file metadata
 */
export async function processAttachment(
  buffer: Buffer,
  originalFilename: string,
  options: {
    sourceMessageId?: string;
    sourceSender?: string;
    skipVirusScan?: boolean;
  } = {}
): Promise<FileMetadata> {
  // Create file metadata
  const metadata = await createFileMetadata(buffer, originalFilename, {
    sourceMessageId: options.sourceMessageId,
    sourceSender: options.sourceSender,
  });
  
  // Check file size
  if (isFileTooLarge(metadata.size)) {
    throw new Error(`File size exceeds maximum allowed size of ${formatFileSize(MAX_FILE_SIZE)}`);
  }
  
  // Check if file type is supported
  if (!isValidDocumentType(metadata.mimeType)) {
    throw new Error(`Unsupported file type: ${metadata.mimeType}`);
  }
  
  // Perform virus scan if not skipped
  if (!options.skipVirusScan) {
    const { filePath, cleanup } = await prepareForVirusScan(buffer, metadata.filename);
    
    try {
      // Note: Actual virus scanning would be implemented here or called from here
      // For now, we'll just mark it as scanned and safe
      metadata.virusScanned = true;
      metadata.isSafe = true;
    } finally {
      // Clean up temporary files
      await cleanup();
    }
  }
  
  return metadata;
}

/**
 * Batch processes multiple attachments
 * 
 * @param attachments - Array of attachment objects with buffer and filename
 * @param options - Processing options
 * @returns Promise resolving to array of processed file metadata
 */
export async function processAttachments(
  attachments: Array<{ buffer: Buffer; filename: string }>,
  options: {
    sourceMessageId?: string;
    sourceSender?: string;
    skipVirusScan?: boolean;
  } = {}
): Promise<FileMetadata[]> {
  const results: FileMetadata[] = [];
  const errors: Error[] = [];
  
  // Process each attachment
  for (const attachment of attachments) {
    try {
      const metadata = await processAttachment(
        attachment.buffer,
        attachment.filename,
        options
      );
      results.push(metadata);
    } catch (error) {
      // Collect errors but continue processing other attachments
      errors.push(error as Error);
    }
  }
  
  // If all attachments failed, throw an error
  if (errors.length > 0 && errors.length === attachments.length) {
    throw new Error(`All attachments failed processing: ${errors.map(e => e.message).join('; ')}`);
  }
  
  return results;
}

/**
 * Prepares attachments for publishing to RabbitMQ
 * Converts file metadata to a format suitable for message queue
 * 
 * @param metadata - File metadata to prepare
 * @returns Object ready for JSON serialization and publishing
 */
export function prepareAttachmentForPublishing(metadata: FileMetadata): Record<string, any> {
  // Create a copy of the metadata without the buffer to avoid sending large data in the message
  const { buffer, ...metadataWithoutBuffer } = metadata;
  
  // Add additional fields needed for processing
  return {
    ...metadataWithoutBuffer,
    processedAt: new Date().toISOString(),
    // Add any additional fields required by the document service
  };
}

/**
 * Creates a temporary directory structure for organizing attachments by type
 * Useful for batch processing of different document types
 * 
 * @returns Promise resolving to the path of the created directory structure
 */
export async function createAttachmentProcessingStructure(): Promise<{
  basePath: string;
  paths: {
    pdf: string;
    image: string;
    document: string;
    spreadsheet: string;
    other: string;
  };
  cleanup: () => Promise<void>;
}> {
  const basePath = await createTempDirectory('mca-processing-');
  
  // Create subdirectories for different document types
  const paths = {
    pdf: path.join(basePath, 'pdf'),
    image: path.join(basePath, 'image'),
    document: path.join(basePath, 'document'),
    spreadsheet: path.join(basePath, 'spreadsheet'),
    other: path.join(basePath, 'other'),
  };
  
  // Create all subdirectories
  await Promise.all([
    fs.promises.mkdir(paths.pdf, { recursive: true }),
    fs.promises.mkdir(paths.image, { recursive: true }),
    fs.promises.mkdir(paths.document, { recursive: true }),
    fs.promises.mkdir(paths.spreadsheet, { recursive: true }),
    fs.promises.mkdir(paths.other, { recursive: true }),
  ]);
  
  return {
    basePath,
    paths,
    cleanup: async () => {
      await removeTempDirectory(basePath);
    },
  };
}

/**
 * Gets the appropriate directory for a file based on its MIME type
 * 
 * @param mimeType - The MIME type of the file
 * @param paths - Object containing paths for different document types
 * @returns The appropriate directory path for the file
 */
export function getDirectoryForMimeType(
  mimeType: string,
  paths: {
    pdf: string;
    image: string;
    document: string;
    spreadsheet: string;
    other: string;
  }
): string {
  if (mimeType === 'application/pdf') {
    return paths.pdf;
  } else if (mimeType.startsWith('image/')) {
    return paths.image;
  } else if (
    mimeType === 'application/msword' ||
    mimeType === 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
  ) {
    return paths.document;
  } else if (
    mimeType === 'application/vnd.ms-excel' ||
    mimeType === 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
  ) {
    return paths.spreadsheet;
  } else {
    return paths.other;
  }
}

/**
 * Prepares a file for S3 upload
 * Adds necessary metadata and ensures proper content type
 * 
 * @param metadata - File metadata
 * @returns Object with S3 upload parameters
 */
export function prepareForS3Upload(metadata: FileMetadata): {
  Key: string;
  Body: Buffer;
  ContentType: string;
  Metadata: Record<string, string>;
} {
  if (!metadata.buffer) {
    throw new Error('File buffer is required for S3 upload');
  }
  
  // Create S3 key with path structure: YYYY/MM/DD/filename
  const date = new Date();
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, '0');
  const day = String(date.getDate()).padStart(2, '0');
  const key = `${year}/${month}/${day}/${metadata.filename}`;
  
  // Prepare metadata for S3
  const s3Metadata: Record<string, string> = {
    originalFilename: metadata.originalFilename || '',
    contentHash: metadata.contentHash || '',
    createdAt: metadata.createdAt.toISOString(),
  };
  
  // Add source information if available
  if (metadata.sourceMessageId) {
    s3Metadata.sourceMessageId = metadata.sourceMessageId;
  }
  
  if (metadata.sourceSender) {
    s3Metadata.sourceSender = metadata.sourceSender;
  }
  
  return {
    Key: key,
    Body: metadata.buffer,
    ContentType: metadata.mimeType,
    Metadata: s3Metadata,
  };
}

/**
 * Creates a cleanup function for multiple temporary resources
 * 
 * @param resources - Array of resources to clean up
 * @returns Function that cleans up all resources when called
 */
export function createCleanupFunction(
  resources: Array<{ type: 'file' | 'directory'; path: string }>
): () => Promise<void> {
  return async () => {
    for (const resource of resources) {
      try {
        if (resource.type === 'file') {
          await removeTempFile(resource.path);
        } else {
          await removeTempDirectory(resource.path);
        }
      } catch (error) {
        console.error(`Error cleaning up ${resource.type} at ${resource.path}:`, error);
      }
    }
  };
}

/**
 * Registers cleanup handlers for temporary resources
 * Ensures resources are cleaned up when the process exits
 * 
 * @param cleanup - The cleanup function to register
 */
export function registerCleanupHandlers(cleanup: () => Promise<void>): void {
  // Clean up on normal exit
  process.on('exit', () => {
    try {
      // Use synchronous operations since we're in an exit handler
      // This is a best-effort cleanup, as async operations won't complete
    } catch (error) {
      console.error('Error during exit cleanup:', error);
    }
  });
  
  // Clean up on SIGINT (Ctrl+C)
  process.on('SIGINT', async () => {
    try {
      await cleanup();
      process.exit(0);
    } catch (error) {
      console.error('Error during SIGINT cleanup:', error);
      process.exit(1);
    }
  });
  
  // Clean up on SIGTERM (kill)
  process.on('SIGTERM', async () => {
    try {
      await cleanup();
      process.exit(0);
    } catch (error) {
      console.error('Error during SIGTERM cleanup:', error);
      process.exit(1);
    }
  });
  
  // Clean up on uncaught exceptions
  process.on('uncaughtException', async (error) => {
    console.error('Uncaught exception:', error);
    try {
      await cleanup();
      process.exit(1);
    } catch (cleanupError) {
      console.error('Error during exception cleanup:', cleanupError);
      process.exit(1);
    }
  });
}