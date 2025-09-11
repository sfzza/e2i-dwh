# e2i/orchestrator/dags/etl_pipeline_updated.py

from __future__ import annotations

import logging
import os
import pandas as pd
import requests
import hashlib
import psycopg2
import json
from datetime import timedelta
from typing import Dict, List, Tuple, Any

from airflow.models.dag import DAG
from airflow.operators.python import PythonOperator
from botocore.client import Config
from botocore.exceptions import BotoCoreError, ClientError
from clickhouse_driver import Client
from airflow.utils.dates import days_ago

# -------------------------------------------------------------------
# Configuration
# -------------------------------------------------------------------

# Set up a single logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("etl_pipeline")

# MinIO/S3 Configuration
MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "http://minio:9000")
MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY", "minioadmin")
MINIO_REGION = os.getenv("MINIO_REGION", "us-east-1")
MINIO_LANDING_BUCKET = os.getenv("MINIO_LANDING_BUCKET", "uploads")
MINIO_ARCHIVE_BUCKET = os.getenv("MINIO_ARCHIVE_BUCKET", "archive")

# ClickHouse Configuration
CLICKHOUSE_HOST = os.getenv("CLICKHOUSE_HOST", "clickhouse")
CLICKHOUSE_PORT = os.getenv("CLICKHOUSE_PORT", 9000)
CLICKHOUSE_USER = os.getenv("CLICKHOUSE_USER", "user")
CLICKHOUSE_PASSWORD = os.getenv("CLICKHOUSE_PASSWORD", "password")
CLICKHOUSE_DB = os.getenv("CLICKHOUSE_DB", "default")
CLICKHOUSE_TABLE = os.getenv("CLICKHOUSE_TABLE", "applicants")

# Tokenization Service Configuration
TOKENIZATION_ENDPOINT = os.getenv("TOKENIZATION_ENDPOINT", "http://tokenization_service:8004")
TOKENIZATION_API_KEY = os.getenv("TOKENIZATION_API_KEY", "your-secure-api-key-change-in-production")

# Local File Paths within the Airflow Worker
LOCAL_STAGING_DIR = os.getenv("LOCAL_STAGING_DIR", "/tmp/etl_staging")
LOCAL_PROCESSED_DIR = os.getenv("LOCAL_PROCESSED_DIR", "/tmp/etl_processed")

# Add database connection for reading mappings
DB_CONFIG = {
    'host': os.getenv('DJANGO_DB_HOST', 'orchestrator_postgres'),
    'port': os.getenv('DJANGO_DB_PORT', '5432'),
    'database': os.getenv('DJANGO_DB_NAME', 'e2i_db'),
    'user': os.getenv('DJANGO_DB_USER', 'e2i_user'),
    'password': os.getenv('DJANGO_DB_PASSWORD', 'e2i_pass'),
}

# -------------------------------------------------------------------
# ETL Core Logic
# -------------------------------------------------------------------

def _get_s3_client():
    """Create a boto3 S3 client configured for MinIO."""
    return boto3.client(
        "s3",
        endpoint_url=MINIO_ENDPOINT,
        aws_access_key_id=MINIO_ACCESS_KEY,
        aws_secret_access_key=MINIO_SECRET_KEY,
        config=Config(signature_version="s3v4"),
        region_name=MINIO_REGION,
    )

def perform_extract(file_path: str) -> str:
    """
    Downloads raw CSV from MinIO, validates headers, and stores it in a local staging location.
    The header validation is now done by the transform step using template mappings.
    """
    os.makedirs(LOCAL_STAGING_DIR, exist_ok=True)
    client = _get_s3_client()
    filename = os.path.basename(file_path)
    staging_path = os.path.join(LOCAL_STAGING_DIR, filename)

    try:
        logger.info("Downloading s3://%s/%s -> %s", MINIO_LANDING_BUCKET, file_path, staging_path)
        client.download_file(MINIO_LANDING_BUCKET, file_path, staging_path)
    except (BotoCoreError, ClientError) as e:
        logger.exception("Failed to download file from MinIO: %s", e)
        raise RuntimeError(f"Failed to download {MINIO_LANDING_BUCKET}/{file_path}") from e

    logger.info("Extract completed: %s", staging_path)
    return staging_path


def get_upload_mappings(upload_id: str) -> Dict[str, Any]:
    """
    Fetch column mappings and template info for an upload from the database.
    Returns the template and column mapping configuration.
    """
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()

        # Get upload template info
        cursor.execute("""
            SELECT ut.selected_template_id, dt.name as template_name, dt.target_table
            FROM upload_template_info ut
            JOIN data_templates dt ON ut.selected_template_id = dt.id
            WHERE ut.upload_id = %s
        """, (upload_id,))

        template_row = cursor.fetchone()
        if not template_row:
            raise ValueError(f"No template mapping found for upload {upload_id}")

        template_id, template_name, target_table = template_row

        # Get column mappings with template column info
        cursor.execute("""
            SELECT
                cm.source_column,
                tc.name as target_column,
                tc.data_type,
                tc.processing_type,
                tc.processing_config,
                tc.is_required,
                tc.max_length,
                tc.regex_pattern,
                cm.transform_function,
                cm.transform_params
            FROM column_mappings cm
            JOIN template_columns tc ON cm.target_column_id = tc.id
            WHERE cm.upload_id = %s
            ORDER BY tc.order
        """, (upload_id,))

        mappings = []
        for row in cursor.fetchall():
            mappings.append({
                'source_column': row[0],
                'target_column': row[1],
                'data_type': row[2],
                'processing_type': row[3],
                'processing_config': row[4] or {},
                'is_required': row[5],
                'max_length': row[6],
                'regex_pattern': row[7],
                'transform_function': row[8],
                'transform_params': row[9] or {},
            })

        cursor.close()
        conn.close()

        return {
            'template_id': template_id,
            'template_name': template_name,
            'target_table': target_table,
            'mappings': mappings
        }

    except Exception as e:
        logger.error(f"Failed to get upload mappings: {e}")
        raise

def tokenize_with_service(values: list, data_type: str = "name") -> dict:
    """
    Call the tokenization service to tokenize values and store mappings.
    Returns a mapping of original_value -> token.
    """
    if not values:
        return {}

    try:
        response = requests.post(
            f"{TOKENIZATION_ENDPOINT}/api/v1/tokenize",
            json={
                "values": values,
                "data_type": data_type
            },
            headers={
                "Authorization": f"Bearer {TOKENIZATION_API_KEY}",
                "Content-Type": "application/json"
            },
            timeout=30
        )
        response.raise_for_status()

        result = response.json()
        mappings = result.get("mappings", {})

        logger.info(f"Successfully tokenized {len(mappings)} {data_type} values via service")
        return mappings

    except requests.exceptions.RequestException as e:
        logger.error(f"Tokenization service call failed: {e}")
        # Fallback to local hashing (backward compatibility)
        logger.info("Falling back to local SHA-256 tokenization")
        return {
            value: hashlib.sha256(str(value).encode()).hexdigest()
            for value in values
        }


def apply_transform_function(series: pd.Series, func_name: str, params: Dict) -> pd.Series:
    """Apply specified transformation function to a pandas Series."""

    if func_name == 'upper':
        return series.astype(str).str.upper()
    elif func_name == 'lower':
        return series.astype(str).str.lower()
    elif func_name == 'trim':
        return series.astype(str).str.strip()
    elif func_name == 'title':
        return series.astype(str).str.title()
    elif func_name == 'format_date':
        date_format = params.get('format', '%Y-%m-%d')
        return pd.to_datetime(series, errors='coerce').dt.strftime(date_format)
    elif func_name == 'extract_numbers':
        return series.astype(str).str.extract(r'(\d+)', expand=False)
    elif func_name == 'prefix':
        prefix = params.get('prefix', '')
        return prefix + series.astype(str)
    elif func_name == 'suffix':
        suffix = params.get('suffix', '')
        return series.astype(str) + suffix
    elif func_name == 'replace':
        old_val = params.get('old', '')
        new_val = params.get('new', '')
        return series.astype(str).str.replace(old_val, new_val)
    else:
        logger.warning(f"Unknown transform function: {func_name}")
        return series


def convert_data_type(series: pd.Series, data_type: str, mapping: Dict) -> pd.Series:
    """Convert series to specified data type with validation."""

    try:
        if data_type == 'string':
            result = series.astype(str)
            max_length = mapping.get('max_length')
            if max_length:
                result = result.str[:max_length]
            return result

        elif data_type == 'integer':
            return pd.to_numeric(series, errors='coerce').astype('Int64')

        elif data_type == 'float':
            return pd.to_numeric(series, errors='coerce')

        elif data_type == 'datetime':
            return pd.to_datetime(series, errors='coerce')

        elif data_type == 'date':
            return pd.to_datetime(series, errors='coerce').dt.date

        elif data_type == 'boolean':
            return series.astype(str).str.lower().isin(['true', '1', 'yes', 'y'])

        else:
            logger.warning(f"Unknown data type: {data_type}, keeping as string")
            return series.astype(str)

    except Exception as e:
        logger.error(f"Data type conversion failed for {data_type}: {e}")
        return series


def apply_tokenization(series: pd.Series, mapping: Dict) -> pd.Series:
    """Apply tokenization to sensitive data using the tokenization service."""

    # Get unique non-null values to minimize API calls
    unique_values = series.dropna().unique().tolist()
    if not unique_values:
        return series

    # Determine data type for tokenization service
    processing_config = mapping.get('processing_config', {})
    data_type = processing_config.get('token_type', 'general')

    try:
        # Use existing tokenization service function
        token_mapping = tokenize_with_service(unique_values, data_type)

        # Apply tokenization mapping
        return series.map(lambda x: token_mapping.get(x, x) if pd.notna(x) else x)

    except Exception as e:
        logger.error(f"Tokenization failed: {e}")
        # Fallback to hashing
        return apply_hashing(series, mapping)


def apply_hashing(series: pd.Series, mapping: Dict) -> pd.Series:
    """Apply hashing transformation."""
    import hashlib

    def hash_value(val):
        if pd.isna(val):
            return val
        return hashlib.sha256(str(val).encode()).hexdigest()

    return series.apply(hash_value)


def apply_normalization(series: pd.Series, mapping: Dict) -> pd.Series:
    """Apply normalization rules."""
    processing_config = mapping.get('processing_config', {})

    result = series.astype(str).str.strip()

    if processing_config.get('lowercase', False):
        result = result.str.lower()

    if processing_config.get('remove_spaces', False):
        result = result.str.replace(' ', '')

    if processing_config.get('remove_special_chars', False):
        result = result.str.replace(r'[^a-zA-Z0-9]', '', regex=True)

    return result


def apply_column_transformations(df: pd.DataFrame, mappings: List[Dict]) -> pd.DataFrame:
    """
    Apply transformations based on column mappings configuration.
    """
    result_df = pd.DataFrame()

    for mapping in mappings:
        source_col = mapping['source_column']
        target_col = mapping['target_column']
        data_type = mapping['data_type']
        processing_type = mapping['processing_type']
        transform_function = mapping.get('transform_function')

        if source_col not in df.columns:
            if mapping['is_required']:
                raise ValueError(f"Required source column '{source_col}' not found in file")
            else:
                # Create empty column for optional fields
                result_df[target_col] = None
                continue

        # Get source data
        source_data = df[source_col].copy()

        # Apply custom transform function if specified
        if transform_function:
            source_data = apply_transform_function(source_data, transform_function, mapping.get('transform_params', {}))

        # Apply data type conversion
        source_data = convert_data_type(source_data, data_type, mapping)

        # Apply processing (tokenization, hashing, etc.)
        if processing_type == 'tokenize':
            source_data = apply_tokenization(source_data, mapping)
        elif processing_type == 'hash':
            source_data = apply_hashing(source_data, mapping)
        elif processing_type == 'normalize':
            source_data = apply_normalization(source_data, mapping)

        result_df[target_col] = source_data

    return result_df


def perform_transform_with_mappings(staging_path: str, upload_id: str) -> str:
    """
    Enhanced transform function that uses database-driven column mappings.
    """
    os.makedirs(LOCAL_PROCESSED_DIR, exist_ok=True)

    try:
        logger.info("Reading staging file %s", staging_path)
        df = pd.read_csv(staging_path)

        # Get mapping configuration from database
        mapping_config = get_upload_mappings(upload_id)
        logger.info(f"Using template: {mapping_config['template_name']}")

        # Apply column mappings and transformations
        processed_df = apply_column_transformations(df, mapping_config['mappings'])

        # Validate required columns
        required_cols = [m['target_column'] for m in mapping_config['mappings'] if m['is_required']]
        missing_data = []
        for col in required_cols:
            if col in processed_df.columns:
                null_count = processed_df[col].isnull().sum()
                if null_count > 0:
                    missing_data.append(f"{col}: {null_count} null values")

        if missing_data:
            logger.warning(f"Data quality issues: {missing_data}")

        # Save processed file
        processed_filename = f"processed_{os.path.basename(staging_path)}"
        processed_path = os.path.join(LOCAL_PROCESSED_DIR, processed_filename)

        logger.info("Writing processed file to %s", processed_path)
        processed_df.to_csv(processed_path, index=False)

        # Update database with processing status
        update_upload_processing_status(upload_id, 'transformed', {
            'target_table': mapping_config['target_table'],
            'processed_columns': list(processed_df.columns),
            'row_count': len(processed_df),
            'data_quality_issues': missing_data,
        })

    except Exception as e:
        logger.exception("Transformation failed for %s", staging_path)
        update_upload_processing_status(upload_id, 'failed', {'error': str(e)})
        raise RuntimeError(f"Transform failed for {staging_path}") from e

    logger.info("Transform completed: %s", processed_path)
    return processed_path


def perform_load(processed_path: str, upload_id: str):
    """
    Loads the processed dataset into the ClickHouse data warehouse.
    """
    try:
        logger.info("Reading processed file %s", processed_path)
        df = pd.read_csv(processed_path)
    except Exception as e:
        logger.exception("Failed to read processed file %s", processed_path)
        raise RuntimeError(f"Failed to read {processed_path}") from e

    if df.empty:
        logger.warning("Processed file %s is empty; nothing to load", processed_path)
        return

    try:
        # Get target table from database
        mapping_config = get_upload_mappings(upload_id)
        target_table = mapping_config['target_table']
        
        client = Client(
            host=CLICKHOUSE_HOST,
            port=CLICKHOUSE_PORT,
            user=CLICKHOUSE_USER,
            password=CLICKHOUSE_PASSWORD,
            database=CLICKHOUSE_DB,
        )
        cols = list(df.columns)
        records = df.where(pd.notnull(df), None).to_records(index=False).tolist()

        cols_sql = ", ".join(f"`{c}`" for c in cols)
        insert_sql = f"INSERT INTO {target_table} ({cols_sql}) VALUES"

        logger.info("Inserting %d rows into ClickHouse table %s", len(records), target_table)
        client.execute(insert_sql, records)

    except Exception as e:
        logger.exception("Failed to insert into ClickHouse: %s", e)
        raise RuntimeError(f"Load failed for {processed_path} into {CLICKHOUSE_TABLE}") from e

    logger.info("Load completed: %d rows into %s", len(records), target_table)

def perform_archive(file_path: str):
    """
    Moves the original file from landing zone to archive zone in MinIO.
    """
    try:
        s3 = _get_s3_client()
        # Ensure the archive bucket exists
        try:
            s3.head_bucket(Bucket=MINIO_ARCHIVE_BUCKET)
        except ClientError:
            logger.info("Archive bucket '%s' not found. Creating it.", MINIO_ARCHIVE_BUCKET)
            s3.create_bucket(Bucket=MINIO_ARCHIVE_BUCKET)

        copy_source = {"Bucket": MINIO_LANDING_BUCKET, "Key": file_path}
        s3.copy(copy_source, MINIO_ARCHIVE_BUCKET, file_path)
        s3.delete_object(Bucket=MINIO_LANDING_BUCKET, Key=file_path)

        logger.info(f"Archived {file_path} from {MINIO_LANDING_BUCKET} -> {MINIO_ARCHIVE_BUCKET}")

    except (BotoCoreError, ClientError) as e:
        raise RuntimeError(f"Archive failed for {file_path}: {e}")

def update_upload_processing_status(upload_id: str, status: str, details: Dict):
    """Update upload status in database with processing details."""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()

        cursor.execute("""
            UPDATE uploads
            SET status = %s, updated_at = NOW()
            WHERE id = %s
        """, (status, upload_id))

        # Also update validation report with processing details if needed
        cursor.execute("""
            UPDATE validation_reports
            SET stats = %s
            WHERE upload_id = %s
        """, (json.dumps(details), upload_id))

        conn.commit()
        cursor.close()
        conn.close()

    except Exception as e:
        logger.error(f"Failed to update upload status: {e}")


# -------------------------------------------------------------------
# Airflow Task Wrapper Functions
# -------------------------------------------------------------------

def run_extract(**kwargs):
    conf = kwargs["dag_run"].conf or {}
    minio_key = conf.get("minioKey")
    if not minio_key:
        raise ValueError("Missing 'minioKey' in DAG run configuration.")
    return perform_extract(file_path=minio_key)


def run_transform_with_mappings(**kwargs):
    """Updated transform task that uses column mappings."""
    ti = kwargs["ti"]
    staging_path = ti.xcom_pull(task_ids="extract")
    if not staging_path:
        raise ValueError("Could not find staged file path from extract task.")

    # Get upload_id from DAG run configuration
    conf = kwargs["dag_run"].conf or {}
    upload_id = conf.get("uploadId")
    if not upload_id:
        raise ValueError("Missing 'uploadId' in DAG run configuration.")

    return perform_transform_with_mappings(staging_path=staging_path, upload_id=upload_id)

def run_load(**kwargs):
    ti = kwargs["ti"]
    processed_path = ti.xcom_pull(task_ids="transform")
    if not processed_path:
        raise ValueError("Could not find processed file path from transform task.")
    
    # Get upload_id from DAG run configuration
    conf = kwargs["dag_run"].conf or {}
    upload_id = conf.get("uploadId")
    if not upload_id:
        raise ValueError("Missing 'uploadId' in DAG run configuration.")

    perform_load(processed_path=processed_path, upload_id=upload_id)


def run_archive(**kwargs):
    conf = kwargs["dag_run"].conf or {}
    minio_key = conf.get("minioKey")
    if not minio_key:
        raise ValueError("Missing 'minioKey' in DAG run configuration.")
    perform_archive(file_path=minio_key)

# -------------------------------------------------------------------
# DAG Definition
# -------------------------------------------------------------------

with DAG(
    dag_id="etl_pipeline",
    start_date=days_ago(1),
    schedule=None,
    catchup=False,
    doc_md="""
    ## ETL Pipeline with Production Tokenization Service and Dynamic Mappings
    This DAG processes CSV files and tokenizes sensitive data using a secure tokenization service and database-driven column mappings.
    **Trigger with configuration:** `{"minioKey": "your-file-name.csv", "uploadId": "your-upload-uuid"}`

    **Process:**
    1. Extract: Download CSV from MinIO.
    2. Transform: Fetches column mappings from the database, cleans and processes data based on the defined rules, and tokenizes PII.
    3. Load: Inserts the processed data into the appropriate ClickHouse table, which is also determined by the template.
    4. Archive: Moves the original file to the archive bucket.

    **Features:**
    - Dynamic column mapping and transformation
    - Database-driven data types and processing rules
    - Secure tokenization service integration
    - Handles data quality issues like missing required columns
    """,
    tags=["etl", "minio", "clickhouse", "tokenization", "dynamic", "production"],
) as dag:
    extract_task = PythonOperator(
        task_id="extract",
        python_callable=run_extract,
    )

    transform_task = PythonOperator(
        task_id="transform",
        python_callable=run_transform_with_mappings,
    )

    load_task = PythonOperator(
        task_id="load",
        python_callable=run_load,
    )

    archive_task = PythonOperator(
        task_id="archive",
        python_callable=run_archive,
    )

    extract_task >> transform_task >> load_task >> archive_task
