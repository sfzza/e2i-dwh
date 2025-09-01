-- Re-create the table with the correct schema
DROP TABLE IF EXISTS applicants;

CREATE TABLE applicants (
    `applicant_id` UInt64,
    `name` String,
    `dob` Nullable(String)
) ENGINE = MergeTree()
ORDER BY applicant_id;
