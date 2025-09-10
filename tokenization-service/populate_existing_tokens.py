#!/usr/bin/env python3
"""
Script to populate the tokenization service with mappings for existing ClickHouse data.
Run this after setting up the tokenization service to enable detokenization of existing data.
"""

import asyncpg
import asyncio
import os
import logging
from clickhouse_driver import Client

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
CLICKHOUSE_HOST = os.getenv("CLICKHOUSE_HOST", "clickhouse")
CLICKHOUSE_USER = os.getenv("CLICKHOUSE_USER", "user") 
CLICKHOUSE_PASSWORD = os.getenv("CLICKHOUSE_PASSWORD", "password")
CLICKHOUSE_DB = os.getenv("CLICKHOUSE_DB", "default")

TOKENIZATION_DB_URL = os.getenv("TOKENIZATION_DB_URL", "postgresql://tokenization_user:tokenization_pass@tokenization_postgres:5432/tokenization_db")

# Sample reverse mappings (you'd need to determine these based on your actual data)
# In a real scenario, you might have this from your original data sources
SAMPLE_REVERSE_MAPPINGS = {
    '8ad85682281d598a24c32d2a6bcfcb5c2a061daaa10573bea82c4b1e206f6cc7': 'John Smith',
    '845a98c681c21f689282452d2373fddc551a97dd73a436ebbce29a626f2c3253': 'Emily Johnson',
    '7670c53359ada168c135df2a9fc625f2ce7e1203a5a751cc35707ffe050afb55': 'Michael Brown',
    '491dee8938507fa813857a7bd4fd92fd7ec4f569d6fc68568e109dcc31e3cbf5': 'Sarah Davis',
    '50f51573d925372bbddbe51a5ac8d25635ee015192f48c318fdbd44ad0d6ee7c': 'David Wilson',
    '13230ebda842c34124c04cda22aa11770398ee53716ddf828d90f1c7c6bfcb53': 'Alice Brown',
    '348208f5e6e839fbde9c98b575305d6eae578e0f0d6eadf4577705f82ec5a6a6': 'Robert Johnson',
    'a8c156eb584478be06335fc27abff39a6cbb5c2459d891619c33b10c922e55e9': 'Maria Garcia',
    '6964bf96867b27c7828d095021478835daa2791a9aab55fd7c73adc5e5337380': 'William Davis',
    '2387b0db4afa1d7510263f5377d89a0ae81f41bff2919f12173d1e042b0be5b3': 'Jennifer Wilson',
}

async def populate_tokenization_database():
    """
    Directly populate the tokenization database with existing token mappings.
    """
    try:
        conn = await asyncpg.connect(TOKENIZATION_DB_URL)
        
        for token, original_value in SAMPLE_REVERSE_MAPPINGS.items():
            await conn.execute("""
                INSERT INTO token_mappings (token, original_value, data_type, created_at)
                VALUES ($1, $2, $3, NOW())
                ON CONFLICT (token) DO NOTHING
            """, token, original_value, "name")
            
            logger.info(f"Populated mapping: {token[:8]}... -> {original_value}")
        
        await conn.close()
        logger.info(f"Successfully populated {len(SAMPLE_REVERSE_MAPPINGS)} token mappings")
        
    except Exception as e:
        logger.error(f"Failed to populate tokenization database: {e}")
        raise

def get_existing_tokens_from_clickhouse():
    """
    Get all existing tokens from ClickHouse to understand what needs to be mapped.
    """
    try:
        client = Client(
            host=CLICKHOUSE_HOST,
            user=CLICKHOUSE_USER,
            password=CLICKHOUSE_PASSWORD,
            database=CLICKHOUSE_DB,
        )
        
        # Get unique hashed names from ClickHouse
        result = client.execute("SELECT DISTINCT name FROM applicants WHERE length(name) = 64")
        unique_tokens = [row[0] for row in result]
        
        logger.info(f"Found {len(unique_tokens)} unique tokens in ClickHouse")
        return unique_tokens
        
    except Exception as e:
        logger.error(f"Failed to query ClickHouse: {e}")
        raise

async def main():
    """
    Main function to populate the tokenization service with existing data.
    """
    logger.info("Starting tokenization service population...")
    
    # Get existing tokens from ClickHouse
    existing_tokens = get_existing_tokens_from_clickhouse()
    logger.info(f"Found {len(existing_tokens)} tokens in ClickHouse")
    
    # Show which tokens we have mappings for
    mapped_tokens = set(SAMPLE_REVERSE_MAPPINGS.keys())
    unmapped_tokens = set(existing_tokens) - mapped_tokens
    
    logger.info(f"Have mappings for: {len(mapped_tokens)} tokens")
    logger.info(f"Missing mappings for: {len(unmapped_tokens)} tokens")
    
    if unmapped_tokens:
        logger.warning("Unmapped tokens (will show as [UNKNOWN] in reports):")
        for token in list(unmapped_tokens)[:5]:  # Show first 5
            logger.warning(f"  {token[:8]}...")
    
    # Populate the tokenization database
    await populate_tokenization_database()
    
    logger.info("Tokenization service population completed!")
    logger.info("You can now use the detokenization endpoints to get readable names.")

if __name__ == "__main__":
    asyncio.run(main())