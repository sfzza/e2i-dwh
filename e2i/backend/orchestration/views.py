from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
import requests
import os
import uuid

class RunPipelineView(APIView):
    def post(self, request):
        airflow_url = os.environ.get("AIRFLOW_URL", "http://localhost:8080")
        dag_id = "poc_pipeline"

        trigger_url = f"{airflow_url}/api/v1/dags/{dag_id}/dagRuns"
        headers = {"Content-Type": "application/json"}

        # Get upload_id from request, or create dummy one
        upload_id = request.data.get("upload_id") or f"dummy-{uuid.uuid4()}"

        payload = {
            "conf": {
                "upload_id": upload_id
            }
        }

        try:
            response = requests.post(
                trigger_url,
                headers=headers,
                json=payload,
                auth=("admin", "admin")  # Airflow username/password
            )
            response.raise_for_status()
            return Response(response.json(), status=response.status_code)

        except requests.exceptions.RequestException as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
