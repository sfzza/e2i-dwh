-- This script is run by the PostgreSQL container's entrypoint.
-- The user and database (tokenization_user and tokenization_db)
-- are automatically created based on environment variables in docker-compose.yml.
-- Therefore, we only need to define the table schemas here.

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