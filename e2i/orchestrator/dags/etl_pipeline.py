from __future__ import annotations

import logging
import os
from datetime import timedelta

import boto3
import pandas as pd
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
MINIO_LANDING_BUCKET = os.getenv("MINIO_LANDING_BUCKET", "landing")
MINIO_ARCHIVE_BUCKET = os.getenv("MINIO_ARCHIVE_BUCKET", "archive")

# ClickHouse Configuration
CLICKHOUSE_HOST = os.getenv("CLICKHOUSE_HOST", "clickhouse")
CLICKHOUSE_PORT = os.getenv("CLICKHOUSE_PORT", 9000)
CLICKHOUSE_USER = os.getenv("CLICKHOUSE_USER", "default")
CLICKHOUSE_PASSWORD = os.getenv("CLICKHOUSE_PASSWORD", "")
CLICKHOUSE_DB = os.getenv("CLICKHOUSE_DB", "default")
CLICKHOUSE_TABLE = os.getenv("CLICKHOUSE_TABLE", "applicants")

# Local File Paths within the Airflow Worker
LOCAL_STAGING_DIR = os.getenv("LOCAL_STAGING_DIR", "/tmp/etl_staging")
LOCAL_PROCESSED_DIR = os.getenv("LOCAL_PROCESSED_DIR", "/tmp/etl_processed")
# --- MODIFIED: Removed 'id' and 'email' from the required columns ---
EXPECTED_COLUMNS = [h.strip() for h in os.getenv("EXPECTED_COLUMNS", "name,dob").split(",")]


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
    (Logic from extract.py)
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

import pandas as pd
import hashlib

# Columns to be tokenized
TOKENIZED_COLUMNS = ["name"]

def tokenize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    Replaces specified columns with a one-way hash token.
    (Placeholder logic)
    """
    for col in TOKENIZED_COLUMNS:
        if col in df.columns:
            # Use a simple one-way hash for tokenization
            df[col] = df[col].apply(
                lambda x: hashlib.sha256(str(x).encode()).hexdigest()
            )
    return df

def perform_transform(staging_path: str) -> str:
    """
    Cleans the staged CSV, tokenizes it, and produces a processed file.
    (Logic from transform.py)
    """
    os.makedirs(LOCAL_PROCESSED_DIR, exist_ok=True)
    try:
        logger.info("Reading staging file %s", staging_path)
        df = pd.read_csv(staging_path)

        # --- Data Cleaning (existing logic) ---
        df.columns = [c.strip().lower() for c in df.columns]
        df = df.dropna(how="all")
        for c in df.select_dtypes(include="object").columns:
            df[c] = df[c].astype(str).str.strip()
        
        # This is for demonstration purposes. The document mentions tokenizing columns,
        # but this simple name standardization might not be necessary after tokenization.
        if "name" in df.columns:
            df["name"] = df["name"].apply(lambda v: v.title() if isinstance(v, str) else v)
        
        # --- NEW: Tokenization Logic ---
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
    (Logic from load.py)
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
    (Logic from archive.py)
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
    ## ETL Pipeline (Single File Implementation)
    This DAG contains all logic for an ETL process in a single file.
    **Trigger with configuration:** `{"minioKey": "your-file-name.csv"}`
    """,
    tags=["etl", "minio", "clickhouse", "single-file"],
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