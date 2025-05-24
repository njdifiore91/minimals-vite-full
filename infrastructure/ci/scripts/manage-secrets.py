#!/usr/bin/env python3
"""
Manage Secrets - A utility for securely managing credentials and secrets across environments

This script provides functionality for securely managing credentials and secrets across
development, staging, and production environments. It implements encryption, secret rotation,
access control, and audit logging, as well as integration with external secret management
systems like AWS Secrets Manager and HashiCorp Vault.

Usage:
  manage-secrets.py [options] <command> [<args>...]

Commands:
  set           Set a secret value
  get           Get a secret value
  list          List available secrets
  rotate        Rotate a secret
  delete        Delete a secret
  import        Import secrets from external systems
  export        Export secrets to external systems
  grant-access  Grant access to a secret for a service
  revoke-access Revoke access to a secret for a service
  audit         View audit logs for secret operations

Options:
  -h, --help                 Show this help message and exit
  -e, --environment ENV      Environment (development, staging, production) [default: development]
  -v, --verbose              Enable verbose output
  --aws                      Use AWS Secrets Manager
  --vault                    Use HashiCorp Vault
  --local                    Use local encrypted storage (default)
  --config FILE              Path to configuration file
  --version                  Show version information
"""

import argparse
import base64
import datetime
import getpass
import hashlib
import hmac
import json
import logging
import os
import sys
import time
import uuid
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union, Any

# Third-party imports
try:
    from cryptography.fernet import Fernet
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
    from cryptography.hazmat.primitives import padding
    from cryptography.hazmat.backends import default_backend
    CRYPTOGRAPHY_AVAILABLE = True
except ImportError:
    CRYPTOGRAPHY_AVAILABLE = False

try:
    import boto3
    from botocore.exceptions import ClientError
    AWS_AVAILABLE = True
except ImportError:
    AWS_AVAILABLE = False

try:
    import hvac
    VAULT_AVAILABLE = True
except ImportError:
    VAULT_AVAILABLE = False

# Constants
VERSION = "1.0.0"
SECRET_DIR = "secrets"
CONFIG_FILE = "config.json"
KEY_FILE = "master.key"
AUDIT_LOG_FILE = "audit.log"
ACCESS_CONTROL_FILE = "access_control.json"
SECRET_FILE_EXT = ".enc"
DEFAULT_KDF_ITERATIONS = 100000
DEFAULT_ROTATION_DAYS = 90

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
    ]
)
logger = logging.getLogger("manage-secrets")


class SecretManager:
    """Main class for managing secrets"""

    def __init__(self, environment: str, config_path: Optional[str] = None,
                 use_aws: bool = False, use_vault: bool = False, use_local: bool = True,
                 verbose: bool = False):
        """Initialize the SecretManager

        Args:
            environment: The environment (development, staging, production)
            config_path: Path to the configuration file
            use_aws: Whether to use AWS Secrets Manager
            use_vault: Whether to use HashiCorp Vault
            use_local: Whether to use local encrypted storage
            verbose: Whether to enable verbose output
        """
        self.environment = environment
        self.use_aws = use_aws
        self.use_vault = use_vault
        self.use_local = use_local
        self.verbose = verbose

        # Set up logging
        if verbose:
            logger.setLevel(logging.DEBUG)
        
        # Check for required dependencies
        if not CRYPTOGRAPHY_AVAILABLE:
            logger.error("The 'cryptography' package is required. Please install it with 'pip install cryptography'.")
            sys.exit(1)
        
        if use_aws and not AWS_AVAILABLE:
            logger.error("The 'boto3' package is required for AWS integration. Please install it with 'pip install boto3'.")
            sys.exit(1)
        
        if use_vault and not VAULT_AVAILABLE:
            logger.error("The 'hvac' package is required for HashiCorp Vault integration. Please install it with 'pip install hvac'.")
            sys.exit(1)

        # Set up paths
        self.base_dir = Path(os.environ.get("SECRETS_BASE_DIR", "/etc/dollarfunding/secrets"))
        self.env_dir = self.base_dir / environment
        self.secrets_dir = self.env_dir / SECRET_DIR
        self.config_file = Path(config_path) if config_path else self.env_dir / CONFIG_FILE
        self.key_file = self.env_dir / KEY_FILE
        self.audit_log_file = self.env_dir / AUDIT_LOG_FILE
        self.access_control_file = self.env_dir / ACCESS_CONTROL_FILE

        # Create directories if they don't exist
        self.env_dir.mkdir(parents=True, exist_ok=True)
        self.secrets_dir.mkdir(parents=True, exist_ok=True)

        # Load configuration
        self.config = self._load_config()

        # Initialize external services if needed
        self.aws_client = None
        self.vault_client = None

        if use_aws:
            self._init_aws()
        
        if use_vault:
            self._init_vault()

        # Load or create master key
        self.master_key = self._load_or_create_master_key()

        # Load access control
        self.access_control = self._load_access_control()

        logger.debug(f"Initialized SecretManager for environment: {environment}")

    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from file or create default"""
        if self.config_file.exists():
            try:
                with open(self.config_file, "r") as f:
                    config = json.load(f)
                    logger.debug(f"Loaded configuration from {self.config_file}")
                    return config
            except Exception as e:
                logger.warning(f"Failed to load configuration: {e}. Using defaults.")

        # Default configuration
        config = {
            "kdf_iterations": DEFAULT_KDF_ITERATIONS,
            "rotation_days": DEFAULT_ROTATION_DAYS,
            "aws": {
                "region": "us-east-1",
                "prefix": f"dollarfunding/{self.environment}/"
            },
            "vault": {
                "url": "http://localhost:8200",
                "mount_point": "secret",
                "path_prefix": f"dollarfunding/{self.environment}/"
            }
        }

        # Save default configuration
        with open(self.config_file, "w") as f:
            json.dump(config, f, indent=2)
            logger.debug(f"Created default configuration at {self.config_file}")

        return config

    def _load_or_create_master_key(self) -> bytes:
        """Load the master key from file or create a new one"""
        if self.key_file.exists():
            try:
                with open(self.key_file, "rb") as f:
                    key = f.read()
                    logger.debug(f"Loaded master key from {self.key_file}")
                    return key
            except Exception as e:
                logger.error(f"Failed to load master key: {e}")
                sys.exit(1)

        # Create a new master key
        key = Fernet.generate_key()
        
        # Save the key with restricted permissions
        with open(self.key_file, "wb") as f:
            f.write(key)
        
        # Set file permissions to be readable only by the owner
        os.chmod(self.key_file, 0o600)
        
        logger.debug(f"Created new master key at {self.key_file}")
        return key

    def _load_access_control(self) -> Dict[str, Dict[str, List[str]]]:
        """Load access control configuration"""
        if self.access_control_file.exists():
            try:
                with open(self.access_control_file, "r") as f:
                    access_control = json.load(f)
                    logger.debug(f"Loaded access control from {self.access_control_file}")
                    return access_control
            except Exception as e:
                logger.warning(f"Failed to load access control: {e}. Using defaults.")

        # Default access control (empty)
        access_control = {}

        # Save default access control
        with open(self.access_control_file, "w") as f:
            json.dump(access_control, f, indent=2)
            logger.debug(f"Created default access control at {self.access_control_file}")

        return access_control

    def _init_aws(self):
        """Initialize AWS Secrets Manager client"""
        try:
            session = boto3.session.Session()
            self.aws_client = session.client(
                service_name='secretsmanager',
                region_name=self.config["aws"]["region"]
            )
            logger.debug("Initialized AWS Secrets Manager client")
        except Exception as e:
            logger.error(f"Failed to initialize AWS Secrets Manager client: {e}")
            sys.exit(1)

    def _init_vault(self):
        """Initialize HashiCorp Vault client"""
        try:
            vault_url = self.config["vault"]["url"]
            # Try to get token from environment variable first
            vault_token = os.environ.get("VAULT_TOKEN")
            
            # If not available, prompt the user
            if not vault_token:
                vault_token = getpass.getpass("Enter Vault token: ")
            
            self.vault_client = hvac.Client(url=vault_url, token=vault_token)
            
            # Verify authentication
            if not self.vault_client.is_authenticated():
                logger.error("Failed to authenticate with Vault")
                sys.exit(1)
                
            logger.debug("Initialized HashiCorp Vault client")
        except Exception as e:
            logger.error(f"Failed to initialize HashiCorp Vault client: {e}")
            sys.exit(1)

    def _log_audit(self, action: str, secret_name: str, service_id: Optional[str] = None,
                  success: bool = True, details: Optional[str] = None):
        """Log an audit entry

        Args:
            action: The action performed (get, set, rotate, etc.)
            secret_name: The name of the secret
            service_id: The ID of the service performing the action
            success: Whether the action was successful
            details: Additional details about the action
        """
        timestamp = datetime.datetime.now().isoformat()
        entry = {
            "timestamp": timestamp,
            "action": action,
            "secret_name": secret_name,
            "service_id": service_id,
            "success": success,
            "details": details
        }

        # Append to audit log file
        with open(self.audit_log_file, "a") as f:
            f.write(json.dumps(entry) + "\n")

        logger.debug(f"Logged audit entry: {action} on {secret_name}")

    def _derive_key(self, secret_name: str, salt: bytes) -> bytes:
        """Derive an encryption key for a specific secret

        Args:
            secret_name: The name of the secret
            salt: The salt for key derivation

        Returns:
            The derived encryption key
        """
        # Use PBKDF2 to derive a key from the master key and secret name
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,  # 256 bits for AES-256
            salt=salt,
            iterations=self.config["kdf_iterations"],
            backend=default_backend()
        )
        
        # Combine master key and secret name for derivation
        material = self.master_key + secret_name.encode()
        return kdf.derive(material)

    def _encrypt(self, data: Union[str, bytes], secret_name: str) -> Tuple[bytes, bytes]:
        """Encrypt data using AES-256-GCM

        Args:
            data: The data to encrypt (string or bytes)
            secret_name: The name of the secret (used for key derivation)

        Returns:
            Tuple of (encrypted_data, salt)
        """
        # Convert string to bytes if needed
        if isinstance(data, str):
            data = data.encode()

        # Generate a random salt for key derivation
        salt = os.urandom(16)
        
        # Derive the encryption key
        key = self._derive_key(secret_name, salt)
        
        # Generate a random IV (initialization vector)
        iv = os.urandom(16)
        
        # Create an encryptor with AES-256-GCM mode
        encryptor = Cipher(
            algorithms.AES(key),
            modes.GCM(iv),
            backend=default_backend()
        ).encryptor()
        
        # Encrypt the data
        ciphertext = encryptor.update(data) + encryptor.finalize()
        
        # Get the authentication tag
        tag = encryptor.tag
        
        # Combine IV, ciphertext, and tag
        encrypted_data = iv + ciphertext + tag
        
        return encrypted_data, salt

    def _decrypt(self, encrypted_data: bytes, salt: bytes, secret_name: str) -> bytes:
        """Decrypt data using AES-256-GCM

        Args:
            encrypted_data: The encrypted data
            salt: The salt used for key derivation
            secret_name: The name of the secret (used for key derivation)

        Returns:
            The decrypted data as bytes
        """
        # Derive the encryption key
        key = self._derive_key(secret_name, salt)
        
        # Extract IV, ciphertext, and tag
        iv = encrypted_data[:16]
        tag = encrypted_data[-16:]  # GCM tag is 16 bytes
        ciphertext = encrypted_data[16:-16]
        
        # Create a decryptor with AES-256-GCM mode
        decryptor = Cipher(
            algorithms.AES(key),
            modes.GCM(iv, tag),
            backend=default_backend()
        ).decryptor()
        
        # Decrypt the data
        return decryptor.update(ciphertext) + decryptor.finalize()

    def _get_secret_path(self, secret_name: str, version: Optional[int] = None) -> Path:
        """Get the path to a secret file

        Args:
            secret_name: The name of the secret
            version: The version of the secret (None for latest)

        Returns:
            The path to the secret file
        """
        # Replace slashes with underscores in the secret name
        safe_name = secret_name.replace("/", "_")
        
        if version is not None:
            return self.secrets_dir / f"{safe_name}.v{version}{SECRET_FILE_EXT}"
        
        # Find the latest version
        versions = []
        for path in self.secrets_dir.glob(f"{safe_name}.v*{SECRET_FILE_EXT}"):
            try:
                v = int(path.stem.split(".v")[1])
                versions.append(v)
            except (ValueError, IndexError):
                continue
        
        if not versions:
            # No versioned files found, try the unversioned file
            return self.secrets_dir / f"{safe_name}{SECRET_FILE_EXT}"
        
        latest_version = max(versions)
        return self.secrets_dir / f"{safe_name}.v{latest_version}{SECRET_FILE_EXT}"

    def _check_access(self, secret_name: str, service_id: str, action: str) -> bool:
        """Check if a service has access to a secret

        Args:
            secret_name: The name of the secret
            service_id: The ID of the service
            action: The action to check (get, set, rotate, delete)

        Returns:
            True if the service has access, False otherwise
        """
        # If no access control is defined for the secret, deny access
        if secret_name not in self.access_control:
            return False
        
        # If the service is not in the access control list, deny access
        if service_id not in self.access_control[secret_name]:
            return False
        
        # Check if the service has the required permission
        return action in self.access_control[secret_name][service_id]

    def set_secret(self, secret_name: str, value: str, service_id: Optional[str] = None,
                  rotate: bool = False) -> bool:
        """Set a secret value

        Args:
            secret_name: The name of the secret
            value: The value of the secret
            service_id: The ID of the service setting the secret
            rotate: Whether to rotate the secret (create a new version)

        Returns:
            True if successful, False otherwise
        """
        try:
            # Check access if service_id is provided
            if service_id and not self._check_access(secret_name, service_id, "set"):
                logger.error(f"Service {service_id} does not have permission to set secret {secret_name}")
                self._log_audit("set", secret_name, service_id, False, "Access denied")
                return False

            # Create metadata
            metadata = {
                "name": secret_name,
                "created_at": datetime.datetime.now().isoformat(),
                "created_by": service_id,
                "rotation_due": (datetime.datetime.now() + 
                               datetime.timedelta(days=self.config["rotation_days"])).isoformat()
            }

            # Determine the version
            version = None
            if rotate:
                # Find the current version
                versions = []
                safe_name = secret_name.replace("/", "_")
                for path in self.secrets_dir.glob(f"{safe_name}.v*{SECRET_FILE_EXT}"):
                    try:
                        v = int(path.stem.split(".v")[1])
                        versions.append(v)
                    except (ValueError, IndexError):
                        continue
                
                version = max(versions) + 1 if versions else 1
                metadata["version"] = version

            # Encrypt the value
            data_to_encrypt = json.dumps({
                "value": value,
                "metadata": metadata
            })
            encrypted_data, salt = self._encrypt(data_to_encrypt, secret_name)

            # Determine the file path
            if version is not None:
                safe_name = secret_name.replace("/", "_")
                file_path = self.secrets_dir / f"{safe_name}.v{version}{SECRET_FILE_EXT}"
            else:
                file_path = self._get_secret_path(secret_name)

            # Save the encrypted data and salt
            with open(file_path, "wb") as f:
                # Format: salt (16 bytes) + encrypted_data
                f.write(salt + encrypted_data)

            # Set file permissions to be readable only by the owner
            os.chmod(file_path, 0o600)

            # If using AWS Secrets Manager
            if self.use_aws and self.aws_client:
                aws_secret_name = self.config["aws"]["prefix"] + secret_name
                try:
                    self.aws_client.create_secret(
                        Name=aws_secret_name,
                        SecretString=value,
                        Description=f"Managed by Dollar Funding MCA Secret Manager - {metadata['created_at']}"
                    )
                except self.aws_client.exceptions.ResourceExistsException:
                    # Secret already exists, update it
                    self.aws_client.put_secret_value(
                        SecretId=aws_secret_name,
                        SecretString=value
                    )
                logger.debug(f"Stored secret in AWS Secrets Manager: {aws_secret_name}")

            # If using HashiCorp Vault
            if self.use_vault and self.vault_client:
                vault_path = self.config["vault"]["path_prefix"] + secret_name
                mount_point = self.config["vault"]["mount_point"]
                
                self.vault_client.secrets.kv.v2.create_or_update_secret(
                    path=vault_path,
                    secret={"value": value},
                    mount_point=mount_point,
                    metadata={"created_at": metadata["created_at"]}
                )
                logger.debug(f"Stored secret in HashiCorp Vault: {vault_path}")

            # Log the audit entry
            action = "rotate" if rotate else "set"
            self._log_audit(action, secret_name, service_id, True)

            logger.info(f"Successfully {'rotated' if rotate else 'set'} secret: {secret_name}")
            return True

        except Exception as e:
            logger.error(f"Failed to set secret {secret_name}: {e}")
            self._log_audit("set", secret_name, service_id, False, str(e))
            return False

    def get_secret(self, secret_name: str, service_id: Optional[str] = None,
                 version: Optional[int] = None) -> Optional[str]:
        """Get a secret value

        Args:
            secret_name: The name of the secret
            service_id: The ID of the service getting the secret
            version: The version of the secret (None for latest)

        Returns:
            The secret value, or None if not found or access denied
        """
        try:
            # Check access if service_id is provided
            if service_id and not self._check_access(secret_name, service_id, "get"):
                logger.error(f"Service {service_id} does not have permission to get secret {secret_name}")
                self._log_audit("get", secret_name, service_id, False, "Access denied")
                return None

            # If using AWS Secrets Manager and no specific version is requested
            if self.use_aws and self.aws_client and version is None:
                aws_secret_name = self.config["aws"]["prefix"] + secret_name
                try:
                    response = self.aws_client.get_secret_value(SecretId=aws_secret_name)
                    value = response["SecretString"]
                    logger.debug(f"Retrieved secret from AWS Secrets Manager: {aws_secret_name}")
                    self._log_audit("get", secret_name, service_id, True, "Retrieved from AWS Secrets Manager")
                    return value
                except self.aws_client.exceptions.ResourceNotFoundException:
                    logger.debug(f"Secret not found in AWS Secrets Manager: {aws_secret_name}")
                    # Fall back to local storage
                except Exception as e:
                    logger.warning(f"Failed to get secret from AWS Secrets Manager: {e}")
                    # Fall back to local storage

            # If using HashiCorp Vault and no specific version is requested
            if self.use_vault and self.vault_client and version is None:
                vault_path = self.config["vault"]["path_prefix"] + secret_name
                mount_point = self.config["vault"]["mount_point"]
                
                try:
                    response = self.vault_client.secrets.kv.v2.read_secret_version(
                        path=vault_path,
                        mount_point=mount_point
                    )
                    value = response["data"]["data"]["value"]
                    logger.debug(f"Retrieved secret from HashiCorp Vault: {vault_path}")
                    self._log_audit("get", secret_name, service_id, True, "Retrieved from HashiCorp Vault")
                    return value
                except Exception as e:
                    logger.warning(f"Failed to get secret from HashiCorp Vault: {e}")
                    # Fall back to local storage

            # Get the secret from local storage
            file_path = self._get_secret_path(secret_name, version)
            
            if not file_path.exists():
                logger.error(f"Secret not found: {secret_name}")
                self._log_audit("get", secret_name, service_id, False, "Secret not found")
                return None

            # Read the encrypted data and salt
            with open(file_path, "rb") as f:
                data = f.read()
                salt = data[:16]  # First 16 bytes are the salt
                encrypted_data = data[16:]  # Rest is the encrypted data

            # Decrypt the data
            decrypted_data = self._decrypt(encrypted_data, salt, secret_name)
            secret_data = json.loads(decrypted_data.decode())

            # Log the audit entry
            self._log_audit("get", secret_name, service_id, True)

            logger.debug(f"Retrieved secret: {secret_name}")
            return secret_data["value"]

        except Exception as e:
            logger.error(f"Failed to get secret {secret_name}: {e}")
            self._log_audit("get", secret_name, service_id, False, str(e))
            return None

    def list_secrets(self, service_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """List available secrets

        Args:
            service_id: The ID of the service listing secrets

        Returns:
            List of secret metadata
        """
        try:
            secrets = []

            # Get secrets from local storage
            for file_path in self.secrets_dir.glob(f"*{SECRET_FILE_EXT}"):
                try:
                    # Extract the secret name from the file name
                    file_name = file_path.stem
                    if ".v" in file_name:
                        # Versioned file
                        secret_name, version = file_name.split(".v")
                    else:
                        # Unversioned file
                        secret_name = file_name
                        version = "latest"

                    # Replace underscores with slashes in the secret name
                    secret_name = secret_name.replace("_", "/")

                    # Check access if service_id is provided
                    if service_id and not self._check_access(secret_name, service_id, "list"):
                        continue

                    # Read the encrypted data and salt
                    with open(file_path, "rb") as f:
                        data = f.read()
                        salt = data[:16]  # First 16 bytes are the salt
                        encrypted_data = data[16:]  # Rest is the encrypted data

                    # Decrypt the data
                    decrypted_data = self._decrypt(encrypted_data, salt, secret_name)
                    secret_data = json.loads(decrypted_data.decode())

                    # Add metadata to the list
                    secrets.append({
                        "name": secret_name,
                        "version": version,
                        "metadata": secret_data["metadata"]
                    })
                except Exception as e:
                    logger.warning(f"Failed to process secret file {file_path}: {e}")

            # If using AWS Secrets Manager
            if self.use_aws and self.aws_client:
                try:
                    aws_prefix = self.config["aws"]["prefix"]
                    response = self.aws_client.list_secrets(
                        Filters=[
                            {
                                "Key": "name",
                                "Values": [aws_prefix]
                            }
                        ]
                    )

                    for secret in response["SecretList"]:
                        # Extract the secret name without the prefix
                        name = secret["Name"]
                        if name.startswith(aws_prefix):
                            name = name[len(aws_prefix):]

                        # Check access if service_id is provided
                        if service_id and not self._check_access(name, service_id, "list"):
                            continue

                        # Add to the list if not already present
                        if not any(s["name"] == name for s in secrets):
                            secrets.append({
                                "name": name,
                                "version": "latest",
                                "metadata": {
                                    "created_at": secret.get("CreatedDate", "").isoformat() if hasattr(secret.get("CreatedDate", ""), "isoformat") else "",
                                    "aws_managed": True
                                }
                            })
                except Exception as e:
                    logger.warning(f"Failed to list secrets from AWS Secrets Manager: {e}")

            # If using HashiCorp Vault
            if self.use_vault and self.vault_client:
                try:
                    vault_prefix = self.config["vault"]["path_prefix"]
                    mount_point = self.config["vault"]["mount_point"]
                    
                    # List secrets in Vault
                    response = self.vault_client.secrets.kv.v2.list_secrets(
                        path=vault_prefix,
                        mount_point=mount_point
                    )

                    for key in response.get("data", {}).get("keys", []):
                        name = key
                        
                        # Check access if service_id is provided
                        if service_id and not self._check_access(name, service_id, "list"):
                            continue

                        # Add to the list if not already present
                        if not any(s["name"] == name for s in secrets):
                            secrets.append({
                                "name": name,
                                "version": "latest",
                                "metadata": {
                                    "vault_managed": True
                                }
                            })
                except Exception as e:
                    logger.warning(f"Failed to list secrets from HashiCorp Vault: {e}")

            # Log the audit entry
            self._log_audit("list", "*", service_id, True)

            logger.debug(f"Listed {len(secrets)} secrets")
            return secrets

        except Exception as e:
            logger.error(f"Failed to list secrets: {e}")
            self._log_audit("list", "*", service_id, False, str(e))
            return []

    def rotate_secret(self, secret_name: str, value: str, service_id: Optional[str] = None) -> bool:
        """Rotate a secret (create a new version)

        Args:
            secret_name: The name of the secret
            value: The new value of the secret
            service_id: The ID of the service rotating the secret

        Returns:
            True if successful, False otherwise
        """
        return self.set_secret(secret_name, value, service_id, rotate=True)

    def delete_secret(self, secret_name: str, service_id: Optional[str] = None,
                    version: Optional[int] = None) -> bool:
        """Delete a secret

        Args:
            secret_name: The name of the secret
            service_id: The ID of the service deleting the secret
            version: The version of the secret to delete (None for all versions)

        Returns:
            True if successful, False otherwise
        """
        try:
            # Check access if service_id is provided
            if service_id and not self._check_access(secret_name, service_id, "delete"):
                logger.error(f"Service {service_id} does not have permission to delete secret {secret_name}")
                self._log_audit("delete", secret_name, service_id, False, "Access denied")
                return False

            # Delete from local storage
            if version is not None:
                # Delete specific version
                file_path = self._get_secret_path(secret_name, version)
                if file_path.exists():
                    file_path.unlink()
                    logger.debug(f"Deleted secret version {version}: {secret_name}")
            else:
                # Delete all versions
                safe_name = secret_name.replace("/", "_")
                for file_path in self.secrets_dir.glob(f"{safe_name}*{SECRET_FILE_EXT}"):
                    file_path.unlink()
                logger.debug(f"Deleted all versions of secret: {secret_name}")

            # If using AWS Secrets Manager
            if self.use_aws and self.aws_client and version is None:
                aws_secret_name = self.config["aws"]["prefix"] + secret_name
                try:
                    self.aws_client.delete_secret(
                        SecretId=aws_secret_name,
                        ForceDeleteWithoutRecovery=True
                    )
                    logger.debug(f"Deleted secret from AWS Secrets Manager: {aws_secret_name}")
                except self.aws_client.exceptions.ResourceNotFoundException:
                    logger.debug(f"Secret not found in AWS Secrets Manager: {aws_secret_name}")
                except Exception as e:
                    logger.warning(f"Failed to delete secret from AWS Secrets Manager: {e}")

            # If using HashiCorp Vault
            if self.use_vault and self.vault_client:
                vault_path = self.config["vault"]["path_prefix"] + secret_name
                mount_point = self.config["vault"]["mount_point"]
                
                try:
                    if version is not None:
                        # Delete specific version
                        self.vault_client.secrets.kv.v2.delete_version(
                            path=vault_path,
                            versions=[version],
                            mount_point=mount_point
                        )
                        logger.debug(f"Deleted secret version {version} from HashiCorp Vault: {vault_path}")
                    else:
                        # Delete all versions
                        self.vault_client.secrets.kv.v2.delete_metadata_and_all_versions(
                            path=vault_path,
                            mount_point=mount_point
                        )
                        logger.debug(f"Deleted all versions of secret from HashiCorp Vault: {vault_path}")
                except Exception as e:
                    logger.warning(f"Failed to delete secret from HashiCorp Vault: {e}")

            # Log the audit entry
            self._log_audit("delete", secret_name, service_id, True)

            logger.info(f"Successfully deleted secret: {secret_name}")
            return True

        except Exception as e:
            logger.error(f"Failed to delete secret {secret_name}: {e}")
            self._log_audit("delete", secret_name, service_id, False, str(e))
            return False

    def grant_access(self, secret_name: str, service_id: str, permissions: List[str],
                    granter_id: Optional[str] = None) -> bool:
        """Grant access to a secret for a service

        Args:
            secret_name: The name of the secret
            service_id: The ID of the service to grant access to
            permissions: The permissions to grant (get, set, rotate, delete, list)
            granter_id: The ID of the service granting access

        Returns:
            True if successful, False otherwise
        """
        try:
            # Check if the granter has admin access
            if granter_id and not self._check_access(secret_name, granter_id, "admin"):
                logger.error(f"Service {granter_id} does not have permission to grant access to secret {secret_name}")
                self._log_audit("grant_access", secret_name, granter_id, False, "Access denied")
                return False

            # Initialize access control for the secret if it doesn't exist
            if secret_name not in self.access_control:
                self.access_control[secret_name] = {}

            # Initialize access control for the service if it doesn't exist
            if service_id not in self.access_control[secret_name]:
                self.access_control[secret_name][service_id] = []

            # Add the permissions
            for permission in permissions:
                if permission not in self.access_control[secret_name][service_id]:
                    self.access_control[secret_name][service_id].append(permission)

            # Save the access control
            with open(self.access_control_file, "w") as f:
                json.dump(self.access_control, f, indent=2)

            # Log the audit entry
            self._log_audit("grant_access", secret_name, granter_id, True,
                          f"Granted {', '.join(permissions)} to {service_id}")

            logger.info(f"Granted {', '.join(permissions)} access to {service_id} for secret {secret_name}")
            return True

        except Exception as e:
            logger.error(f"Failed to grant access to secret {secret_name}: {e}")
            self._log_audit("grant_access", secret_name, granter_id, False, str(e))
            return False

    def revoke_access(self, secret_name: str, service_id: str, permissions: Optional[List[str]] = None,
                     revoker_id: Optional[str] = None) -> bool:
        """Revoke access to a secret for a service

        Args:
            secret_name: The name of the secret
            service_id: The ID of the service to revoke access from
            permissions: The permissions to revoke (None for all)
            revoker_id: The ID of the service revoking access

        Returns:
            True if successful, False otherwise
        """
        try:
            # Check if the revoker has admin access
            if revoker_id and not self._check_access(secret_name, revoker_id, "admin"):
                logger.error(f"Service {revoker_id} does not have permission to revoke access to secret {secret_name}")
                self._log_audit("revoke_access", secret_name, revoker_id, False, "Access denied")
                return False

            # Check if the secret exists in access control
            if secret_name not in self.access_control:
                logger.error(f"Secret {secret_name} not found in access control")
                self._log_audit("revoke_access", secret_name, revoker_id, False, "Secret not found")
                return False

            # Check if the service exists in access control
            if service_id not in self.access_control[secret_name]:
                logger.error(f"Service {service_id} not found in access control for secret {secret_name}")
                self._log_audit("revoke_access", secret_name, revoker_id, False, "Service not found")
                return False

            if permissions is None:
                # Revoke all permissions
                del self.access_control[secret_name][service_id]
                logger.debug(f"Revoked all permissions for {service_id} on secret {secret_name}")
            else:
                # Revoke specific permissions
                for permission in permissions:
                    if permission in self.access_control[secret_name][service_id]:
                        self.access_control[secret_name][service_id].remove(permission)
                logger.debug(f"Revoked {', '.join(permissions)} for {service_id} on secret {secret_name}")

            # Remove the service if it has no permissions left
            if service_id in self.access_control[secret_name] and not self.access_control[secret_name][service_id]:
                del self.access_control[secret_name][service_id]

            # Remove the secret if it has no services left
            if secret_name in self.access_control and not self.access_control[secret_name]:
                del self.access_control[secret_name]

            # Save the access control
            with open(self.access_control_file, "w") as f:
                json.dump(self.access_control, f, indent=2)

            # Log the audit entry
            details = f"Revoked all permissions from {service_id}" if permissions is None else \
                     f"Revoked {', '.join(permissions)} from {service_id}"
            self._log_audit("revoke_access", secret_name, revoker_id, True, details)

            logger.info(f"Revoked access for {service_id} to secret {secret_name}")
            return True

        except Exception as e:
            logger.error(f"Failed to revoke access to secret {secret_name}: {e}")
            self._log_audit("revoke_access", secret_name, revoker_id, False, str(e))
            return False

    def get_audit_logs(self, secret_name: Optional[str] = None, service_id: Optional[str] = None,
                      action: Optional[str] = None, start_time: Optional[str] = None,
                      end_time: Optional[str] = None, limit: int = 100) -> List[Dict[str, Any]]:
        """Get audit logs for secret operations

        Args:
            secret_name: Filter by secret name
            service_id: Filter by service ID
            action: Filter by action
            start_time: Filter by start time (ISO format)
            end_time: Filter by end time (ISO format)
            limit: Maximum number of logs to return

        Returns:
            List of audit log entries
        """
        try:
            logs = []

            # Parse start and end times
            start_dt = datetime.datetime.fromisoformat(start_time) if start_time else None
            end_dt = datetime.datetime.fromisoformat(end_time) if end_time else None

            # Read the audit log file
            if self.audit_log_file.exists():
                with open(self.audit_log_file, "r") as f:
                    for line in f:
                        try:
                            entry = json.loads(line.strip())

                            # Apply filters
                            if secret_name and entry["secret_name"] != secret_name and entry["secret_name"] != "*":
                                continue

                            if service_id and entry["service_id"] != service_id:
                                continue

                            if action and entry["action"] != action:
                                continue

                            if start_dt:
                                entry_dt = datetime.datetime.fromisoformat(entry["timestamp"])
                                if entry_dt < start_dt:
                                    continue

                            if end_dt:
                                entry_dt = datetime.datetime.fromisoformat(entry["timestamp"])
                                if entry_dt > end_dt:
                                    continue

                            logs.append(entry)

                            # Apply limit
                            if len(logs) >= limit:
                                break
                        except Exception as e:
                            logger.warning(f"Failed to parse audit log entry: {e}")

            logger.debug(f"Retrieved {len(logs)} audit log entries")
            return logs

        except Exception as e:
            logger.error(f"Failed to get audit logs: {e}")
            return []

    def import_from_aws(self, prefix: Optional[str] = None, service_id: Optional[str] = None) -> bool:
        """Import secrets from AWS Secrets Manager

        Args:
            prefix: The prefix to filter secrets by
            service_id: The ID of the service importing secrets

        Returns:
            True if successful, False otherwise
        """
        if not self.use_aws or not self.aws_client:
            logger.error("AWS Secrets Manager is not enabled")
            return False

        try:
            # Use the configured prefix if none is provided
            if prefix is None:
                prefix = self.config["aws"]["prefix"]

            # List secrets in AWS Secrets Manager
            response = self.aws_client.list_secrets(
                Filters=[
                    {
                        "Key": "name",
                        "Values": [prefix]
                    }
                ]
            )

            success_count = 0
            failure_count = 0

            for secret in response["SecretList"]:
                try:
                    # Extract the secret name without the prefix
                    name = secret["Name"]
                    if name.startswith(prefix):
                        name = name[len(prefix):]

                    # Get the secret value
                    value_response = self.aws_client.get_secret_value(SecretId=secret["Name"])
                    value = value_response["SecretString"]

                    # Set the secret locally
                    if self.set_secret(name, value, service_id):
                        success_count += 1
                    else:
                        failure_count += 1
                except Exception as e:
                    logger.warning(f"Failed to import secret {secret['Name']}: {e}")
                    failure_count += 1

            # Log the audit entry
            self._log_audit("import", f"aws:{prefix}*", service_id, True,
                          f"Imported {success_count} secrets, {failure_count} failures")

            logger.info(f"Imported {success_count} secrets from AWS Secrets Manager, {failure_count} failures")
            return success_count > 0 and failure_count == 0

        except Exception as e:
            logger.error(f"Failed to import secrets from AWS Secrets Manager: {e}")
            self._log_audit("import", f"aws:{prefix}*", service_id, False, str(e))
            return False

    def import_from_vault(self, path: Optional[str] = None, service_id: Optional[str] = None) -> bool:
        """Import secrets from HashiCorp Vault

        Args:
            path: The path to filter secrets by
            service_id: The ID of the service importing secrets

        Returns:
            True if successful, False otherwise
        """
        if not self.use_vault or not self.vault_client:
            logger.error("HashiCorp Vault is not enabled")
            return False

        try:
            # Use the configured path if none is provided
            if path is None:
                path = self.config["vault"]["path_prefix"]

            mount_point = self.config["vault"]["mount_point"]

            # List secrets in Vault
            response = self.vault_client.secrets.kv.v2.list_secrets(
                path=path,
                mount_point=mount_point
            )

            success_count = 0
            failure_count = 0

            for key in response.get("data", {}).get("keys", []):
                try:
                    # Get the secret value
                    secret_path = f"{path}{key}"
                    secret_response = self.vault_client.secrets.kv.v2.read_secret_version(
                        path=secret_path,
                        mount_point=mount_point
                    )

                    # Extract the value
                    value = secret_response["data"]["data"]["value"]

                    # Set the secret locally
                    if self.set_secret(key, value, service_id):
                        success_count += 1
                    else:
                        failure_count += 1
                except Exception as e:
                    logger.warning(f"Failed to import secret {key}: {e}")
                    failure_count += 1

            # Log the audit entry
            self._log_audit("import", f"vault:{path}*", service_id, True,
                          f"Imported {success_count} secrets, {failure_count} failures")

            logger.info(f"Imported {success_count} secrets from HashiCorp Vault, {failure_count} failures")
            return success_count > 0 and failure_count == 0

        except Exception as e:
            logger.error(f"Failed to import secrets from HashiCorp Vault: {e}")
            self._log_audit("import", f"vault:{path}*", service_id, False, str(e))
            return False

    def export_to_aws(self, secret_names: List[str], service_id: Optional[str] = None) -> bool:
        """Export secrets to AWS Secrets Manager

        Args:
            secret_names: The names of the secrets to export
            service_id: The ID of the service exporting secrets

        Returns:
            True if successful, False otherwise
        """
        if not self.use_aws or not self.aws_client:
            logger.error("AWS Secrets Manager is not enabled")
            return False

        try:
            success_count = 0
            failure_count = 0

            for secret_name in secret_names:
                try:
                    # Check access if service_id is provided
                    if service_id and not self._check_access(secret_name, service_id, "export"):
                        logger.error(f"Service {service_id} does not have permission to export secret {secret_name}")
                        failure_count += 1
                        continue

                    # Get the secret value
                    value = self.get_secret(secret_name, service_id)
                    if value is None:
                        logger.error(f"Secret not found: {secret_name}")
                        failure_count += 1
                        continue

                    # Export to AWS Secrets Manager
                    aws_secret_name = self.config["aws"]["prefix"] + secret_name
                    try:
                        self.aws_client.create_secret(
                            Name=aws_secret_name,
                            SecretString=value,
                            Description=f"Exported by Dollar Funding MCA Secret Manager - {datetime.datetime.now().isoformat()}"
                        )
                    except self.aws_client.exceptions.ResourceExistsException:
                        # Secret already exists, update it
                        self.aws_client.put_secret_value(
                            SecretId=aws_secret_name,
                            SecretString=value
                        )

                    success_count += 1
                    logger.debug(f"Exported secret to AWS Secrets Manager: {aws_secret_name}")
                except Exception as e:
                    logger.warning(f"Failed to export secret {secret_name}: {e}")
                    failure_count += 1

            # Log the audit entry
            self._log_audit("export", "aws:*", service_id, True,
                          f"Exported {success_count} secrets, {failure_count} failures")

            logger.info(f"Exported {success_count} secrets to AWS Secrets Manager, {failure_count} failures")
            return success_count > 0 and failure_count == 0

        except Exception as e:
            logger.error(f"Failed to export secrets to AWS Secrets Manager: {e}")
            self._log_audit("export", "aws:*", service_id, False, str(e))
            return False

    def export_to_vault(self, secret_names: List[str], service_id: Optional[str] = None) -> bool:
        """Export secrets to HashiCorp Vault

        Args:
            secret_names: The names of the secrets to export
            service_id: The ID of the service exporting secrets

        Returns:
            True if successful, False otherwise
        """
        if not self.use_vault or not self.vault_client:
            logger.error("HashiCorp Vault is not enabled")
            return False

        try:
            success_count = 0
            failure_count = 0

            for secret_name in secret_names:
                try:
                    # Check access if service_id is provided
                    if service_id and not self._check_access(secret_name, service_id, "export"):
                        logger.error(f"Service {service_id} does not have permission to export secret {secret_name}")
                        failure_count += 1
                        continue

                    # Get the secret value
                    value = self.get_secret(secret_name, service_id)
                    if value is None:
                        logger.error(f"Secret not found: {secret_name}")
                        failure_count += 1
                        continue

                    # Export to HashiCorp Vault
                    vault_path = self.config["vault"]["path_prefix"] + secret_name
                    mount_point = self.config["vault"]["mount_point"]
                    
                    self.vault_client.secrets.kv.v2.create_or_update_secret(
                        path=vault_path,
                        secret={"value": value},
                        mount_point=mount_point,
                        metadata={"exported_at": datetime.datetime.now().isoformat()}
                    )

                    success_count += 1
                    logger.debug(f"Exported secret to HashiCorp Vault: {vault_path}")
                except Exception as e:
                    logger.warning(f"Failed to export secret {secret_name}: {e}")
                    failure_count += 1

            # Log the audit entry
            self._log_audit("export", "vault:*", service_id, True,
                          f"Exported {success_count} secrets, {failure_count} failures")

            logger.info(f"Exported {success_count} secrets to HashiCorp Vault, {failure_count} failures")
            return success_count > 0 and failure_count == 0

        except Exception as e:
            logger.error(f"Failed to export secrets to HashiCorp Vault: {e}")
            self._log_audit("export", "vault:*", service_id, False, str(e))
            return False


def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description="Manage secrets securely across environments")
    
    # Global options
    parser.add_argument("-e", "--environment", default="development",
                        choices=["development", "staging", "production"],
                        help="Environment (development, staging, production)")
    parser.add_argument("-v", "--verbose", action="store_true",
                        help="Enable verbose output")
    parser.add_argument("--aws", action="store_true",
                        help="Use AWS Secrets Manager")
    parser.add_argument("--vault", action="store_true",
                        help="Use HashiCorp Vault")
    parser.add_argument("--local", action="store_true",
                        help="Use local encrypted storage (default)")
    parser.add_argument("--config", help="Path to configuration file")
    parser.add_argument("--version", action="version", version=f"%(prog)s {VERSION}")
    
    # Subcommands
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")
    
    # Set command
    set_parser = subparsers.add_parser("set", help="Set a secret value")
    set_parser.add_argument("name", help="Name of the secret")
    set_parser.add_argument("value", nargs="?", help="Value of the secret (if not provided, will prompt)")
    set_parser.add_argument("--service-id", help="ID of the service setting the secret")
    
    # Get command
    get_parser = subparsers.add_parser("get", help="Get a secret value")
    get_parser.add_argument("name", help="Name of the secret")
    get_parser.add_argument("--service-id", help="ID of the service getting the secret")
    get_parser.add_argument("--version", type=int, help="Version of the secret")
    
    # List command
    list_parser = subparsers.add_parser("list", help="List available secrets")
    list_parser.add_argument("--service-id", help="ID of the service listing secrets")
    
    # Rotate command
    rotate_parser = subparsers.add_parser("rotate", help="Rotate a secret")
    rotate_parser.add_argument("name", help="Name of the secret")
    rotate_parser.add_argument("value", nargs="?", help="New value of the secret (if not provided, will prompt)")
    rotate_parser.add_argument("--service-id", help="ID of the service rotating the secret")
    
    # Delete command
    delete_parser = subparsers.add_parser("delete", help="Delete a secret")
    delete_parser.add_argument("name", help="Name of the secret")
    delete_parser.add_argument("--service-id", help="ID of the service deleting the secret")
    delete_parser.add_argument("--version", type=int, help="Version of the secret to delete (None for all versions)")
    
    # Import command
    import_parser = subparsers.add_parser("import", help="Import secrets from external systems")
    import_parser.add_argument("--aws-prefix", help="Prefix for AWS Secrets Manager")
    import_parser.add_argument("--vault-path", help="Path for HashiCorp Vault")
    import_parser.add_argument("--service-id", help="ID of the service importing secrets")
    
    # Export command
    export_parser = subparsers.add_parser("export", help="Export secrets to external systems")
    export_parser.add_argument("names", nargs="+", help="Names of the secrets to export")
    export_parser.add_argument("--aws", action="store_true", help="Export to AWS Secrets Manager")
    export_parser.add_argument("--vault", action="store_true", help="Export to HashiCorp Vault")
    export_parser.add_argument("--service-id", help="ID of the service exporting secrets")
    
    # Grant access command
    grant_parser = subparsers.add_parser("grant-access", help="Grant access to a secret for a service")
    grant_parser.add_argument("name", help="Name of the secret")
    grant_parser.add_argument("service_id", help="ID of the service to grant access to")
    grant_parser.add_argument("permissions", nargs="+", choices=["get", "set", "rotate", "delete", "list", "export", "admin"],
                             help="Permissions to grant")
    grant_parser.add_argument("--granter-id", help="ID of the service granting access")
    
    # Revoke access command
    revoke_parser = subparsers.add_parser("revoke-access", help="Revoke access to a secret for a service")
    revoke_parser.add_argument("name", help="Name of the secret")
    revoke_parser.add_argument("service_id", help="ID of the service to revoke access from")
    revoke_parser.add_argument("permissions", nargs="*", choices=["get", "set", "rotate", "delete", "list", "export", "admin"],
                              help="Permissions to revoke (None for all)")
    revoke_parser.add_argument("--revoker-id", help="ID of the service revoking access")
    
    # Audit command
    audit_parser = subparsers.add_parser("audit", help="View audit logs for secret operations")
    audit_parser.add_argument("--secret-name", help="Filter by secret name")
    audit_parser.add_argument("--service-id", help="Filter by service ID")
    audit_parser.add_argument("--action", choices=["set", "get", "list", "rotate", "delete", "import", "export",
                                                 "grant_access", "revoke_access"],
                             help="Filter by action")
    audit_parser.add_argument("--start-time", help="Filter by start time (ISO format)")
    audit_parser.add_argument("--end-time", help="Filter by end time (ISO format)")
    audit_parser.add_argument("--limit", type=int, default=100, help="Maximum number of logs to return")
    
    return parser.parse_args()


def main():
    """Main entry point"""
    args = parse_args()
    
    # If no command is provided, show help and exit
    if args.command is None:
        print(__doc__)
        return
    
    # Initialize the secret manager
    manager = SecretManager(
        environment=args.environment,
        config_path=args.config,
        use_aws=args.aws,
        use_vault=args.vault,
        use_local=args.local or (not args.aws and not args.vault),  # Default to local if no other option is specified
        verbose=args.verbose
    )
    
    # Execute the command
    if args.command == "set":
        # Prompt for value if not provided
        value = args.value
        if value is None:
            value = getpass.getpass("Enter secret value: ")
        
        success = manager.set_secret(args.name, value, args.service_id)
        if not success:
            sys.exit(1)
    
    elif args.command == "get":
        value = manager.get_secret(args.name, args.service_id, args.version)
        if value is None:
            sys.exit(1)
        print(value)
    
    elif args.command == "list":
        secrets = manager.list_secrets(args.service_id)
        if not secrets:
            print("No secrets found")
        else:
            print(f"Found {len(secrets)} secrets:")
            for secret in secrets:
                print(f"- {secret['name']} (version: {secret['version']})")
                if args.verbose:
                    for key, value in secret.get("metadata", {}).items():
                        print(f"  {key}: {value}")
    
    elif args.command == "rotate":
        # Prompt for value if not provided
        value = args.value
        if value is None:
            value = getpass.getpass("Enter new secret value: ")
        
        success = manager.rotate_secret(args.name, value, args.service_id)
        if not success:
            sys.exit(1)
    
    elif args.command == "delete":
        success = manager.delete_secret(args.name, args.service_id, args.version)
        if not success:
            sys.exit(1)
    
    elif args.command == "import":
        if args.aws and args.aws_prefix is not None:
            success = manager.import_from_aws(args.aws_prefix, args.service_id)
            if not success:
                sys.exit(1)
        
        if args.vault and args.vault_path is not None:
            success = manager.import_from_vault(args.vault_path, args.service_id)
            if not success:
                sys.exit(1)
    
    elif args.command == "export":
        if args.aws:
            success = manager.export_to_aws(args.names, args.service_id)
            if not success:
                sys.exit(1)
        
        if args.vault:
            success = manager.export_to_vault(args.names, args.service_id)
            if not success:
                sys.exit(1)
    
    elif args.command == "grant-access":
        success = manager.grant_access(args.name, args.service_id, args.permissions, args.granter_id)
        if not success:
            sys.exit(1)
    
    elif args.command == "revoke-access":
        success = manager.revoke_access(args.name, args.service_id, args.permissions, args.revoker_id)
        if not success:
            sys.exit(1)
    
    elif args.command == "audit":
        logs = manager.get_audit_logs(
            secret_name=args.secret_name,
            service_id=args.service_id,
            action=args.action,
            start_time=args.start_time,
            end_time=args.end_time,
            limit=args.limit
        )
        
        if not logs:
            print("No audit logs found")
        else:
            print(f"Found {len(logs)} audit logs:")
            for log in logs:
                timestamp = log["timestamp"]
                action = log["action"]
                secret_name = log["secret_name"]
                service_id = log["service_id"] or "unknown"
                success = "success" if log["success"] else "failure"
                details = log.get("details", "")
                
                print(f"[{timestamp}] {action.upper()} {secret_name} by {service_id} - {success}")
                if details:
                    print(f"  Details: {details}")


if __name__ == "__main__":
    main()