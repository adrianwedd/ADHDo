-- PostgreSQL initialization script for MCP ADHD Server
-- This script sets up the database for first-time deployment

-- Create database if it doesn't exist (handled by POSTGRES_DB env var)
-- Extensions that might be useful for ADHD functionality
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";  -- For fuzzy text matching
CREATE EXTENSION IF NOT EXISTS "btree_gin"; -- For better indexing

-- Create indexes for performance optimization
-- These will be created after Alembic migrations run, but we prepare for them

-- Log initial setup
DO $$
BEGIN
  RAISE NOTICE 'MCP ADHD Server database initialized successfully';
  RAISE NOTICE 'Database: %', current_database();
  RAISE NOTICE 'User: %', current_user;
  RAISE NOTICE 'Extensions installed: uuid-ossp, pg_trgm, btree_gin';
END $$;