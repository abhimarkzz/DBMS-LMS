-- =============================================================================
-- Migration 002: Users and Role System
-- =============================================================================
-- Design decision: We use a hybrid role model.
--   - users.role column (ENUM) for fast, simple auth checks in most queries
--   - user_roles junction table for future expansion (multi-role, permissions)
--
-- This avoids expensive joins on every JWT validation while keeping the
-- schema extensible. The ENUM approach is appropriate because LMS roles
-- are well-defined and unlikely to grow beyond 3-5 types.
-- =============================================================================

-- Role ENUM — controls all valid roles in the system
CREATE TYPE user_role AS ENUM ('STUDENT', 'TEACHER', 'ADMIN');

-- Role definitions table — allows adding metadata to roles
CREATE TABLE roles (
    role_id     UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    role_name   user_role NOT NULL UNIQUE,
    description TEXT,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Core user accounts table
-- Holds authentication credentials and basic profile info.
-- Role-specific details (semester, department, employee_id) live in
-- separate tables to avoid nulls for inapplicable columns.
CREATE TABLE users (
    user_id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email           VARCHAR(255) NOT NULL,
    password_hash   VARCHAR(255) NOT NULL,   -- bcrypt hash, never plain text
    first_name      VARCHAR(100) NOT NULL,
    last_name       VARCHAR(100) NOT NULL,
    phone           VARCHAR(20),
    role            user_role NOT NULL,
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_login_at   TIMESTAMPTZ,

    -- Email must be unique across the entire system
    CONSTRAINT users_email_unique UNIQUE (email),

    -- Basic format validation — deeper validation belongs in the application
    CONSTRAINT users_email_format CHECK (email ~* '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$'),

    -- Passwords shorter than 60 chars cannot be a valid bcrypt hash
    CONSTRAINT users_password_hash_length CHECK (LENGTH(password_hash) >= 60)
);

-- Junction table for future multi-role or fine-grained permission support.
-- Currently each user has exactly one role via users.role, but this table
-- allows assigning multiple roles without breaking the existing model.
CREATE TABLE user_roles (
    user_role_id    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    role_id         UUID NOT NULL REFERENCES roles(role_id) ON DELETE RESTRICT,
    assigned_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    assigned_by     UUID REFERENCES users(user_id) ON DELETE SET NULL,

    -- A user cannot have the same role assigned twice
    CONSTRAINT user_roles_unique UNIQUE (user_id, role_id)
);

-- =============================================================================
-- Indexes for users and roles
-- =============================================================================

-- The most common user lookup: find by email during login
-- Without this index, login queries scan the full users table.
CREATE INDEX idx_users_email ON users(email);

-- Filter active users in admin queries
CREATE INDEX idx_users_is_active ON users(is_active);

-- Filter by role for admin dashboards (count students, teachers, etc.)
CREATE INDEX idx_users_role ON users(role);

-- user_roles: look up all roles for a given user
CREATE INDEX idx_user_roles_user_id ON user_roles(user_id);

-- =============================================================================
-- Trigger: auto-update users.updated_at on every row modification
-- =============================================================================

CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_users_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW
    EXECUTE FUNCTION set_updated_at();

-- Seed the three base roles so they exist before any user is created
INSERT INTO roles (role_name, description) VALUES
    ('STUDENT', 'Enrolled student with access to courses and assignments'),
    ('TEACHER', 'Course instructor with ability to create and manage courses'),
    ('ADMIN',   'System administrator with full management access');
