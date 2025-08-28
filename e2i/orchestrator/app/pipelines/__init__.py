def get_pipeline_tasks(pipeline_key: str):
    if pipeline_key == "tokenize_load":
        return ["extract", "transform", "load", "archive"]
    return []
