-- =============================================================================
-- Migration 011: Refresh Tokens
-- =============================================================================
-- Stores refresh token metadata for token rotation and revocation.
-- The actual token string is stored hashed (SHA-256) to prevent theft
-- from database access — similar to how we hash passwords.
--
-- When a user logs out or a token is refreshed, the old token is revoked.
-- This enables a secure token rotation pattern.
-- =============================================================================

CREATE TABLE refresh_tokens (
    token_id        UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    token_hash      VARCHAR(64) NOT NULL,       -- SHA-256 of the actual token
    issued_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at      TIMESTAMPTZ NOT NULL,
    revoked         BOOLEAN NOT NULL DEFAULT FALSE,
    revoked_at      TIMESTAMPTZ,
    device_info     VARCHAR(255),               -- User-Agent or device hint

    CONSTRAINT refresh_tokens_hash_unique UNIQUE (token_hash)
);

-- Token lookup during refresh — must be fast
CREATE INDEX idx_refresh_tokens_token_hash ON refresh_tokens(token_hash);

-- Find all active tokens for a user (for logout-all-devices feature)
CREATE INDEX idx_refresh_tokens_user_id ON refresh_tokens(user_id);

-- Clean up expired tokens periodically
CREATE INDEX idx_refresh_tokens_expires_at ON refresh_tokens(expires_at);
