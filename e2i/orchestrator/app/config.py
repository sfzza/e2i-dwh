import os

# Flag to control whether to use LocalWorker or Airflow
USE_LOCAL_WORKER = os.getenv("USE_LOCAL_WORKER", "true").lower() == "true"
