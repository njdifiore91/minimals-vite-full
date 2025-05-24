# Dockerfile for Kong API Gateway 3.5.0
# This Dockerfile configures Kong API Gateway for the MCA Application Processing System
# It serves as the unified API Gateway for all microservices with security controls

FROM kong:3.5.0

# Set environment variables for Kong configuration
# Logging configuration - direct logs to stdout/stderr for container log collection
ENV KONG_PROXY_ACCESS_LOG=/dev/stdout
ENV KONG_ADMIN_ACCESS_LOG=/dev/stdout
ENV KONG_PROXY_ERROR_LOG=/dev/stderr
ENV KONG_ADMIN_ERROR_LOG=/dev/stderr

# Admin API configuration - enable both HTTP and HTTPS access
ENV KONG_ADMIN_LISTEN="0.0.0.0:8001, 0.0.0.0:8444 ssl"

# Proxy listener configuration - enable both HTTP and HTTPS
ENV KONG_PROXY_LISTEN="0.0.0.0:8000, 0.0.0.0:8443 ssl"

# Enable required plugins for MCA Application Processing System
# - JWT authentication for secure API access (RS256 algorithm, 60 min token expiry)
# - Rate limiting with Redis for traffic control
# - Correlation ID for request tracking across services
# - CORS for browser security
# - Response transformer for API response modification
# - Request transformer for API request modification
ENV KONG_PLUGINS="bundled,jwt,rate-limiting,correlation-id,cors,response-transformer,request-transformer"

# Redis configuration for rate limiting and caching
# These will be overridden by environment variables at runtime
# Redis 7.0 is used with 15 minutes TTL for application data and 24 hours for user sessions
ENV KONG_REDIS_HOST=redis
ENV KONG_REDIS_PORT=6379
ENV KONG_REDIS_TIMEOUT=2000

# Default database configuration (will be overridden at runtime)
# PostgreSQL 14 is used in primary-replica configuration
ENV KONG_DATABASE=postgres
ENV KONG_PG_HOST=kong-database
ENV KONG_PG_PORT=5432
ENV KONG_PG_USER=kong
ENV KONG_PG_PASSWORD=kong
ENV KONG_PG_DATABASE=kong

# Create directories for custom configuration and SSL certificates
RUN mkdir -p /usr/local/kong/conf /usr/local/kong/ssl

# Create volume mount points for configuration and certificates
# This allows for updating configurations without rebuilding the image
VOLUME ["/usr/local/kong/conf", "/usr/local/kong/ssl"]

# Expose ports
# - 8000: HTTP proxy port for API traffic
# - 8001: HTTP Admin API port for management
# - 8443: HTTPS proxy port for secure API traffic
# - 8444: HTTPS Admin API port for secure management
EXPOSE 8000 8001 8443 8444

# Set up health check for container orchestration platforms (Kubernetes)
# This allows the orchestration platform to monitor the container health
# and restart it if necessary, ensuring high availability
HEALTHCHECK --interval=10s --timeout=10s --retries=10 \
  CMD kong health

# Use non-root user for security best practices
# This follows the principle of least privilege
USER kong

# Start Kong with the docker-start command which includes proper signal handling
# This ensures graceful shutdown and proper container lifecycle management
CMD ["kong", "docker-start"]