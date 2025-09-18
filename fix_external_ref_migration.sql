-- Migration script to add missing columns to pipeline_runs table
-- This fixes the schema mismatch between the orchestrator code and database

-- Add the missing external_ref column
ALTER TABLE pipeline_runs 
ADD COLUMN external_ref VARCHAR(256);

-- Add the missing failure_reason column
ALTER TABLE pipeline_runs 
ADD COLUMN failure_reason TEXT;

-- Add the missing triggered_by column
ALTER TABLE pipeline_runs 
ADD COLUMN triggered_by VARCHAR(128);

-- Add the missing retry_count column
ALTER TABLE pipeline_runs 
ADD COLUMN retry_count INTEGER DEFAULT 0 NOT NULL;

-- Add indexes for better query performance (optional but recommended)
CREATE INDEX idx_pipeline_runs_external_ref ON pipeline_runs(external_ref);

-- Verify the columns were added
\d pipeline_runs;
