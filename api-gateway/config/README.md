# Kong API Gateway Configuration

## Overview

This directory contains the configuration files for the Kong API Gateway (version 3.5.0), which serves as the unified entry point for all API requests in the Merchant Cash Advance (MCA) Application Processing System. The gateway provides consistent security controls, request routing, and monitoring across all backend microservices.

## Role in System Architecture

The Kong API Gateway serves as:

- **Unified Entry Point**: Single access point for all frontend client requests
- **Security Boundary**: Primary security layer implementing multiple protection mechanisms
- **Request Router**: Directs traffic to appropriate backend microservices
- **Cross-Cutting Concerns Handler**: Manages authentication, rate limiting, and monitoring

## Configuration Structure

This directory uses a declarative configuration approach for version control while supporting database-backed deployment for dynamic updates.

### File Organization

```
config/
├── README.md                 # This documentation file
├── kong.yml                  # Main declarative configuration file
├── routes/                   # Route-specific configurations
│   ├── applications.yml      # Application API routes
│   ├── documents.yml         # Document API routes
│   └── webhooks.yml          # Webhook configuration routes
├── plugins/                  # Plugin configurations
│   ├── authentication.yml    # JWT authentication settings
│   ├── rate-limiting.yml     # Rate limiting policies
│   ├── cors.yml              # CORS configuration
│   └── security.yml          # Additional security plugins
└── certificates/            # TLS certificates (referenced only, not stored in repo)
```

### Key Configuration Files

- **kong.yml**: The main configuration file that defines services, routes, and global plugins. This file serves as the entry point for Kong's declarative configuration.

- **routes/*.yml**: Individual route configurations for different API groups. These files define the paths, methods, and service mappings for each API endpoint.

- **plugins/*.yml**: Plugin-specific configurations that implement security features, monitoring, and other cross-cutting concerns.

## Deployment Process

The Kong API Gateway is deployed using a database-backed configuration approach, which allows for dynamic updates while maintaining version control through declarative configuration files.

### Initial Deployment

1. **Database Initialization**:
   ```bash
   kong migrations bootstrap
   ```

2. **Configuration Loading**:
   ```bash
   kong config db_import kong.yml
   ```

3. **Gateway Start**:
   ```bash
   kong start
   ```

### Configuration Updates

1. **Update Configuration Files**: Modify the relevant YAML files in this directory

2. **Validate Configuration**:
   ```bash
   kong config parse kong.yml
   ```

3. **Apply Changes**:
   ```bash
   kong config db_import kong.yml
   ```

4. **Verify Deployment**:
   ```bash
   kong config db_export
   ```

## Security Features

The Kong API Gateway implements multiple layers of security:

### JWT Authentication

- **Algorithm**: RS256 (asymmetric key signing)
- **Validation**: Token expiration, issuer validation, and audience verification
- **Key Rotation**: Automatic key rotation support

### Rate Limiting

- **Authenticated Users**: 60 requests per minute
- **Unauthenticated Requests**: 10 requests per minute
- **Administrative Endpoints**: Custom limits based on endpoint sensitivity

### CORS Policies

- **Allowed Origins**: Explicitly configured for frontend domains
- **Allowed Methods**: Restricted to required HTTP methods
- **Allowed Headers**: Limited to necessary request headers
- **Pre-flight Caching**: Optimized for performance while maintaining security

### Request Transformation

- **Security Headers**: Automatic addition of security headers
- **Request Sanitization**: Removal of potentially harmful metadata

### IP Filtering

- **Administrative Endpoints**: Restricted by IP allowlists
- **Blocked Request Logging**: Audit logging of denied access attempts

## Management Guidelines

### Adding New Routes

1. Create a new route configuration in the `routes/` directory or update an existing one
2. Define the path, methods, and target service
3. Specify any route-specific plugins
4. Validate and import the configuration

### Configuring Plugins

1. Modify the relevant plugin configuration in the `plugins/` directory
2. For global plugins, update the `kong.yml` file
3. For route-specific plugins, update the appropriate route configuration
4. Validate and import the configuration

### Monitoring and Logging

- Kong Admin API provides access to gateway metrics and status
- Logs are forwarded to the centralized logging system
- Prometheus metrics are exposed for monitoring dashboards

## Troubleshooting

### Common Issues

1. **Authentication Failures**:
   - Verify JWT configuration in `plugins/authentication.yml`
   - Check public key configuration
   - Validate token format and claims

2. **Rate Limiting Problems**:
   - Review rate limit settings in `plugins/rate-limiting.yml`
   - Check Redis configuration for distributed rate limiting
   - Verify consumer identification

3. **Routing Errors**:
   - Confirm route definitions in `routes/` directory
   - Check service availability
   - Verify path and method configurations

4. **Plugin Conflicts**:
   - Review plugin execution order
   - Check for conflicting plugin configurations
   - Validate plugin compatibility

### Diagnostic Commands

```bash
# Check Kong status
kong health

# List all routes
kong config db_export | grep -A 10 routes:

# List all services
kong config db_export | grep -A 10 services:

# Check specific plugin configuration
kong config db_export | grep -A 20 "name: jwt"
```

## References

- [Kong Documentation](https://docs.konghq.com/)
- [Kong Plugins](https://docs.konghq.com/hub/)
- [Declarative Configuration Format](https://docs.konghq.com/gateway/latest/reference/db-less-and-declarative-config/)
- [Kong Admin API](https://docs.konghq.com/gateway/latest/admin-api/)