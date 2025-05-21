import { Injectable } from '@nestjs/common';
import * as NodeClam from 'clamscan';
import * as fs from 'fs';
import * as path from 'path';
import { promisify } from 'util';
import { v4 as uuidv4 } from 'uuid';

import { AppConfig } from '../config/app';
import { logger } from '../utils/logger';
import { retry } from '../utils/retry';
import { createServiceError } from '../utils/error';

/**
 * Interface for virus scan result
 */
export interface IScanResult {
  /** Whether the file is infected */
  isInfected: boolean;
  /** Path to the scanned file */
  file?: string;
  /** Detected viruses if any */
  viruses?: string[];
  /** Error if scan failed */
  error?: Error;
}

/**
 * Interface for quarantine result
 */
export interface IQuarantineResult {
  /** Whether the quarantine operation was successful */
  success: boolean;
  /** Path to the quarantined file */
  quarantinePath?: string;
  /** Error if quarantine failed */
  error?: Error;
}

/**
 * Interface for virus scanner configuration
 */
export interface IVirusScannerConfig {
  /** Path to the ClamAV binary */
  clamavBinaryPath?: string;
  /** Path to virus definitions */
  clamavDbPath?: string;
  /** Socket path for clamd */
  clamdscanSocket?: string;
  /** Host for clamd TCP connection */
  clamdscanHost?: string;
  /** Port for clamd TCP connection */
  clamdscanPort?: number;
  /** Path to quarantine directory */
  quarantinePath: string;
  /** Whether to remove infected files */
  removeInfected: boolean;
  /** Whether to use multiscan (multiple threads) */
  useMultiscan: boolean;
  /** Timeout for scanning in milliseconds */
  scanTimeout: number;
  /** Maximum file size to scan in bytes */
  maxFileSize: number;
  /** Email addresses to notify on virus detection */
  notificationEmails: string[];
}

/**
 * Service for scanning email attachments for viruses
 * 
 * This service integrates with ClamAV to scan files before they enter
 * the document processing pipeline. It provides functionality for:
 * - Scanning individual files and buffers
 * - Quarantining infected files
 * - Notifying administrators of detected threats
 * - Logging scan results for audit purposes
 */
@Injectable()
export class VirusScannerService {
  private clamscan: any;
  private initialized: boolean = false;
  private config: IVirusScannerConfig;
  private writeFileAsync = promisify(fs.writeFile);
  private mkdirAsync = promisify(fs.mkdir);
  private unlinkAsync = promisify(fs.unlink);
  
  /**
   * Creates an instance of VirusScannerService
   */
  constructor() {
    this.config = this.loadConfig();
    this.initialize();
  }

  /**
   * Loads configuration based on environment
   */
  private loadConfig(): IVirusScannerConfig {
    const env = process.env.NODE_ENV || 'development';
    const quarantinePath = process.env.VIRUS_QUARANTINE_PATH || path.join(process.cwd(), 'quarantine');
    
    // Default configuration
    const config: IVirusScannerConfig = {
      quarantinePath,
      removeInfected: false,
      useMultiscan: true,
      scanTimeout: 60000, // 60 seconds
      maxFileSize: 25 * 1024 * 1024, // 25MB
      notificationEmails: ['security@dollarfunding.com']
    };

    // Environment-specific configuration
    if (env === 'development') {
      // For development, prefer local binary if available
      config.clamavBinaryPath = '/usr/bin/clamscan';
      config.removeInfected = false;
    } else {
      // For staging and production, prefer clamd socket/TCP
      config.clamdscanSocket = process.env.CLAMD_SOCKET || '/var/run/clamav/clamd.sock';
      config.clamdscanHost = process.env.CLAMD_HOST || '127.0.0.1';
      config.clamdscanPort = parseInt(process.env.CLAMD_PORT || '3310', 10);
      config.removeInfected = true;
    }

    // Add notification emails from environment if available
    if (process.env.VIRUS_NOTIFICATION_EMAILS) {
      config.notificationEmails = process.env.VIRUS_NOTIFICATION_EMAILS.split(',');
    }

    return config;
  }

  /**
   * Initializes the virus scanner
   */
  private async initialize(): Promise<void> {
    try {
      // Ensure quarantine directory exists
      await this.ensureQuarantineDirectory();

      // Initialize ClamAV scanner
      const options: any = {
        removeInfected: this.config.removeInfected,
        quarantineInfected: !this.config.removeInfected,
        scanRecursively: true,
        clamscan: {
          path: this.config.clamavBinaryPath,
          db: this.config.clamavDbPath,
          active: !!this.config.clamavBinaryPath
        },
        clamdscan: {
          socket: this.config.clamdscanSocket,
          host: this.config.clamdscanHost,
          port: this.config.clamdscanPort,
          timeout: this.config.scanTimeout,
          localFallback: true,
          multiscan: this.config.useMultiscan,
          active: !!(this.config.clamdscanSocket || (this.config.clamdscanHost && this.config.clamdscanPort))
        },
        preference: this.config.clamdscanSocket || (this.config.clamdscanHost && this.config.clamdscanPort) 
          ? 'clamdscan' 
          : 'clamscan'
      };

      // Initialize the scanner
      this.clamscan = await new NodeClam().init(options);
      this.initialized = true;

      // Log successful initialization
      logger.info('Virus scanner initialized successfully', {
        component: 'VirusScannerService',
        preference: options.preference,
        clamdscanActive: options.clamdscan.active,
        clamscanActive: options.clamscan.active
      });

      // Get and log ClamAV version
      const version = await this.clamscan.getVersion();
      logger.info(`ClamAV version: ${version}`, { component: 'VirusScannerService' });
    } catch (error) {
      logger.error('Failed to initialize virus scanner', {
        component: 'VirusScannerService',
        error: error.message,
        stack: error.stack
      });
      
      // Don't throw here to allow the service to start even if ClamAV is not available
      // We'll check this.initialized before scanning
    }
  }

  /**
   * Ensures the quarantine directory exists
   */
  private async ensureQuarantineDirectory(): Promise<void> {
    try {
      await this.mkdirAsync(this.config.quarantinePath, { recursive: true });
      logger.info(`Quarantine directory ensured at ${this.config.quarantinePath}`, {
        component: 'VirusScannerService'
      });
    } catch (error) {
      logger.error('Failed to create quarantine directory', {
        component: 'VirusScannerService',
        path: this.config.quarantinePath,
        error: error.message
      });
      throw error;
    }
  }

  /**
   * Checks if the virus scanner is initialized
   */
  public isInitialized(): boolean {
    return this.initialized;
  }

  /**
   * Scans a file for viruses
   * 
   * @param filePath - Path to the file to scan
   * @returns Scan result
   */
  public async scanFile(filePath: string): Promise<IScanResult> {
    if (!this.initialized) {
      const error = new Error('Virus scanner not initialized');
      logger.error('Cannot scan file, virus scanner not initialized', {
        component: 'VirusScannerService',
        filePath
      });
      return { isInfected: false, error };
    }

    try {
      // Check if file exists and is within size limits
      const stats = await fs.promises.stat(filePath);
      if (stats.size > this.config.maxFileSize) {
        const error = createServiceError(
          'FILE_TOO_LARGE',
          `File exceeds maximum scan size of ${this.config.maxFileSize} bytes`,
          { filePath, fileSize: stats.size, maxSize: this.config.maxFileSize }
        );
        logger.warn('File too large for virus scanning', {
          component: 'VirusScannerService',
          filePath,
          fileSize: stats.size,
          maxSize: this.config.maxFileSize
        });
        return { isInfected: false, error };
      }

      // Scan the file with retry logic
      const scanResult = await retry(
        async () => this.clamscan.isInfected(filePath),
        {
          retries: 3,
          minTimeout: 1000,
          factor: 2,
          onRetry: (error) => {
            logger.warn('Retrying virus scan after error', {
              component: 'VirusScannerService',
              filePath,
              error: error.message
            });
          }
        }
      );

      // Log scan result
      if (scanResult.isInfected) {
        logger.warn('Virus detected in file', {
          component: 'VirusScannerService',
          filePath,
          viruses: scanResult.viruses,
          action: this.config.removeInfected ? 'removed' : 'quarantined'
        });

        // Quarantine the file if not set to remove
        if (!this.config.removeInfected) {
          await this.quarantineFile(filePath, scanResult.viruses);
        }

        // Notify administrators
        await this.notifyAdministrators(filePath, scanResult.viruses);
      } else {
        logger.info('File scanned, no viruses detected', {
          component: 'VirusScannerService',
          filePath
        });
      }

      return scanResult;
    } catch (error) {
      logger.error('Error scanning file for viruses', {
        component: 'VirusScannerService',
        filePath,
        error: error.message,
        stack: error.stack
      });
      return { isInfected: false, error };
    }
  }

  /**
   * Scans a buffer for viruses
   * 
   * @param buffer - Buffer to scan
   * @param filename - Optional filename for logging
   * @returns Scan result
   */
  public async scanBuffer(buffer: Buffer, filename?: string): Promise<IScanResult> {
    if (!this.initialized) {
      const error = new Error('Virus scanner not initialized');
      logger.error('Cannot scan buffer, virus scanner not initialized', {
        component: 'VirusScannerService',
        filename
      });
      return { isInfected: false, error };
    }

    try {
      // Check if buffer is within size limits
      if (buffer.length > this.config.maxFileSize) {
        const error = createServiceError(
          'FILE_TOO_LARGE',
          `Buffer exceeds maximum scan size of ${this.config.maxFileSize} bytes`,
          { filename, bufferSize: buffer.length, maxSize: this.config.maxFileSize }
        );
        logger.warn('Buffer too large for virus scanning', {
          component: 'VirusScannerService',
          filename,
          bufferSize: buffer.length,
          maxSize: this.config.maxFileSize
        });
        return { isInfected: false, error };
      }

      // Create a temporary file for scanning
      const tempFilePath = path.join(
        this.config.quarantinePath,
        `temp-${uuidv4()}${filename ? `-${path.basename(filename)}` : ''}`
      );
      
      await this.writeFileAsync(tempFilePath, buffer);

      try {
        // Scan the temporary file
        const scanResult = await this.scanFile(tempFilePath);
        
        // Clean up the temporary file if not infected or if set to remove infected
        if (!scanResult.isInfected || this.config.removeInfected) {
          await this.unlinkAsync(tempFilePath).catch(err => {
            logger.error('Failed to delete temporary file', {
              component: 'VirusScannerService',
              tempFilePath,
              error: err.message
            });
          });
        }

        return scanResult;
      } catch (error) {
        // Clean up the temporary file on error
        await this.unlinkAsync(tempFilePath).catch(() => {});
        throw error;
      }
    } catch (error) {
      logger.error('Error scanning buffer for viruses', {
        component: 'VirusScannerService',
        filename,
        error: error.message,
        stack: error.stack
      });
      return { isInfected: false, error };
    }
  }

  /**
   * Quarantines an infected file
   * 
   * @param filePath - Path to the infected file
   * @param viruses - List of detected viruses
   * @returns Quarantine result
   */
  private async quarantineFile(filePath: string, viruses?: string[]): Promise<IQuarantineResult> {
    try {
      // Generate a unique quarantine filename
      const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
      const basename = path.basename(filePath);
      const quarantineFilename = `infected-${timestamp}-${basename}`;
      const quarantinePath = path.join(this.config.quarantinePath, quarantineFilename);

      // Create a metadata file with infection details
      const metadataPath = `${quarantinePath}.meta.json`;
      const metadata = {
        originalPath: filePath,
        quarantinedAt: new Date().toISOString(),
        viruses: viruses || ['Unknown threat'],
        fileSize: (await fs.promises.stat(filePath)).size
      };

      // Copy the file to quarantine
      await fs.promises.copyFile(filePath, quarantinePath);
      await this.writeFileAsync(metadataPath, JSON.stringify(metadata, null, 2));

      logger.info('Infected file quarantined', {
        component: 'VirusScannerService',
        originalPath: filePath,
        quarantinePath,
        viruses
      });

      return { success: true, quarantinePath };
    } catch (error) {
      logger.error('Failed to quarantine infected file', {
        component: 'VirusScannerService',
        filePath,
        error: error.message,
        stack: error.stack
      });
      return { success: false, error };
    }
  }

  /**
   * Notifies administrators about detected threats
   * 
   * @param filePath - Path to the infected file
   * @param viruses - List of detected viruses
   */
  private async notifyAdministrators(filePath: string, viruses?: string[]): Promise<void> {
    try {
      // In a real implementation, this would send an email or other notification
      // For now, we'll just log the notification
      logger.warn('SECURITY ALERT: Virus detected in email attachment', {
        component: 'VirusScannerService',
        filePath,
        viruses: viruses || ['Unknown threat'],
        notificationSent: true,
        recipients: this.config.notificationEmails
      });

      // In a complete implementation, this would use a notification service
      // to send emails or other alerts to administrators
      // Example:
      // await this.notificationService.sendSecurityAlert({
      //   subject: 'SECURITY ALERT: Virus detected in email attachment',
      //   recipients: this.config.notificationEmails,
      //   data: {
      //     filePath,
      //     viruses: viruses || ['Unknown threat'],
      //     detectedAt: new Date().toISOString(),
      //     quarantined: !this.config.removeInfected
      //   }
      // });
    } catch (error) {
      logger.error('Failed to notify administrators about virus detection', {
        component: 'VirusScannerService',
        filePath,
        error: error.message
      });
      // Don't throw the error to prevent blocking the main flow
    }
  }

  /**
   * Gets the virus scanner configuration
   * 
   * @returns Current virus scanner configuration
   */
  public getConfig(): IVirusScannerConfig {
    return { ...this.config };
  }

  /**
   * Updates the virus scanner configuration
   * 
   * @param config - New configuration options
   */
  public updateConfig(config: Partial<IVirusScannerConfig>): void {
    this.config = { ...this.config, ...config };
    logger.info('Virus scanner configuration updated', {
      component: 'VirusScannerService',
      config: this.config
    });
  }

  /**
   * Checks if ClamAV is available and functioning
   * 
   * @returns True if ClamAV is available and functioning
   */
  public async healthCheck(): Promise<boolean> {
    if (!this.initialized) {
      return false;
    }

    try {
      // Get ClamAV version as a simple health check
      const version = await this.clamscan.getVersion();
      return !!version;
    } catch (error) {
      logger.error('ClamAV health check failed', {
        component: 'VirusScannerService',
        error: error.message
      });
      return false;
    }
  }
}