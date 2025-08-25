from __future__ import annotations
from sqlalchemy.orm import Session
from .models import Pipeline

SEEDS = [
    {"key": "tokenize_load", "name": "Tokenize & Load"},
    {"key": "e2i_tokenize_load", "name": "Tokenize & Load (alias)"},
    {"key": "archive", "name": "Archive to cold storage"},
]


def seed_pipelines(db: Session):
    for s in SEEDS:
        exists = db.query(Pipeline).filter_by(key=s["key"]).first()
        if not exists:
            db.add(Pipeline(**s, is_active=True))
    db.commit()
