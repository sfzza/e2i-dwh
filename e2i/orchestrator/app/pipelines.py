# app/pipelines.py

PIPELINES = {
    "tokenize_load": ["extract", "transform", "load"],
    "archive": ["extract", "archive"]
}

def get_pipeline_tasks(pipeline_key: str):
    return PIPELINES.get(pipeline_key, [])
