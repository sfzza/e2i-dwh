# app/pipelines.py

PIPELINES = {
    "tokenize_load": ["extract", "transform", "load"],
    "archive": ["extract", "archive"],
    "e2i_tokenize_load": ["tokenize", "load"],
    "etl_pipeline": ["extract", "transform", "load", "archive"],  # 👈 add this
}


def get_pipeline_tasks(pipeline_key: str):
    return PIPELINES.get(pipeline_key, [])
