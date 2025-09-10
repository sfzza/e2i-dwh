-- tokenization-service/init-tokenization-db.sql

-- Create tokenization database
CREATE DATABASE IF NOT EXISTS tokenization_db;

-- Connect to the tokenization database
\c tokenization_db;

-- Create user if not exists
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'tokenization_user') THEN
        CREATE USER tokenization_user WITH PASSWORD 'tokenization_pass';
    END IF;
END
$$;

-- Grant privileges
GRANT ALL PRIVILEGES ON DATABASE tokenization_db TO tokenization_user;

-- Create token mappings table
CREATE TABLE IF NOT EXISTS token_mappings (
    id SERIAL PRIMARY KEY,
    token VARCHAR(64) UNIQUE NOT NULL,
    original_value TEXT NOT NULL,
    data_type VARCHAR(50) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_token_mappings_token ON token_mappings(token);
CREATE INDEX IF NOT EXISTS idx_token_mappings_data_type ON token_mappings(data_type);
CREATE INDEX IF NOT EXISTS idx_token_mappings_created_at ON token_mappings(created_at);

-- Create audit table for detokenization access
CREATE TABLE IF NOT EXISTS detokenization_audit (
    id SERIAL PRIMARY KEY,
    token VARCHAR(64) NOT NULL,
    data_type VARCHAR(50),
    accessed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for audit queries
CREATE INDEX IF NOT EXISTS idx_detokenization_audit_token ON detokenization_audit(token);
CREATE INDEX IF NOT EXISTS idx_detokenization_audit_accessed_at ON detokenization_audit(accessed_at);

-- Grant table permissions
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO tokenization_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO tokenization_user;