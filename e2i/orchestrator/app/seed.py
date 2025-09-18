from __future__ import annotations
from sqlalchemy.orm import Session
from .models import Pipeline

SEED_PIPELINES = [
    {
        "key": "etl_pipeline",
        "name": "ETL Pipeline",
        "dag_id": "etl_pipeline",
        "description": "Main ETL pipeline for CSV data ingestion",
        "is_active": True,
        "config": {"max_retries": 3, "timeout": 3600}
    },
    {
        "key": "tokenize_load", 
        "name": "Tokenize and Load",
        "dag_id": "tokenize_load",
        "description": "Pipeline for tokenizing PII and loading data",
        "is_active": True,
        "config": {"enable_tokenization": True}
    },
    {
        "key": "e2i_tokenize_load",
        "name": "Tokenize & Load (alias)",
        "dag_id": "tokenize_load",
        "description": "Alias for tokenize_load pipeline",
        "is_active": True,
        "config": {}
    },
    {
        "key": "archive",
        "name": "Archive to cold storage",
        "dag_id": "archive_pipeline",
        "description": "Archive processed files to cold storage",
        "is_active": True,
        "config": {}
    }
]

def seed_pipelines(db: Session):
    for s in SEED_PIPELINES:
        existing = db.query(Pipeline).filter_by(key=s["key"]).first()
        if existing:
            # Optional: update existing fields
            existing.name = s["name"]
            existing.dag_id = s["dag_id"]
            existing.description = s.get("description", "")
            existing.is_active = s.get("is_active", True)
            existing.config = s.get("config", {})
        else:
            db.add(Pipeline(**s))
    db.commit()
