# Kong API Gateway Dockerfile
# Based on Kong 3.5.0 official image

FROM kong:3.5.0

# Set environment variables
ENV KONG_DATABASE=off \
    KONG_DECLARATIVE_CONFIG=/etc/kong/kong.yml \
    KONG_PROXY_ACCESS_LOG=/dev/stdout \
    KONG_ADMIN_ACCESS_LOG=/dev/stdout \
    KONG_PROXY_ERROR_LOG=/dev/stderr \
    KONG_ADMIN_ERROR_LOG=/dev/stderr \
    KONG_ADMIN_LISTEN=0.0.0.0:8001, 0.0.0.0:8444 ssl \
    KONG_LOG_LEVEL=notice

# Create directory for Kong configuration
RUN mkdir -p /etc/kong/jwt-keys

# Set up volume mounts for configuration files
VOLUME ["/etc/kong"]

# Expose ports
# - 8000: Proxy listener (HTTP)
# - 8443: Proxy listener (HTTPS)
# - 8001: Admin API (HTTP)
# - 8444: Admin API (HTTPS)
EXPOSE 8000 8443 8001 8444

# Set up healthcheck
HEALTHCHECK --interval=10s --timeout=10s --retries=10 \
    CMD kong health

# Use non-root user for security (kong user is already set up in the base image)
USER kong

# Start Kong
CMD ["kong", "docker-start"]