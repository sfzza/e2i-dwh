import io
import json
import uuid
from io import BytesIO

from django.test import TestCase, Client, override_settings
from django.urls import path
from unittest.mock import patch

from .views import upload_view, presign_view, complete_view, upload_status_view
from .models import Upload, ValidationReport


# Temporary URLConf for these tests (rooted to this test module)
def _urls():
    return [
        path("ingest/upload", upload_view),
        path("ingest/presign", presign_view),
        path("ingest/complete", complete_view),
        path("ingest/uploads/<uuid:upload_id>/status", upload_status_view),
    ]


# This must be module-level so Django can import it when ROOT_URLCONF=__name__
urlpatterns = _urls()


@override_settings(ROOT_URLCONF=__name__)
class IngestionFlowTests(TestCase):
    def setUp(self):
        # Attach a random X-USER-ID header for each test
        self.client = Client(HTTP_X_USER_ID=str(uuid.uuid4()))

    def _csv_file(self, text: str, name: str = "sample.csv"):
        """Helper to generate in-memory CSV file for upload tests"""
        return io.BytesIO(text.encode("utf-8")), name

    def test_upload_missing_file(self):
        resp = self.client.post("/ingest/upload")
        self.assertEqual(resp.status_code, 400)
        self.assertIn("Missing multipart field", resp.json().get("message", ""))

    def test_presign_requires_filename(self):
        resp = self.client.post(
            "/ingest/presign",
            data=json.dumps({"contentLength": 10}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 400)

    def test_models_exist(self):
        # Ensure basic ORM works
        up = Upload.objects.create(
            user_id=uuid.uuid4(), file_name="x.csv", minio_key="k", status="pending"
        )
        ValidationReport.objects.create(upload=up)
        self.assertEqual(Upload.objects.count(), 1)
        self.assertEqual(ValidationReport.objects.count(), 1)

    def test_status_not_found(self):
        resp = self.client.get(f"/ingest/uploads/{uuid.uuid4()}/status")
        self.assertEqual(resp.status_code, 404)

    @patch("e2i_api.apps.ingestion.views.Minio.get_object")
    def test_presign_and_complete_flow(self, mock_get_object):
        """
        End-to-end presign + complete test, mocking MinIO client
        """

        # Mock MinIO to return a CSV file content
        mock_get_object.return_value = BytesIO(b"col1,col2\n1,2\n")

        # Step 1: Presign request (fixed key to fileName)
        resp = self.client.post(
            "/ingest/presign",
            data=json.dumps({"fileName": "test.csv", "contentLength": 12}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200, resp.content)
        presign_data = resp.json()
        upload_id = presign_data["id"]
        self.assertTrue("url" in presign_data)

        # Step 2: Complete request (will call our mocked MinIO)
        resp2 = self.client.post(
            "/ingest/complete",
            data=json.dumps({"id": upload_id}),
            content_type="application/json",
        )
        self.assertEqual(resp2.status_code, 200, resp2.content)
        data2 = resp2.json()
        self.assertEqual(data2["status"], "validated")

        # Step 3: Status request
        resp3 = self.client.get(f"/ingest/uploads/{upload_id}/status")
        self.assertEqual(resp3.status_code, 200)
        self.assertEqual(resp3.json()["status"], "validated")
