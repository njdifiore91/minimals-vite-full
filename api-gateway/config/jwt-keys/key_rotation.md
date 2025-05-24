# JWT Key Rotation Process for Kong API Gateway

## Introduction

This document outlines the procedures for rotating JWT signing keys in the MCA Application Processing System. Regular key rotation is a security best practice that limits the impact of potential key compromise and ensures the ongoing integrity of our authentication system.

## Overview

The MCA Application Processing System uses RS256 asymmetric key pairs for JWT signing and validation. The private key is used to sign tokens, while the public key is used for validation at the Kong API Gateway layer. This document describes the process for rotating these keys without service disruption.

## Prerequisites

Before beginning the key rotation process, ensure you have:

- Administrative access to the Kong API Gateway
- Access to the JWT key storage location
- OpenSSL installed on your workstation
- Backup of the current keys
- Scheduled maintenance window (for planned rotations)

## Key Rotation Schedule

- **Regular rotation**: Every 90 days
- **Emergency rotation**: Immediately upon suspected compromise

## Planned Key Rotation Procedure

### 1. Generate New Key Pair

```bash
# Create a directory for the new keys
mkdir -p /tmp/new_jwt_keys
cd /tmp/new_jwt_keys

# Generate a new 2048-bit RSA private key
openssl genrsa -out private_key.pem 2048

# Extract the public key from the private key
openssl rsa -in private_key.pem -pubout -out public_key.pem

# Verify the keys
openssl rsa -in private_key.pem -check
openssl rsa -pubin -in public_key.pem -text -noout
```

### 2. Configure Kong for Key Rotation

Kong API Gateway supports multiple public keys for JWT validation during the rotation period. This allows for a smooth transition without invalidating existing tokens.

#### 2.1 Add the New Public Key to Kong

```bash
# Add the new public key to Kong with a unique key ID (kid)
curl -X POST http://kong-admin:8001/jwt-keys \
  --data "key=$(cat public_key.pem)" \
  --data "kid=key-$(date +%Y%m%d)" \
  --data "algorithm=RS256"
```

#### 2.2 Update JWT Plugin Configuration

```bash
# Update the JWT plugin to use both the old and new keys
curl -X PATCH http://kong-admin:8001/plugins/{jwt-plugin-id} \
  --data "config.key_claim_name=kid" \
  --data "config.claims_to_verify=exp,iat,iss,aud"
```

### 3. Update Token Issuing Service

Update the authentication service to use the new private key for signing new tokens. Include the key ID (kid) in the JWT header to identify which public key should be used for validation.

```javascript
// Example JWT header with key ID
const header = {
  alg: 'RS256',
  typ: 'JWT',
  kid: 'key-20230615' // Matches the kid used when adding the key to Kong
};
```

### 4. Transition Period

During the transition period (typically 24-48 hours):

- New tokens will be signed with the new private key
- Existing tokens signed with the old private key will still be valid
- Kong will validate tokens using either key based on the 'kid' claim

### 5. Remove the Old Key

After all old tokens have expired (based on your token expiry time, typically 60 minutes as specified in the technical requirements):

```bash
# List all JWT keys to find the ID of the old key
curl -X GET http://kong-admin:8001/jwt-keys

# Remove the old key
curl -X DELETE http://kong-admin:8001/jwt-keys/{old-key-id}
```

### 6. Secure the New Private Key

Store the new private key securely according to your organization's key management procedures.

## Emergency Key Rotation Procedure

In case of suspected or confirmed private key compromise, follow these steps for immediate key rotation:

### 1. Generate New Key Pair

Follow the same procedure as in the planned rotation to generate a new key pair.

### 2. Invalidate All Existing Tokens

```bash
# Update the JWT plugin to immediately reject tokens with the compromised key
curl -X PATCH http://kong-admin:8001/plugins/{jwt-plugin-id} \
  --data "config.key_claim_name=kid" \
  --data "config.claims_to_verify=exp,iat,iss,aud" \
  --data "config.secret_is_base64=false"

# Remove the compromised key
curl -X DELETE http://kong-admin:8001/jwt-keys/{compromised-key-id}
```

### 3. Add the New Public Key to Kong

```bash
# Add the new public key to Kong
curl -X POST http://kong-admin:8001/jwt-keys \
  --data "key=$(cat public_key.pem)" \
  --data "kid=key-emergency-$(date +%Y%m%d-%H%M%S)" \
  --data "algorithm=RS256"
```

### 4. Update Token Issuing Service

Immediately update the authentication service to use the new private key for signing tokens.

### 5. Force Re-authentication

Implement a mechanism to force all users to re-authenticate, such as:

- Clear all active sessions in Redis
- Update the frontend to detect invalid tokens and redirect to login
- Send notifications to users if appropriate

## Verification Steps

After completing the key rotation, verify that the system is working correctly:

### 1. Verify Kong Configuration

```bash
# List all JWT keys to confirm the new key is present
curl -X GET http://kong-admin:8001/jwt-keys

# Verify the JWT plugin configuration
curl -X GET http://kong-admin:8001/plugins/{jwt-plugin-id}
```

### 2. Test Token Validation

- Generate a test token with the new private key
- Verify that the token is accepted by Kong
- If in transition period, verify that tokens signed with the old key are still valid
- After transition period, verify that tokens signed with the old key are rejected

### 3. Monitor Authentication Metrics

Monitor the following metrics for at least 24 hours after rotation:

- Authentication success/failure rates
- API response times
- Error rates in authentication-related services
- User session creation rates

## Best Practices

1. **Regular Rotation**: Rotate keys every 90 days even without suspected compromise
2. **Key Length**: Use 2048-bit RSA keys at minimum (4096-bit recommended for higher security)
3. **Secure Storage**: Store private keys in a secure key management system
4. **Automation**: Automate the rotation process where possible to reduce human error
5. **Audit Logging**: Maintain detailed logs of all key rotation activities
6. **Testing**: Test the rotation procedure in a staging environment before production
7. **Documentation**: Keep this document updated with any changes to the rotation process

## Troubleshooting

### Common Issues

1. **Increased Authentication Failures**
   - Check that the new public key was properly added to Kong
   - Verify the JWT plugin configuration
   - Ensure the token issuing service is using the correct private key

2. **Token Validation Errors**
   - Verify the 'kid' claim in the JWT header matches the key ID in Kong
   - Check that the token hasn't expired
   - Ensure the token contains all required claims (exp, iat, iss, aud)

3. **API Gateway Performance Issues**
   - Monitor Kong performance metrics
   - Check for increased latency in token validation
   - Consider scaling Kong if necessary during high-traffic periods

## References

- [Kong JWT Plugin Documentation](https://docs.konghq.com/hub/kong-inc/jwt/)
- [JWT.io](https://jwt.io/) - For debugging JWT tokens
- [OpenSSL Documentation](https://www.openssl.org/docs/)
- [NIST Guidelines for Key Management](https://csrc.nist.gov/publications/detail/sp/800-57-part-1/rev-5/final)

## Revision History

| Date | Version | Author | Changes |
|------|---------|--------|--------|
| 2023-06-15 | 1.0 | Security Team | Initial document |