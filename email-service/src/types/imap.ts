/**
 * IMAP Connection Types
 * 
 * This file defines TypeScript interfaces for IMAP connection configuration,
 * search criteria, and connection management used by the Email Service.
 */

import type { TLSSocket } from 'tls';
import type { IDateValue } from './common';

// ----------------------------------------------------------------------

/**
 * IMAP server connection configuration
 * Defines parameters required to establish a connection to an IMAP server
 */
export interface IIMAPConfig {
  /** IMAP server hostname or IP address */
  host: string;
  
  /** IMAP server port (typically 143 for standard, 993 for TLS) */
  port: number;
  
  /** Username for authentication */
  user: string;
  
  /** Password for authentication */
  password: string;
  
  /** Whether to use TLS for the connection (required for production) */
  tls: boolean;
  
  /** TLS configuration options */
  tlsOptions?: {
    /** Minimum TLS version to accept (must be TLS 1.2+) */
    minVersion?: 'TLSv1.2' | 'TLSv1.3';
    
    /** Whether to reject unauthorized certificates */
    rejectUnauthorized?: boolean;
    
    /** CA certificates to trust */
    ca?: string | string[] | Buffer | Buffer[];
    
    /** Client certificate for mutual TLS */
    cert?: string | Buffer;
    
    /** Client key for mutual TLS */
    key?: string | Buffer;
  };
  
  /** Authentication timeout in milliseconds */
  authTimeout?: number;
  
  /** Socket timeout in milliseconds */
  socketTimeout?: number;
  
  /** Keep-alive configuration */
  keepalive?: boolean | {
    /** Interval in milliseconds at which NOOPs are sent */
    interval?: number;
    
    /** Interval in milliseconds at which IDLE command is re-sent */
    idleInterval?: number;
    
    /** Force NOOP keepalive even on servers that support IDLE */
    forceNoop?: boolean;
  };
  
  /** Debug function for logging */
  debug?: (info: string) => void;
}

/**
 * IMAP search criteria for filtering emails
 * Used to search for specific emails in a mailbox
 */
export interface IIMAPSearchCriteria {
  /** Search for all messages */
  ALL?: boolean;
  
  /** Search for messages with a specific flag */
  FLAGGED?: boolean;
  UNFLAGGED?: boolean;
  SEEN?: boolean;
  UNSEEN?: boolean;
  ANSWERED?: boolean;
  UNANSWERED?: boolean;
  DELETED?: boolean;
  UNDELETED?: boolean;
  DRAFT?: boolean;
  UNDRAFT?: boolean;
  
  /** Search by date */
  BEFORE?: Date | string;
  ON?: Date | string;
  SINCE?: Date | string;
  SENTON?: Date | string;
  SENTSINCE?: Date | string;
  SENTSINCE?: Date | string;
  
  /** Search by size */
  LARGER?: number;
  SMALLER?: number;
  
  /** Search by header fields */
  FROM?: string;
  TO?: string;
  CC?: string;
  BCC?: string;
  SUBJECT?: string;
  BODY?: string;
  TEXT?: string;
  
  /** Search by UID */
  UID?: string | number | (string | number)[];
}

/**
 * IMAP connection state
 */
export enum IMAPConnectionState {
  DISCONNECTED = 'disconnected',
  CONNECTING = 'connecting',
  CONNECTED = 'connected',
  AUTHENTICATING = 'authenticating',
  AUTHENTICATED = 'authenticated',
  LOGOUT = 'logout',
  ERROR = 'error'
}

/**
 * IMAP connection interface
 * Represents an active connection to an IMAP server
 */
export interface IIMAPConnection {
  /** Unique identifier for this connection */
  id: string;
  
  /** Current state of the connection */
  state: IMAPConnectionState;
  
  /** Configuration used for this connection */
  config: IIMAPConfig;
  
  /** The underlying TLS socket when connected securely */
  socket?: TLSSocket;
  
  /** Timestamp when the connection was established */
  connectedAt?: Date;
  
  /** Timestamp when the connection was last used */
  lastUsedAt?: Date;
  
  /** Number of reconnection attempts made */
  reconnectAttempts?: number;
  
  /** Connect to the IMAP server */
  connect(): Promise<void>;
  
  /** Disconnect from the IMAP server */
  disconnect(): Promise<void>;
  
  /** Check if the connection is active and authenticated */
  isActive(): boolean;
  
  /** Ping the server to keep the connection alive */
  ping(): Promise<boolean>;
}

/**
 * IMAP connection pool configuration
 */
export interface IIMAPConnectionPoolConfig {
  /** Minimum number of connections to maintain in the pool */
  minConnections: number;
  
  /** Maximum number of connections allowed in the pool */
  maxConnections: number;
  
  /** Time in milliseconds after which an idle connection is closed */
  idleTimeout: number;
  
  /** Maximum time in milliseconds to wait for an available connection */
  acquireTimeout: number;
  
  /** Maximum number of connection attempts before failing */
  maxRetries: number;
  
  /** Delay in milliseconds between reconnection attempts */
  retryDelay: number;
  
  /** Whether to validate connections before providing them from the pool */
  validateConnection: boolean;
}

/**
 * IMAP connection pool interface
 * Manages a pool of IMAP connections for efficient reuse
 */
export interface IIMAPConnectionPool {
  /** Get a connection from the pool */
  acquire(): Promise<IIMAPConnection>;
  
  /** Release a connection back to the pool */
  release(connection: IIMAPConnection): Promise<void>;
  
  /** Create a new connection */
  create(): Promise<IIMAPConnection>;
  
  /** Destroy a connection */
  destroy(connection: IIMAPConnection): Promise<void>;
  
  /** Get the current number of active connections */
  getActiveConnectionCount(): number;
  
  /** Get the current number of idle connections */
  getIdleConnectionCount(): number;
  
  /** Close all connections and shut down the pool */
  shutdown(): Promise<void>;
}

/**
 * IMAP connection error
 */
export class IMAPConnectionError extends Error {
  constructor(
    message: string,
    public readonly code?: string,
    public readonly originalError?: Error
  ) {
    super(message);
    this.name = 'IMAPConnectionError';
  }
}

/**
 * IMAP connection timeout error
 */
export class IMAPConnectionTimeoutError extends IMAPConnectionError {
  constructor(
    message: string,
    public readonly timeout: number,
    public readonly originalError?: Error
  ) {
    super(message, 'TIMEOUT', originalError);
    this.name = 'IMAPConnectionTimeoutError';
  }
}