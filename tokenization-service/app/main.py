# tokenization-service/app/main.py

from fastapi import FastAPI, HTTPException, Depends, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from typing import List, Dict, Optional
import hashlib
import os
import asyncpg
import json
from datetime import datetime
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Tokenization Service", version="1.0.0")
security = HTTPBearer()

# Configuration
API_KEY = os.getenv("TOKENIZATION_API_KEY", "secure-api-key-change-in-production")
DATABASE_URL = os.getenv("TOKENIZATION_DB_URL", "postgresql://tokenization_user:tokenization_pass@tokenization_postgres:5432/tokenization_db")

# Pydantic models
class TokenizeRequest(BaseModel):
    values: List[str]
    data_type: str = "name"  # name, email, phone, ssn, etc.

class DetokenizeRequest(BaseModel):
    tokens: List[str]
    
class TokenizeResponse(BaseModel):
    mappings: Dict[str, str]  # original_value -> token
    
class DetokenizeResponse(BaseModel):
    mappings: Dict[str, str]  # token -> original_value

# Security
async def verify_api_key(credentials: HTTPAuthorizationCredentials = Security(security)):
    if credentials.credentials != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return credentials.credentials

# Database connection
async def get_db_connection():
    return await asyncpg.connect(DATABASE_URL)

# Utility functions
def generate_token(value: str, data_type: str) -> str:
    """Generate a secure token for a value"""
    # Use SHA-256 with a salt (in production, use a more secure approach)
    salt = os.getenv("TOKENIZATION_SALT", "your-secret-salt-change-in-production")
    combined = f"{salt}:{data_type}:{value}"
    return hashlib.sha256(combined.encode()).hexdigest()

def audit_log(action: str, token_count: int, data_type: str = None):
    """Log tokenization/detokenization operations"""
    logger.info(f"AUDIT: {action} - {token_count} tokens - type: {data_type} - timestamp: {datetime.utcnow()}")

# API Endpoints
@app.post("/api/v1/tokenize", response_model=TokenizeResponse)
async def tokenize_values(request: TokenizeRequest, api_key: str = Depends(verify_api_key)):
    """
    Tokenize sensitive values and store the mapping securely.
    """
    try:
        conn = await get_db_connection()
        mappings = {}
        
        for value in request.values:
            token = generate_token(value, request.data_type)
            mappings[value] = token
            
            # Store the mapping in database
            await conn.execute("""
                INSERT INTO token_mappings (token, original_value, data_type, created_at)
                VALUES ($1, $2, $3, $4)
                ON CONFLICT (token) DO NOTHING
            """, token, value, request.data_type, datetime.utcnow())
        
        await conn.close()
        audit_log("TOKENIZE", len(request.values), request.data_type)
        
        return TokenizeResponse(mappings=mappings)
        
    except Exception as e:
        logger.error(f"Tokenization failed: {e}")
        raise HTTPException(status_code=500, detail="Tokenization failed")

@app.post("/api/v1/detokenize", response_model=DetokenizeResponse)
async def detokenize_values(request: DetokenizeRequest, api_key: str = Depends(verify_api_key)):
    """
    Detokenize tokens back to original values (privileged operation).
    """
    try:
        conn = await get_db_connection()
        mappings = {}
        
        for token in request.tokens:
            # Query the database for the original value
            row = await conn.fetchrow("""
                SELECT original_value, data_type 
                FROM token_mappings 
                WHERE token = $1
            """, token)
            
            if row:
                mappings[token] = row['original_value']
                
                # Log the detokenization access
                await conn.execute("""
                    INSERT INTO detokenization_audit (token, data_type, accessed_at)
                    VALUES ($1, $2, $3)
                """, token, row['data_type'], datetime.utcnow())
            else:
                logger.warning(f"Token not found: {token[:8]}...")
                mappings[token] = f"[UNKNOWN_TOKEN]"
        
        await conn.close()
        audit_log("DETOKENIZE", len(request.tokens))
        
        return DetokenizeResponse(mappings=mappings)
        
    except Exception as e:
        logger.error(f"Detokenization failed: {e}")
        raise HTTPException(status_code=500, detail="Detokenization failed")

@app.get("/api/v1/health")
async def health_check():
    """Health check endpoint"""
    try:
        conn = await get_db_connection()
        await conn.fetchval("SELECT 1")
        await conn.close()
        return {"status": "healthy", "timestamp": datetime.utcnow()}
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=503, detail="Service unavailable")

@app.get("/api/v1/stats")
async def get_stats(api_key: str = Depends(verify_api_key)):
    """Get tokenization statistics"""
    try:
        conn = await get_db_connection()
        
        # Get token counts by data type
        token_stats = await conn.fetch("""
            SELECT data_type, COUNT(*) as count
            FROM token_mappings
            GROUP BY data_type
        """)
        
        # Get recent detokenization activity
        recent_access = await conn.fetchval("""
            SELECT COUNT(*)
            FROM detokenization_audit
            WHERE accessed_at > NOW() - INTERVAL '24 hours'
        """)
        
        await conn.close()
        
        return {
            "token_counts": {row['data_type']: row['count'] for row in token_stats},
            "detokenizations_24h": recent_access,
            "timestamp": datetime.utcnow()
        }
        
    except Exception as e:
        logger.error(f"Stats query failed: {e}")
        raise HTTPException(status_code=500, detail="Stats unavailable")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8004)