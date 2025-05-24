/**
 * Virus Scanner Service
 * 
 * This service provides virus scanning capabilities for email attachments before they
 * enter the document processing pipeline. It integrates with ClamAV to scan files,
 * quarantine infected attachments, and notify administrators of security threats.
 * 
 * The service is essential for security and prevents malicious files from being processed.
 */

import { inject, injectable } from 'inversify';
import NodeClam from 'clamscan';
import { promises as fs } from 'fs';
import path from 'path';

// Import types and utilities
import { IEmailAttachment } from '../types/email';
import { ILogger } from '../types/common';
import { IAppConfig } from '../types/config';
import { TYPES } from '../types/inversify-types';
import { retryWithBackoff } from '../utils/retry';

/**
 * Interface for virus scan results
 */
export interface IScanResult {
  isInfected: boolean;
  viruses?: string[];
  error?: Error;
  filePath: string;
}

/**
 * Interface for virus scanner configuration
 */
export interface IVirusScannerConfig {
  // Path to quarantine directory for infected files
  quarantinePath: string;
  
  // ClamAV configuration
  clamav: {
    // Path to clamscan binary
    binPath?: string;
    
    // Socket path for clamdscan
    socketPath?: string;
    
    // Host for remote ClamAV daemon
    host?: string;
    
    // Port for remote ClamAV daemon
    port?: number;
    
    // Timeout for scanning operations (ms)
    timeout: number;
    
    // Whether to scan archives
    scanArchives: boolean;
    
    // Whether to remove infected files automatically
    removeInfected: boolean;
  };
  
  // Notification settings
  notification: {
    // Whether to notify administrators of threats
    enabled: boolean;
    
    // Email addresses to notify
    adminEmails: string[];
  };
}

/**
 * Virus Scanner Service
 * 
 * Provides virus scanning capabilities for email attachments before they enter
 * the document processing pipeline.
 */
@injectable()
export class VirusScannerService {
  private scanner: any;
  private initialized: boolean = false;
  private config: IVirusScannerConfig;
  
  constructor(
    @inject(TYPES.Logger) private readonly logger: ILogger,
    @inject(TYPES.AppConfig) private readonly appConfig: IAppConfig
  ) {
    // Initialize configuration based on environment
    this.config = this.initializeConfig();
    
    // Create quarantine directory if it doesn't exist
    this.ensureQuarantineDirectory();
    
    // Initialize ClamAV scanner
    this.initializeScanner().catch(error => {
      this.logger.error('Failed to initialize virus scanner', { error: error.message });
    });
  }
  
  /**
   * Initialize scanner configuration based on environment
   */
  private initializeConfig(): IVirusScannerConfig {
    const env = this.appConfig.environment;
    
    // Base configuration
    const config: IVirusScannerConfig = {
      quarantinePath: path.join(process.cwd(), 'quarantine'),
      clamav: {
        timeout: 60000, // 60 seconds
        scanArchives: true,
        removeInfected: false // We handle this ourselves
      },
      notification: {
        enabled: true,
        adminEmails: ['security@dollarfunding.com']
      }
    };
    
    // Environment-specific configuration
    if (env === 'production') {
      // In production, use clamdscan daemon for better performance
      config.clamav.socketPath = '/var/run/clamav/clamd.sock';
    } else if (env === 'staging') {
      // In staging, use clamdscan daemon
      config.clamav.socketPath = '/var/run/clamav/clamd.sock';
    } else {
      // In development, use local binary
      config.clamav.binPath = '/usr/bin/clamscan';
    }
    
    return config;
  }
  
  /**
   * Ensure quarantine directory exists
   */
  private async ensureQuarantineDirectory(): Promise<void> {
    try {
      await fs.mkdir(this.config.quarantinePath, { recursive: true });
      this.logger.info('Quarantine directory created or verified', {
        path: this.config.quarantinePath
      });
    } catch (error) {
      this.logger.error('Failed to create quarantine directory', {
        path: this.config.quarantinePath,
        error: error.message
      });
    }
  }
  
  /**
   * Initialize ClamAV scanner
   */
  private async initializeScanner(): Promise<void> {
    try {
      const clamConfig: any = {
        removeInfected: this.config.clamav.removeInfected,
        quarantineInfected: false, // We handle quarantine ourselves
        scanRecursively: true,
        debugMode: this.appConfig.environment !== 'production',
        scanLog: path.join(process.cwd(), 'logs', 'virus-scan.log'),
        fileList: null,
        scanArchives: this.config.clamav.scanArchives,
        clamscan: {
          path: this.config.clamav.binPath || null,
          db: null, // Use default virus definitions
          active: !!this.config.clamav.binPath
        },
        clamdscan: {
          socket: this.config.clamav.socketPath || null,
          host: this.config.clamav.host || null,
          port: this.config.clamav.port || null,
          timeout: this.config.clamav.timeout,
          localFallback: false,
          active: !!(this.config.clamav.socketPath || this.config.clamav.host)
        },
        preference: this.config.clamav.socketPath || this.config.clamav.host ? 'clamdscan' : 'clamscan'
      };
      
      const clamscan = new NodeClam();
      this.scanner = await clamscan.init(clamConfig);
      this.initialized = true;
      
      // Log scanner version
      const version = await this.scanner.getVersion();
      this.logger.info('Virus scanner initialized successfully', { version });
    } catch (error) {
      this.initialized = false;
      throw new Error(`Failed to initialize virus scanner: ${error.message}`);
    }
  }
  
  /**
   * Check if scanner is initialized
   */
  public isInitialized(): boolean {
    return this.initialized;
  }
  
  /**
   * Scan a file for viruses
   * 
   * @param filePath Path to the file to scan
   * @returns Scan result with infection status
   */
  public async scanFile(filePath: string): Promise<IScanResult> {
    if (!this.initialized) {
      await this.initializeScanner();
    }
    
    try {
      // Retry scan operation with exponential backoff if it fails
      const result = await retryWithBackoff(
        async () => {
          const scanResult = await this.scanner.isInfected(filePath);
          return scanResult;
        },
        {
          maxRetries: 3,
          initialDelay: 1000,
          maxDelay: 5000
        }
      );
      
      this.logger.info('File scan completed', {
        filePath,
        isInfected: result.isInfected,
        viruses: result.viruses
      });
      
      return {
        isInfected: result.isInfected,
        viruses: result.viruses,
        filePath
      };
    } catch (error) {
      this.logger.error('Error scanning file', {
        filePath,
        error: error.message
      });
      
      return {
        isInfected: false, // Assume not infected on error
        error,
        filePath
      };
    }
  }
  
  /**
   * Scan an email attachment for viruses
   * 
   * @param attachment Email attachment to scan
   * @returns Scan result with infection status
   */
  public async scanAttachment(attachment: IEmailAttachment): Promise<IScanResult> {
    if (!attachment.path) {
      throw new Error('Attachment path is required for virus scanning');
    }
    
    const result = await this.scanFile(attachment.path);
    
    // Handle infected files
    if (result.isInfected) {
      await this.handleInfectedFile(attachment, result);
    }
    
    return result;
  }
  
  /**
   * Handle an infected file
   * 
   * @param attachment Email attachment that is infected
   * @param scanResult Scan result with infection details
   */
  private async handleInfectedFile(attachment: IEmailAttachment, scanResult: IScanResult): Promise<void> {
    try {
      // Generate quarantine file path
      const quarantineFilePath = path.join(
        this.config.quarantinePath,
        `${Date.now()}_${path.basename(attachment.path)}`
      );
      
      // Move file to quarantine
      await fs.copyFile(attachment.path, quarantineFilePath);
      
      // Log quarantine action
      this.logger.warn('Infected file quarantined', {
        originalPath: attachment.path,
        quarantinePath: quarantineFilePath,
        fileName: attachment.filename,
        viruses: scanResult.viruses,
        emailId: attachment.emailId
      });
      
      // Notify administrators if enabled
      if (this.config.notification.enabled) {
        await this.notifyAdministrators(attachment, scanResult);
      }
    } catch (error) {
      this.logger.error('Failed to quarantine infected file', {
        filePath: attachment.path,
        error: error.message
      });
    }
  }
  
  /**
   * Notify administrators of a security threat
   * 
   * @param attachment Email attachment that is infected
   * @param scanResult Scan result with infection details
   */
  private async notifyAdministrators(attachment: IEmailAttachment, scanResult: IScanResult): Promise<void> {
    try {
      // In a real implementation, this would send an email or other notification
      // to administrators. For now, we'll just log the notification.
      this.logger.warn('Security threat notification', {
        to: this.config.notification.adminEmails,
        subject: 'Security Threat Detected: Virus Found in Email Attachment',
        attachment: {
          filename: attachment.filename,
          contentType: attachment.contentType,
          size: attachment.size
        },
        emailId: attachment.emailId,
        viruses: scanResult.viruses,
        timestamp: new Date().toISOString()
      });
      
      // In a production environment, this would integrate with the notification service
      // to send actual emails or other alerts to administrators.
    } catch (error) {
      this.logger.error('Failed to notify administrators', {
        error: error.message
      });
    }
  }
  
  /**
   * Scan multiple attachments for viruses
   * 
   * @param attachments Array of email attachments to scan
   * @returns Array of scan results
   */
  public async scanAttachments(attachments: IEmailAttachment[]): Promise<IScanResult[]> {
    const results: IScanResult[] = [];
    
    for (const attachment of attachments) {
      try {
        const result = await this.scanAttachment(attachment);
        results.push(result);
      } catch (error) {
        this.logger.error('Error scanning attachment', {
          filename: attachment.filename,
          error: error.message
        });
        
        results.push({
          isInfected: false, // Assume not infected on error
          error,
          filePath: attachment.path || 'unknown'
        });
      }
    }
    
    return results;
  }
  
  /**
   * Check if any attachments are infected
   * 
   * @param attachments Array of email attachments to check
   * @returns True if any attachments are infected, false otherwise
   */
  public async hasInfectedAttachments(attachments: IEmailAttachment[]): Promise<boolean> {
    const results = await this.scanAttachments(attachments);
    return results.some(result => result.isInfected);
  }
}