/**
 * IMAP Configuration
 * 
 * This file defines the configuration for the IMAP connection used by the Email Service
 * to monitor the submissions inbox. It includes connection parameters, security settings,
 * polling intervals, and reconnection strategies.
 */

/**
 * Interface for IMAP connection configuration
 */
export interface ImapConnectionConfig {
  user: string;
  password: string;
  host: string;
  port: number;
  tls: boolean;
  tlsOptions: {
    minVersion: string;
    rejectUnauthorized: boolean;
  };
  authTimeout: number;
  socketTimeout: number;
}

/**
 * Interface for IMAP connection pool configuration
 */
export interface ImapPoolConfig {
  maxConnections: number;
  idleTimeout: number;
  acquireTimeout: number;
  createRetryIntervalMs: number;
  createTimeoutMs: number;
}

/**
 * Interface for IMAP polling configuration
 */
export interface ImapPollingConfig {
  intervalMs: number;
  maxRetries: number;
  retryDelayMs: number;
}

/**
 * Interface for IMAP reconnection configuration
 */
export interface ImapReconnectionConfig {
  maxRetries: number;
  retryDelayMs: number;
  backoffFactor: number;
  maxRetryDelayMs: number;
}

/**
 * Complete IMAP configuration interface
 */
export interface ImapConfig {
  connection: ImapConnectionConfig;
  pool: ImapPoolConfig;
  polling: ImapPollingConfig;
  reconnection: ImapReconnectionConfig;
  keepalive: {
    enabled: boolean;
    interval: number;
    idleInterval: number;
    forceNoop: boolean;
  };
}

/**
 * Default IMAP configuration
 * 
 * This configuration is set up for the submissions@dollarfunding.com mailbox
 * with security best practices and appropriate timeout settings.
 */
export const defaultImapConfig: ImapConfig = {
  connection: {
    // Email account credentials for the submissions inbox
    user: 'submissions@dollarfunding.com',
    password: process.env.IMAP_PASSWORD || '',
    
    // IMAP server connection details
    host: 'imap.dollarfunding.com',
    port: 993, // Standard port for IMAP over TLS
    
    // TLS is required for secure connections
    tls: true,
    
    // TLS options to enforce security best practices
    tlsOptions: {
      // Enforce TLS 1.2 or higher
      minVersion: 'TLSv1.2',
      
      // Verify server certificate to prevent MITM attacks
      rejectUnauthorized: true,
    },
    
    // Timeout settings for connection reliability
    authTimeout: 10000, // 10 seconds to authenticate
    socketTimeout: 60000, // 60 seconds socket timeout
  },
  
  // Connection pool settings for efficient resource usage
  pool: {
    maxConnections: 5, // Maximum number of concurrent connections
    idleTimeout: 60000, // 60 seconds before idle connection is released
    acquireTimeout: 30000, // 30 seconds timeout when acquiring a connection
    createRetryIntervalMs: 5000, // 5 seconds between connection creation retries
    createTimeoutMs: 30000, // 30 seconds timeout for connection creation
  },
  
  // Polling configuration for inbox monitoring
  polling: {
    intervalMs: 60000, // Check for new emails every 60 seconds
    maxRetries: 3, // Maximum number of retries for failed polling
    retryDelayMs: 10000, // 10 seconds delay between polling retries
  },
  
  // Reconnection strategy for handling connection failures
  reconnection: {
    maxRetries: 10, // Maximum number of reconnection attempts
    retryDelayMs: 5000, // Initial delay between reconnection attempts
    backoffFactor: 1.5, // Exponential backoff factor for retry delays
    maxRetryDelayMs: 300000, // Maximum delay between retries (5 minutes)
  },
  
  // Keepalive settings to maintain connection
  keepalive: {
    enabled: true, // Enable keepalive to prevent connection timeouts
    interval: 10000, // Send NOOP command every 10 seconds
    idleInterval: 300000, // Refresh IDLE command every 5 minutes
    forceNoop: false, // Use IDLE command if supported by the server
  },
};

/**
 * Get the IMAP configuration with optional overrides
 * 
 * @param overrides - Optional partial configuration to override defaults
 * @returns Complete IMAP configuration
 */
export function getImapConfig(overrides?: Partial<ImapConfig>): ImapConfig {
  if (!overrides) {
    return defaultImapConfig;
  }
  
  return {
    ...defaultImapConfig,
    ...overrides,
    connection: {
      ...defaultImapConfig.connection,
      ...overrides.connection,
      tlsOptions: {
        ...defaultImapConfig.connection.tlsOptions,
        ...overrides.connection?.tlsOptions,
      },
    },
    pool: {
      ...defaultImapConfig.pool,
      ...overrides.pool,
    },
    polling: {
      ...defaultImapConfig.polling,
      ...overrides.polling,
    },
    reconnection: {
      ...defaultImapConfig.reconnection,
      ...overrides.reconnection,
    },
    keepalive: {
      ...defaultImapConfig.keepalive,
      ...overrides.keepalive,
    },
  };
}

/**
 * Environment-specific IMAP configuration
 * 
 * This allows for different configurations based on the environment
 * (development, staging, production)
 */
export const imapConfig = getImapConfig(
  process.env.NODE_ENV === 'production'
    ? {
        // Production-specific overrides
        polling: {
          intervalMs: 30000, // More frequent polling in production
        },
        pool: {
          maxConnections: 10, // More connections for production load
        },
      }
    : process.env.NODE_ENV === 'staging'
    ? {
        // Staging-specific overrides
        polling: {
          intervalMs: 45000, // Less frequent polling in staging
        },
      }
    : {
        // Development-specific overrides
        connection: {
          // Allow self-signed certificates in development
          tlsOptions: {
            rejectUnauthorized: false,
          },
        },
        polling: {
          intervalMs: 120000, // Less frequent polling in development
        },
      }
);

export default imapConfig;