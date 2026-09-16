-- =============================================================================
-- Migration 010: Activity Events (Audit Log)
-- =============================================================================
-- Activity events are stored in PostgreSQL using JSONB for metadata.
--
-- Design choice: JSONB in PostgreSQL (not MongoDB) for activity events
-- because:
--   1. Events need to be correlated with relational data (student_id, course_id)
--      for admin reporting — JOINs are simpler in PostgreSQL
--   2. The metadata shape is flexible but we still need to query by actor_id,
--      event_type, and entity_id — PostgreSQL JSONB handles this well
--   3. Avoids cross-database transactions for events generated mid-transaction
--
-- MongoDB activity_events is used for application-level event streaming where
-- the notification service picks up events and fans them out.
-- =============================================================================

CREATE TABLE activity_events (
    event_id        UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    actor_id        UUID REFERENCES users(user_id) ON DELETE SET NULL,  -- Who did it
    event_type      VARCHAR(60) NOT NULL,       -- LOGIN, ENROLLMENT_CREATED, etc.
    entity_type     VARCHAR(60),                -- users, courses, assignments, etc.
    entity_id       UUID,                       -- The affected entity's primary key
    ip_address      INET,                       -- Client IP (nullable, from X-Forwarded-For)
    request_id      VARCHAR(36),                -- Trace ID from the API Gateway
    -- Flexible metadata: course_name, assignment_title, etc.
    -- Passwords, tokens, and secrets must NEVER appear here.
    metadata        JSONB DEFAULT '{}',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- =============================================================================
-- Indexes for activity_events
-- =============================================================================

-- Find all events by a specific user (admin audit view)
CREATE INDEX idx_activity_events_actor_id ON activity_events(actor_id);

-- Filter by event type (e.g., show all LOGIN events)
CREATE INDEX idx_activity_events_event_type ON activity_events(event_type);

-- Find events for a specific entity (e.g., all events for course X)
CREATE INDEX idx_activity_events_entity ON activity_events(entity_type, entity_id);

-- Time-range filtering (recent activity, daily/weekly reports)
CREATE INDEX idx_activity_events_created_at ON activity_events(created_at DESC);

-- GIN index for querying inside metadata JSONB
-- Useful for: metadata @> '{"course_id": "..."}'
CREATE INDEX idx_activity_events_metadata ON activity_events USING GIN (metadata);

-- =============================================================================
-- Search history: tracks what queries students have made
-- (separate from search_cache which is about result caching)
-- =============================================================================
CREATE TABLE search_history (
    history_id      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    query_text      TEXT NOT NULL,
    course_ids      UUID[],                     -- Courses the search was scoped to
    results_count   INTEGER NOT NULL DEFAULT 0,
    search_type     VARCHAR(20) NOT NULL DEFAULT 'HYBRID',  -- VECTOR, KEYWORD, HYBRID
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_search_history_user_id ON search_history(user_id);
CREATE INDEX idx_search_history_created_at ON search_history(created_at DESC);
