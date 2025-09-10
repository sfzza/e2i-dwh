-- Create database if not exists
CREATE DATABASE IF NOT EXISTS e2i_warehouse;
USE e2i_warehouse;

-- Re-create the table with the correct schema
CREATE TABLE IF NOT EXISTS applicants (
    `applicant_id` UInt64,
    `name` String,
    `dob` Nullable(String)
) ENGINE = MergeTree()
ORDER BY applicant_id;