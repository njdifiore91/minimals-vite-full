# Kong API Gateway Configuration

## Overview

This directory contains the configuration files for the Kong API Gateway (version 3.5.0), which serves as the unified entry point for all API requests in the Merchant Cash Advance (MCA) Application Processing System. The gateway provides consistent security controls, request routing, and monitoring across all microservices.

## Gateway Role in System Architecture

The Kong API Gateway serves as the primary security boundary for all external requests, implementing multiple layers of protection:

- **Unified Entry Point**: All frontend requests pass through the gateway before reaching backend services
- **Security Controls**: Centralized authentication, authorization, and rate limiting
- **Request Routing**: Dynamic routing to appropriate microservices
- **Monitoring**: Request logging and performance tracking
- **Cross-Cutting Concerns**: CORS, request/response transformation, and error handling

## Configuration Structure

### Main Configuration Files

- **kong.yml**: The primary declarative configuration file that defines all services, routes, plugins, and consumers. This file serves as the single source of truth for the gateway's behavior.

### JWT Authentication Files

The `jwt-keys/` directory contains files related to JWT authentication:

- **jwt_config.json**: Configuration for the JWT plugin including validation parameters
- **README.md**: Documentation for JWT key management
- **key_rotation.md**: Procedures for rotating JWT signing keys

## Deployment Process

The Kong API Gateway is deployed using a hybrid approach:

1. **Database-Backed Configuration**: The gateway uses a PostgreSQL database to store its runtime configuration, allowing for dynamic updates through the Admin API.

2. **Declarative Configuration**: The `kong.yml` file provides a version-controlled representation of the gateway configuration that can be applied using the `kong config` commands.

### Deployment Steps

1. **Initial Setup**:
   ```bash
   # Apply the declarative configuration
   kong config db_import ./kong.yml
   ```

2. **Configuration Updates**:
   ```bash
   # Update the configuration
   kong config db_import ./kong.yml
   ```

3. **Validation**:
   ```bash
   # Validate configuration before applying
   kong config parse ./kong.yml
   ```

## Security Plugin Configurations

The gateway implements several security plugins:

### JWT Authentication

The JWT plugin validates tokens using RS256 asymmetric key signing with the following parameters:
- Algorithm: RS256
- Token expiry: 60 minutes
- Refresh token: 7 days

JWT validation includes token expiration, issuer validation, and audience verification to prevent token forgery or replay attacks.

### Rate Limiting

Tiered rate limiting is enforced with the following default limits:
- Authenticated users: 60 requests per minute
- Unauthenticated requests: 10 requests per minute

Rate limits are stored in Redis to ensure consistent enforcement across multiple gateway instances.

### CORS Policies

Strict Cross-Origin Resource Sharing policies are configured with explicit allowed origins, methods, and headers. Pre-flight request caching is optimized for performance while maintaining security boundaries.

### IP Restriction

Configurable IP-based access controls for administrative endpoints with allowlist functionality and audit logging of blocked requests.

## Updating Configurations

### Making Configuration Changes

1. **Edit the declarative configuration file**:
   - Modify `kong.yml` to add/update services, routes, or plugins
   - Follow the Kong declarative configuration format (https://docs.konghq.com/gateway/latest/reference/db-less-and-declarative-config/)

2. **Validate the configuration**:
   ```bash
   kong config parse ./kong.yml
   ```

3. **Apply the configuration**:
   ```bash
   kong config db_import ./kong.yml
   ```

4. **Verify the changes**:
   ```bash
   # List all services
   curl http://localhost:8001/services
   
   # List all routes
   curl http://localhost:8001/routes
   
   # List all plugins
   curl http://localhost:8001/plugins
   ```

### JWT Key Rotation

For JWT key rotation procedures, refer to the `jwt-keys/key_rotation.md` document, which provides detailed steps for both scheduled and emergency key rotations.

## Troubleshooting

### Common Issues

1. **JWT Authentication Failures**:
   - Check token expiration
   - Verify the correct public key is being used
   - Ensure the token contains the required claims (iss, aud, exp)

2. **Rate Limiting Issues**:
   - Verify Redis connection
   - Check rate limit configuration
   - Examine rate limit headers in responses

3. **CORS Errors**:
   - Confirm the origin is in the allowed list
   - Check that the required methods and headers are permitted
   - Verify pre-flight requests are being handled correctly

4. **Routing Problems**:
   - Validate route path patterns
   - Check service host and port configurations
   - Examine route priorities for conflicts

### Logs and Monitoring

Kong logs are available at the following locations:

- **Access Logs**: `/var/log/kong/access.log`
- **Error Logs**: `/var/log/kong/error.log`

For detailed troubleshooting, increase the log level in `kong.conf`:

```
log_level = debug  # Options: debug, info, notice, warn, error, crit
```

## References

- [Kong Documentation](https://docs.konghq.com/gateway/latest/)
- [Kong Declarative Configuration Format](https://docs.konghq.com/gateway/latest/reference/db-less-and-declarative-config/)
- [Kong JWT Plugin](https://docs.konghq.com/hub/kong-inc/jwt/)
- [Kong Rate Limiting Plugin](https://docs.konghq.com/hub/kong-inc/rate-limiting/)
- [Kong CORS Plugin](https://docs.konghq.com/hub/kong-inc/cors/)