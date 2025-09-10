# e2i/orchestrator/dags/etl_pipeline.py

from __future__ import annotations

import logging
import os
from datetime import timedelta

import boto3
import pandas as pd
import requests
import hashlib
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
EXPECTED_COLUMNS = [h.strip() for h in os.getenv("EXPECTED_COLUMNS", "name,dob").split(",")]

# Columns to be tokenized
TOKENIZED_COLUMNS = ["name"]

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

    try:
        with open(staging_path, "r", encoding="utf-8") as f:
            header_line = f.readline()
            header = [h.strip().lower() for h in header_line.strip().split(",") if h.strip()]
            missing = [c for c in EXPECTED_COLUMNS if c not in header]
            if missing:
                raise RuntimeError(f"Missing expected columns: {missing}")
    except Exception:
        logger.exception("Header validation failed for %s", staging_path)
        try:
            os.remove(staging_path)
        except Exception:
            pass
        raise
    
    logger.info("Extract completed: %s", staging_path)
    return staging_path

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

def tokenize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    Replaces specified columns with tokens using the tokenization service.
    Falls back to local hashing if service is unavailable.
    """
    for col in TOKENIZED_COLUMNS:
        if col in df.columns:
            # Get unique values to minimize API calls
            unique_values = df[col].dropna().unique().tolist()
            
            if unique_values:
                # Call tokenization service
                token_mapping = tokenize_with_service(unique_values, col)
                
                # Apply tokenization
                df[col] = df[col].map(lambda x: token_mapping.get(x, x) if pd.notna(x) else x)
                
                logger.info(f"Tokenized column '{col}' with {len(unique_values)} unique values")
            
    return df

def perform_transform(staging_path: str) -> str:
    """
    Cleans the staged CSV, tokenizes it, and produces a processed file.
    """
    os.makedirs(LOCAL_PROCESSED_DIR, exist_ok=True)
    try:
        logger.info("Reading staging file %s", staging_path)
        df = pd.read_csv(staging_path)

        # --- Data Cleaning ---
        df.columns = [c.strip().lower() for c in df.columns]
        df = df.dropna(how="all")
        for c in df.select_dtypes(include="object").columns:
            df[c] = df[c].astype(str).str.strip()
        
        # Name standardization before tokenization
        if "name" in df.columns:
            df["name"] = df["name"].apply(lambda v: v.title() if isinstance(v, str) else v)
        
        # --- Tokenization with Service ---
        df = tokenize_columns(df)
        
        processed_filename = f"processed_{os.path.basename(staging_path)}"
        processed_path = os.path.join(LOCAL_PROCESSED_DIR, processed_filename)
        
        logger.info("Writing processed file to %s", processed_path)
        df.to_csv(processed_path, index=False)
        
    except Exception as e:
        logger.exception("Transformation failed for %s", staging_path)
        raise RuntimeError(f"Transform failed for {staging_path}") from e

    logger.info("Transform completed: %s", processed_path)
    return processed_path

def perform_load(processed_path: str):
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
        insert_sql = f"INSERT INTO {CLICKHOUSE_TABLE} ({cols_sql}) VALUES"

        logger.info("Inserting %d rows into ClickHouse table %s", len(records), CLICKHOUSE_TABLE)
        client.execute(insert_sql, records)
        
    except Exception as e:
        logger.exception("Failed to insert into ClickHouse: %s", e)
        raise RuntimeError(f"Load failed for {processed_path} into {CLICKHOUSE_TABLE}") from e

    logger.info("Load completed: %d rows into %s", len(records), CLICKHOUSE_TABLE)

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

# -------------------------------------------------------------------
# Airflow Task Wrapper Functions
# -------------------------------------------------------------------

def run_extract(**kwargs):
    conf = kwargs["dag_run"].conf or {}
    minio_key = conf.get("minioKey")
    if not minio_key:
        raise ValueError("Missing 'minioKey' in DAG run configuration.")
    return perform_extract(file_path=minio_key)

def run_transform(**kwargs):
    ti = kwargs["ti"]
    staging_path = ti.xcom_pull(task_ids="extract")
    if not staging_path:
        raise ValueError("Could not find staged file path from extract task.")
    return perform_transform(staging_path=staging_path)

def run_load(**kwargs):
    ti = kwargs["ti"]
    processed_path = ti.xcom_pull(task_ids="transform")
    if not processed_path:
        raise ValueError("Could not find processed file path from transform task.")
    perform_load(processed_path=processed_path)

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
    ## ETL Pipeline with Production Tokenization Service
    This DAG processes CSV files and tokenizes sensitive data using a secure tokenization service.
    **Trigger with configuration:** `{"minioKey": "your-file-name.csv"}`
    
    **Process:**
    1. Extract: Download CSV from MinIO
    2. Transform: Clean data and tokenize PII using tokenization service
    3. Load: Insert tokenized data into ClickHouse
    4. Archive: Move original file to archive bucket
    
    **Features:**
    - Production tokenization service with secure token storage
    - Fallback to local hashing if service unavailable
    - Audit trail for all tokenization operations
    - Efficient batching of tokenization API calls
    """,
    tags=["etl", "minio", "clickhouse", "tokenization", "production"],
) as dag:
    extract_task = PythonOperator(
        task_id="extract",
        python_callable=run_extract,
    )

    transform_task = PythonOperator(
        task_id="transform",
        python_callable=run_transform,
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