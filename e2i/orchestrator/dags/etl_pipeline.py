# etl_pipeline.py

from __future__ import annotations

import logging
import os
import pandas as pd
import numpy as np
import requests
import hashlib
import psycopg2
import json
import boto3
from datetime import datetime
from typing import Dict, List, Any

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
CLICKHOUSE_USER = os.getenv("CLICKHOUSE_USER", "user")
CLICKHOUSE_PASSWORD = os.getenv("CLICKHOUSE_PASSWORD", "password")
CLICKHOUSE_DB = os.getenv("CLICKHOUSE_DB", "e2i_warehouse")

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
# Helper Functions
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

def get_clickhouse_client():
    """Returns a ClickHouse client instance."""
    return Client(
        host=CLICKHOUSE_HOST,
        user=CLICKHOUSE_USER,
        password=CLICKHOUSE_PASSWORD,
        database=CLICKHOUSE_DB
    )

def get_upload_mappings(upload_id: str) -> Dict[str, Any]:
    """
    ENHANCED: Get the full template configuration for a given upload from the Django database.
    Now includes support for merged_from_columns.
    """
    conn = None
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()

        # ENHANCED: Get mappings with merged_from_columns support
        cursor.execute("""
            SELECT
                dt.name as template_name,
                dt.target_table,
                cm.source_column,
                tc.name as target_column,
                tc.data_type,
                tc.processing_type,
                tc.is_required,
                tc.max_length,
                cm.transform_function,
                cm.transform_params,
                tc.processing_config,
                tc.merged_from_columns
            FROM column_mappings cm
            JOIN uploads u ON cm.upload_id = u.id
            JOIN data_templates dt ON cm.template_id = dt.id
            JOIN template_columns tc ON cm.target_column_id = tc.id
            WHERE u.id = %s
        """, (upload_id,))

        rows = cursor.fetchall()
        if not rows:
            raise ValueError(f"No column mappings found for upload_id: {upload_id}")

        template_name = rows[0][0]
        target_table = rows[0][1]

        mappings = []
        for row in rows:
            merged_from_columns = row[11]  # This could be None or a JSON array
            transform_params = row[9] or {}
            
            # Parse merged_from_columns if it exists
            if merged_from_columns:
                try:
                    if isinstance(merged_from_columns, str):
                        merged_from_columns = json.loads(merged_from_columns)
                except (json.JSONDecodeError, TypeError):
                    merged_from_columns = None
            
            # Check if this is a user-mapped merged column (from transform_params)
            if transform_params.get('is_merged') and transform_params.get('merged_sources'):
                # This is a user-mapped merged column, use the sources from transform_params
                merged_from_columns = transform_params['merged_sources']
                logger.info(f"Found user-mapped merged column '{row[3]}' with sources: {merged_from_columns}")
            
            mappings.append({
                'source_column': row[2],
                'target_column': row[3],
                'data_type': row[4],
                'processing_type': row[5],
                'is_required': row[6],
                'max_length': row[7],
                'transform_function': row[8],
                'transform_params': transform_params,
                'processing_config': row[10] or {},
                'merged_from_columns': merged_from_columns,
            })

        logger.info(f"Found template '{template_name}' targeting table '{target_table}' with {len(mappings)} mappings.")

        return {
            'template_name': template_name,
            'target_table': target_table,
            'mappings': mappings
        }

    except Exception as e:
        logger.error(f"Failed to get template mappings for upload {upload_id}: {e}")
        raise
    finally:
        if conn:
            conn.close()

def tokenize_with_service(values: list, data_type: str = "name") -> dict:
    """Call the tokenization service to tokenize values."""
    if not values:
        return {}
    try:
        response = requests.post(
            f"{TOKENIZATION_ENDPOINT}/api/v1/tokenize",
            json={"values": values, "data_type": data_type},
            headers={"Authorization": f"Bearer {TOKENIZATION_API_KEY}", "Content-Type": "application/json"},
            timeout=30
        )
        response.raise_for_status()
        result = response.json()
        return result.get("mappings", {})
    except requests.exceptions.RequestException as e:
        logger.error(f"Tokenization service call failed, falling back to local hashing: {e}")
        return {value: hashlib.sha256(str(value).encode()).hexdigest() for value in values}

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
        # FIXED: Properly handle extraction to avoid numpy arrays
        extracted = series.astype(str).str.extract(r'(\d+)', expand=False)
        return extracted.fillna('').astype(str)
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
            # Convert to numeric first, handling errors
            numeric_series = pd.to_numeric(series, errors='coerce')
            # For ClickHouse compatibility, convert NaN to None and use object dtype
            # This allows ClickHouse to handle nullable integers properly
            return numeric_series.where(pd.notna(numeric_series), None).astype('object')

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
        return series.astype(str)  # Fallback to string
    
def apply_processing(series: pd.Series, mapping: Dict) -> pd.Series:
    """Apply processing like tokenization or hashing."""
    processing_type = mapping.get('processing_type', 'none')

    if processing_type == 'tokenize':
        unique_values = series.dropna().unique().tolist()
        if not unique_values:
            return series
        token_map = tokenize_with_service(unique_values)
        return series.map(token_map).fillna(series)

    if processing_type == 'hash':
        return series.apply(lambda x: hashlib.sha256(str(x).encode()).hexdigest() if pd.notna(x) else x)

    return series    

def clean_dataframe_for_clickhouse(df: pd.DataFrame) -> pd.DataFrame:
    """
    ADDED: Convert any numpy arrays or complex objects to strings for ClickHouse compatibility.
    """
    cleaned_df = df.copy()
    
    for col in cleaned_df.columns:
        # Check if any values in the column are numpy arrays or complex objects
        sample_values = cleaned_df[col].dropna().head(10).tolist()
        
        has_arrays = any(isinstance(val, np.ndarray) for val in sample_values)
        has_complex = any(isinstance(val, (list, tuple, dict)) for val in sample_values)
        
        if has_arrays:
            logger.warning(f"Column '{col}' contains numpy arrays, converting to strings")
            cleaned_df[col] = cleaned_df[col].apply(
                lambda x: ','.join(map(str, x)) if isinstance(x, np.ndarray) else x
            )
        elif has_complex:
            logger.warning(f"Column '{col}' contains complex objects, converting to strings")
            cleaned_df[col] = cleaned_df[col].apply(
                lambda x: str(x) if isinstance(x, (list, tuple, dict)) else x
            )
        
        # Ensure all values are properly typed for ClickHouse
        if cleaned_df[col].dtype == 'object':
            # Convert object columns to string and handle any remaining complex types
            cleaned_df[col] = cleaned_df[col].apply(
                lambda x: str(x) if not pd.isna(x) and not isinstance(x, (str, int, float, bool)) else x
            )
    
    return cleaned_df

def debug_dataframe_types(df: pd.DataFrame, stage: str = "unknown"):
    """
    ENHANCED: Debug function to identify problematic column types and data issues.
    """
    logger.info(f"=== DataFrame Debug at {stage} ===")
    logger.info(f"Shape: {df.shape}")
    
    for col in df.columns:
        col_dtype = df[col].dtype
        non_null_count = df[col].count()
        null_count = df[col].isna().sum()
        
        if non_null_count > 0:
            sample_val = df[col].dropna().iloc[0]
            sample_type = type(sample_val)
        else:
            sample_val = "ALL_NULL"
            sample_type = "N/A"
        
        logger.info(f"Column '{col}': dtype={col_dtype}, non_null={non_null_count}, null={null_count}, sample_val={sample_val}, sample_type={sample_type}")
        
        # Check for arrays and complex types in the column
        if non_null_count > 0:
            sample_values = df[col].dropna().head(5).tolist()
            has_arrays = any(isinstance(val, np.ndarray) for val in sample_values)
            has_complex = any(isinstance(val, (list, tuple, dict)) for val in sample_values)
            
            if has_arrays:
                logger.error(f"❌ Column '{col}' contains numpy arrays!")
            if has_complex:
                logger.warning(f"⚠️ Column '{col}' contains complex objects!")
                
            # Check for mixed types
            unique_types = set(type(val) for val in sample_values)
            if len(unique_types) > 1:
                logger.warning(f"⚠️ Column '{col}' has mixed types: {unique_types}")
            
    logger.info("=== End Debug ===")

def merge_columns(df: pd.DataFrame, columns_to_merge: List[str], separator: str = " ") -> pd.Series:
    """
    ADDED: Merge multiple columns into a single column.
    """
    logger.info(f"=== MERGE COLUMNS DEBUG ===")
    logger.info(f"DataFrame columns: {list(df.columns)}")
    logger.info(f"Columns to merge: {columns_to_merge}")
    logger.info(f"DataFrame shape: {df.shape}")
    
    available_columns = [col for col in columns_to_merge if col in df.columns]
    missing_columns = [col for col in columns_to_merge if col not in df.columns]
    
    logger.info(f"Available columns for merging: {available_columns}")
    logger.info(f"Missing columns: {missing_columns}")
    
    if not available_columns:
        logger.warning(f"None of the columns to merge {columns_to_merge} are available in the data")
        return pd.Series([None] * len(df), dtype='object')
    
    if len(available_columns) == 1:
        logger.info(f"Only one column '{available_columns[0]}' available for merging, using it directly")
        result = df[available_columns[0]].astype(str)
        logger.info(f"Single column merge result sample: {result.head(3).tolist()}")
        return result
    
    logger.info(f"Merging columns: {available_columns}")
    
    # Show sample data from columns being merged
    for col in available_columns:
        sample_data = df[col].head(3).tolist()
        logger.info(f"Sample data from '{col}': {sample_data}")
    
    # Merge available columns, skipping null values
    merged_series = df[available_columns].apply(
        lambda row: separator.join(
            str(val) for val in row if pd.notna(val) and str(val).strip() != ''
        ), axis=1
    )
    
    # Replace empty strings with None
    merged_series = merged_series.apply(lambda x: None if x == '' else x)
    
    logger.info(f"Merged result sample: {merged_series.head(3).tolist()}")
    logger.info(f"=== END MERGE COLUMNS DEBUG ===")
    
    return merged_series

def apply_column_transformations(df: pd.DataFrame, mappings: List[Dict]) -> pd.DataFrame:
    """
    ENHANCED: Apply all defined transformations based on the mapping configuration.
    Now supports column merging via merged_from_columns.
    """
    result_df = pd.DataFrame()
    
    for mapping in mappings:
        source_col = mapping['source_column']
        target_col = mapping['target_column']
        merged_from_columns = mapping.get('merged_from_columns')

        logger.info(f"=== PROCESSING MAPPING ===")
        logger.info(f"Target column: {target_col}")
        logger.info(f"Source column: {source_col}")
        logger.info(f"Merged from columns: {merged_from_columns}")
        logger.info(f"Transform params: {mapping.get('transform_params', {})}")

        # Check if this is a column merge operation
        if merged_from_columns and isinstance(merged_from_columns, list):
            logger.info(f"Processing merged column '{target_col}' from {merged_from_columns}")
            
            # For merged columns, always merge the specified columns
            # Check if all required columns exist in the data
            missing_cols = [col for col in merged_from_columns if col not in df.columns]
            if missing_cols:
                logger.warning(f"Some columns for merging are missing: {missing_cols}. Available columns: {list(df.columns)}")
                # Create empty series if columns are missing
                source_data = pd.Series([None] * len(df), dtype='object')
            else:
                # All columns exist, perform the merge
                logger.info(f"Merging columns: {merged_from_columns}")
                source_data = merge_columns(df, merged_from_columns)
            
        elif source_col not in df.columns:
            logger.warning(f"Source column '{source_col}' not found in data. Available columns: {list(df.columns)}")
            if mapping.get('is_required', False):
                raise ValueError(f"Required source column '{source_col}' not found. Available: {list(df.columns)}")
            
            # FIXED: Create proper empty/null values based on target data type
            data_type = mapping.get('data_type', 'string')
            if data_type == 'integer':
                result_df[target_col] = pd.Series([None] * len(df), dtype='Int64')
            elif data_type == 'float':
                result_df[target_col] = pd.Series([None] * len(df), dtype='float64')
            elif data_type == 'boolean':
                result_df[target_col] = pd.Series([None] * len(df), dtype='boolean')
            elif data_type in ['datetime', 'date']:
                result_df[target_col] = pd.Series([None] * len(df), dtype='datetime64[ns]')
            else:  # string or unknown
                result_df[target_col] = pd.Series([None] * len(df), dtype='object')
            continue
        else:
            # Normal single-column mapping
            source_data = df[source_col].copy()

        # Apply transformations step by step with error handling
        try:
            if mapping.get('transform_function'):
                source_data = apply_transform_function(source_data, mapping['transform_function'], mapping.get('transform_params', {}))

            source_data = convert_data_type(source_data, mapping['data_type'], mapping)
            source_data = apply_processing(source_data, mapping)

            result_df[target_col] = source_data
            
        except Exception as e:
            logger.error(f"Error processing column '{source_col}' -> '{target_col}': {e}")
            # Fallback: convert to string, but handle the case where source_col doesn't exist
            if merged_from_columns:
                # For merged columns, try to create a basic merge as fallback
                try:
                    fallback_data = merge_columns(df, merged_from_columns)
                    result_df[target_col] = fallback_data.astype(str)
                except:
                    result_df[target_col] = pd.Series([''] * len(df), dtype='object')
            elif source_col in df.columns:
                result_df[target_col] = df[source_col].astype(str)
            else:
                result_df[target_col] = pd.Series([''] * len(df), dtype='object')
            
    return result_df

def update_upload_processing_status(upload_id: str, status: str, details: Dict = None):
    """Update upload status in the main Django database."""
    conn = None
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        error_message = details.get('error') if details else None

        cursor.execute(
            "UPDATE uploads SET status = %s, error = %s, updated_at = NOW() WHERE id = %s",
            (status, error_message, upload_id)
        )
        conn.commit()
        logger.info(f"Updated upload {upload_id} status to '{status}' in Django DB.")
    except Exception as e:
        logger.error(f"Failed to update upload status in Django DB: {e}")
    finally:
        if conn:
            conn.close()

def create_table_if_not_exists(client: Client, table_name: str, df: pd.DataFrame, upload_id: str = None):
    """
    ENHANCED: Dynamically creates a ClickHouse table based on the DataFrame's actual dtypes.
    Also adds missing columns to existing tables. Now includes ALL template columns including merged ones.
    """
    logger.info(f"Checking if table '{CLICKHOUSE_DB}.{table_name}' exists...")

    type_mapping = {
        'int64': 'Int64',
        'Int64': 'Int64',  # Handle nullable integers
        'float64': 'Float64',
        'datetime64[ns]': 'DateTime',
        'bool': 'UInt8',
        'object': 'String'
    }

    # First, try to get existing table structure
    existing_columns = set()
    try:
        result = client.execute(f"DESCRIBE {CLICKHOUSE_DB}.`{table_name}`")
        existing_columns = {row[0] for row in result}
        logger.info(f"Existing table columns: {existing_columns}")
    except Exception as e:
        logger.info(f"Table doesn't exist yet or error getting structure: {e}")
        existing_columns = set()

    # Get ALL template columns including merged ones from the database
    all_template_columns = set()
    if upload_id:
        try:
            conn = psycopg2.connect(**DB_CONFIG)
            cursor = conn.cursor()
            
            # Get all template columns for this upload
            cursor.execute("""
                SELECT tc.name, tc.data_type
                FROM column_mappings cm
                JOIN uploads u ON cm.upload_id = u.id
                JOIN template_columns tc ON cm.target_column_id = tc.id
                WHERE u.id = %s
            """, (upload_id,))
            
            template_rows = cursor.fetchall()
            for row in template_rows:
                col_name, data_type = row
                all_template_columns.add((col_name, data_type))
            
            conn.close()
            logger.info(f"Found {len(all_template_columns)} template columns: {[col[0] for col in all_template_columns]}")
        except Exception as e:
            logger.warning(f"Could not get template columns from database: {e}")
            all_template_columns = set()

    # Prepare column definitions for all DataFrame columns
    columns_defs = []
    new_columns = []
    
    # First, add DataFrame columns
    for col_name, dtype in df.dtypes.items():
        # Check if this is an integer column stored as object (with None values)
        if str(dtype) == 'object':
            # Check if the column contains integers or None values
            sample_values = df[col_name].dropna().head(10)
            if not sample_values.empty and all(isinstance(val, (int, float)) and not isinstance(val, bool) for val in sample_values):
                # This is likely an integer column with None values
                ch_type = 'Int64'
            else:
                ch_type = 'String'
        else:
            ch_type = type_mapping.get(str(dtype), 'String')
        
        columns_defs.append(f"`{col_name}` Nullable({ch_type})")
        
        # Track new columns that need to be added
        if col_name not in existing_columns:
            new_columns.append((col_name, ch_type))
    
    # Then, add template columns that are not in the DataFrame (like merged columns)
    for col_name, data_type in all_template_columns:
        if col_name not in df.columns and col_name not in existing_columns:
            # Map template data type to ClickHouse type
            if data_type == 'integer':
                ch_type = 'Int64'
            elif data_type == 'float':
                ch_type = 'Float64'
            elif data_type in ['datetime', 'date']:
                ch_type = 'DateTime'
            elif data_type == 'boolean':
                ch_type = 'UInt8'
            else:  # string or unknown
                ch_type = 'String'
            
            columns_defs.append(f"`{col_name}` Nullable({ch_type})")
            new_columns.append((col_name, ch_type))
            logger.info(f"Adding template column '{col_name}' ({ch_type}) that's not in DataFrame")

    columns_str = ',\n    '.join(columns_defs)
    order_by_key = df.columns[0] if not df.columns.empty else 'id'

    logger.info(f"Creating table with columns: {[col.split('`')[1] for col in columns_defs]}")
    logger.info(f"DataFrame columns: {list(df.columns)}")
    logger.info(f"New columns to add: {[col[0] for col in new_columns]}")

    # Create table if it doesn't exist
    create_sql = f"""
    CREATE TABLE IF NOT EXISTS {CLICKHOUSE_DB}.`{table_name}`
    (
        {columns_str}
    )
    ENGINE = MergeTree()
    ORDER BY `{order_by_key}`
    SETTINGS allow_nullable_key = 1
    """

    logger.info(f"Executing CREATE TABLE statement if needed for table '{table_name}'")
    logger.info(f"CREATE SQL: {create_sql}")
    try:
        client.execute(create_sql)
        logger.info(f"Table '{table_name}' is ready.")
    except Exception as e:
        logger.error(f"Failed to create table '{table_name}': {e}")
        raise

    # Add missing columns to existing table
    for col_name, ch_type in new_columns:
        try:
            alter_sql = f"ALTER TABLE {CLICKHOUSE_DB}.`{table_name}` ADD COLUMN `{col_name}` Nullable({ch_type})"
            logger.info(f"Adding missing column: {alter_sql}")
            client.execute(alter_sql)
            logger.info(f"Successfully added column '{col_name}' to table '{table_name}'")
        except Exception as e:
            logger.error(f"Failed to add column '{col_name}' to table '{table_name}': {e}")
            # Don't raise here - column might already exist or there might be other issues
            # The main insertion will fail with a clear error if there are still issues

# -------------------------------------------------------------------
# Core ETL Logic
# -------------------------------------------------------------------

def perform_extract(file_path: str) -> str:
    """Downloads raw CSV from MinIO to a local staging location."""
    os.makedirs(LOCAL_STAGING_DIR, exist_ok=True)
    client = _get_s3_client()
    filename = os.path.basename(file_path)
    staging_path = os.path.join(LOCAL_STAGING_DIR, filename)
    try:
        logger.info(f"Downloading s3://{MINIO_LANDING_BUCKET}/{file_path} -> {staging_path}")
        client.download_file(MINIO_LANDING_BUCKET, file_path, staging_path)
    except (BotoCoreError, ClientError) as e:
        raise RuntimeError(f"Failed to download {file_path}") from e
    return staging_path

def perform_transform(staging_path: str, upload_id: str) -> Dict[str, str]:
    """
    ENHANCED: Transforms data and returns both the processed file path AND the target table.
    """
    os.makedirs(LOCAL_PROCESSED_DIR, exist_ok=True)
    try:
        # ENHANCED: Read CSV with better parameters to handle complex data
        df = pd.read_csv(staging_path, dtype=str, keep_default_na=False, na_values=[''])
        df.columns = df.columns.str.strip()

        logger.info(f"Loaded CSV with shape: {df.shape}")
        debug_dataframe_types(df, "after_csv_load")

        mapping_config = get_upload_mappings(upload_id)
        target_table = mapping_config['target_table']

        processed_df = apply_column_transformations(df, mapping_config['mappings'])

        if processed_df.empty:
            raise ValueError("Processed DataFrame is empty. Check mappings and source file.")

        debug_dataframe_types(processed_df, "after_transformations")

        processed_filename = f"processed_{os.path.basename(staging_path)}"
        processed_path = os.path.join(LOCAL_PROCESSED_DIR, processed_filename)
        processed_df.to_csv(processed_path, index=False)

        logger.info(f"Transform completed. Processed file: {processed_path}, Target table: {target_table}")
        update_upload_processing_status(upload_id, 'transformed')

        return {'processed_path': processed_path, 'target_table': target_table}

    except Exception as e:
        logger.exception(f"Transformation failed for {staging_path}")
        update_upload_processing_status(upload_id, 'failed', {'error': str(e)})
        raise

def perform_load(processed_path: str, target_table: str, upload_id: str):
    """
    ENHANCED: Loads a processed CSV into a dynamically determined ClickHouse table.
    """
    logger.info(f"Starting load of {processed_path} into table {target_table}")
    client = get_clickhouse_client()
    try:
        df = pd.read_csv(processed_path)
        
        # Add debugging information
        logger.info(f"DataFrame shape: {df.shape}")
        logger.info(f"DataFrame dtypes: {df.dtypes.to_dict()}")
        
        # Check for problematic columns before cleaning
        for col in df.columns:
            if df[col].dtype == 'float64' and df[col].isna().all():
                logger.warning(f"Column '{col}' is entirely NaN - likely from missing source column")
            elif df[col].dtype == 'float64' and not df[col].dropna().empty:
                sample_val = df[col].dropna().iloc[0]
                logger.info(f"Column '{col}' float64 sample value: {sample_val} (type: {type(sample_val)})")
        
        debug_dataframe_types(df, "before_cleaning")
        
        # ENHANCED: Clean the dataframe before insertion to handle numpy arrays and type issues
        df = clean_dataframe_for_clickhouse(df)
        
        debug_dataframe_types(df, "after_cleaning")
        
        # ADDED: Final type validation and conversion
        for col in df.columns:
            # Ensure no float NaN values remain in object columns
            if df[col].dtype == 'object':
                df[col] = df[col].apply(lambda x: None if pd.isna(x) else str(x) if x is not None else None)
            elif df[col].dtype == 'float64' and df[col].isna().all():
                # Convert entirely NaN float columns to object with None values
                df[col] = pd.Series([None] * len(df), dtype='object')
                
        logger.info(f"Final DataFrame dtypes: {df.dtypes.to_dict()}")
            
        create_table_if_not_exists(client, target_table, df, upload_id)

        logger.info(f"Inserting {len(df)} rows into ClickHouse table '{target_table}'")
        
        try:
            client.insert_dataframe(f"INSERT INTO {CLICKHOUSE_DB}.`{target_table}` VALUES", df)
        except Exception as insert_error:
            logger.error(f"insert_dataframe failed: {insert_error}")
            logger.info("Trying alternative insertion method...")
            
            # Alternative insertion method using records with explicit column names
            records = df.to_dict('records')
            
            # Get column names from DataFrame
            column_names = list(df.columns)
            columns_str = ', '.join([f'`{col}`' for col in column_names])
            
            logger.info(f"Alternative insertion: inserting {len(records)} records with columns: {column_names}")
            
            # Clean records for ClickHouse compatibility
            cleaned_records = []
            for record in records:
                cleaned_record = {}
                for key, value in record.items():
                    if pd.isna(value) or value is None:
                        cleaned_record[key] = None
                    elif isinstance(value, (int, float)) and not isinstance(value, bool):
                        # Handle numeric values - convert to int if it's a whole number
                        if isinstance(value, float) and value.is_integer():
                            cleaned_record[key] = int(value)
                        else:
                            cleaned_record[key] = value
                    elif isinstance(value, str):
                        # Try to convert string numbers to actual numbers
                        try:
                            if '.' in value:
                                float_val = float(value)
                                if float_val.is_integer():
                                    cleaned_record[key] = int(float_val)
                                else:
                                    cleaned_record[key] = float_val
                            else:
                                cleaned_record[key] = int(value)
                        except (ValueError, TypeError):
                            cleaned_record[key] = value
                    else:
                        cleaned_record[key] = str(value) if value is not None else None
                cleaned_records.append(cleaned_record)
            
            # Use explicit column names in INSERT statement
            insert_sql = f"INSERT INTO {CLICKHOUSE_DB}.`{target_table}` ({columns_str}) VALUES"
            logger.info(f"Executing: {insert_sql}")
            client.execute(insert_sql, cleaned_records)

        update_upload_processing_status(upload_id, 'completed')
        logger.info(f"Successfully loaded data into '{target_table}'")

    except Exception as e:
        logger.exception(f"Failed to insert data into ClickHouse table '{target_table}'")
        update_upload_processing_status(upload_id, 'failed', {'error': str(e)})
        raise
    finally:
        if os.path.exists(processed_path):
            os.remove(processed_path)

def perform_archive(file_path: str):
    """Moves the original file from landing to archive bucket in MinIO."""
    try:
        s3 = _get_s3_client()
        copy_source = {"Bucket": MINIO_LANDING_BUCKET, "Key": file_path}

        try:
            s3.head_bucket(Bucket=MINIO_ARCHIVE_BUCKET)
        except ClientError:
            s3.create_bucket(Bucket=MINIO_ARCHIVE_BUCKET)

        s3.copy(copy_source, MINIO_ARCHIVE_BUCKET, file_path)
        s3.delete_object(Bucket=MINIO_LANDING_BUCKET, Key=file_path)
        logger.info(f"Archived {file_path} to {MINIO_ARCHIVE_BUCKET}")
    except (BotoCoreError, ClientError) as e:
        raise RuntimeError(f"Archive failed for {file_path}: {e}")


# -------------------------------------------------------------------
# Airflow Task Wrapper Functions
# -------------------------------------------------------------------

def run_extract(**kwargs):
    conf = kwargs["dag_run"].conf
    minio_key = conf.get("minioKey")
    return perform_extract(file_path=minio_key)

def run_transform(**kwargs):
    ti = kwargs["ti"]
    staging_path = ti.xcom_pull(task_ids="extract")
    upload_id = kwargs["dag_run"].conf.get("uploadId")
    return perform_transform(staging_path=staging_path, upload_id=upload_id)

def run_load(**kwargs):
    ti = kwargs["ti"]
    transform_output = ti.xcom_pull(task_ids="transform")
    processed_path = transform_output['processed_path']
    target_table = transform_output['target_table']
    upload_id = kwargs["dag_run"].conf.get("uploadId")
    perform_load(processed_path=processed_path, target_table=target_table, upload_id=upload_id)

def run_archive(**kwargs):
    minio_key = kwargs["dag_run"].conf.get("minioKey")
    perform_archive(file_path=minio_key)

# -------------------------------------------------------------------
# DAG Definition
# -------------------------------------------------------------------

with DAG(
    dag_id="etl_pipeline",
    start_date=days_ago(1),
    schedule_interval=None,
    catchup=False,
    doc_md="""
    ## Dynamic ETL Pipeline (Corrected)
    This DAG processes any CSV file based on a user-defined template.
    It fetches mappings and the target table name from a database, dynamically
    creates the table in ClickHouse if it doesn't exist, and loads the data.
    **Trigger with config:** `{"minioKey": "path/to/file.csv", "uploadId": "upload-uuid"}`
    """,
    tags=["etl", "dynamic", "template-based"],
) as dag:
    extract_task = PythonOperator(task_id="extract", python_callable=run_extract)
    transform_task = PythonOperator(task_id="transform", python_callable=run_transform)
    load_task = PythonOperator(task_id="load", python_callable=run_load)
    archive_task = PythonOperator(task_id="archive", python_callable=run_archive)

    extract_task >> transform_task >> load_task >> archive_task