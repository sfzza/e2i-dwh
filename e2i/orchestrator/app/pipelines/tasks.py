def extract(params: dict):
    print("Extracting from MinIO:", params["minioKey"])
    # TODO: add real MinIO download + validation
    return {"rowsProcessed": 1234}

def transform(params: dict):
    print("Transforming file:", params["minioKey"])
    # TODO: add real cleaning/tokenization
    return {"transformedRows": 1200}

def load(params: dict):
    print("Loading into ClickHouse")
    # TODO: insert into ClickHouse
    return {"rowsLoaded": 1200}

def archive(params: dict):
    print("Archiving file in MinIO")
    # TODO: move from landing → archive bucket
    return {"archived": True}
