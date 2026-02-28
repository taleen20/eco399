import time
import os
from locust import HttpUser, task, between, events


TEST_PDF = os.path.join(os.path.dirname(__file__), "test_data", "test.pdf")


class UploadUser(HttpUser):
    """
    Simulates a user who uploads a PDF, polls until processing completes,
    then downloads the resulting CSV.
    """
    wait_time = between(1, 3)

    @task(1)
    def health_check(self):
        self.client.get("/health", name="/health")

    @task(5)
    def full_upload_flow(self):
        # 1. Upload the PDF
        with open(TEST_PDF, "rb") as f:
            response = self.client.post(
                "/upload",
                files={"file": ("test.pdf", f, "application/pdf")},
                data={"language": "en"},
                name="/upload",
            )

        if response.status_code != 202:
            return

        job_id = response.json().get("job_id")
        if not job_id:
            return

        # 2. Poll /status until done (max 120s)
        deadline = time.time() + 120
        while time.time() < deadline:
            status_resp = self.client.get(
                f"/status/{job_id}",
                name="/status/[job_id]",
            )
            if status_resp.status_code != 200:
                break

            state = status_resp.json().get("state")
            if state == "success":
                filename = status_resp.json().get("filename")
                if filename:
                    self.client.get(
                        f"/download/{filename}",
                        name="/download/[filename]",
                    )
                break
            elif state == "failure":
                # Mark the upload as a failure in locust stats
                self.client.post(
                    "/upload",
                    name="/upload [task-failed]",
                    catch_response=True,
                )
                break

            time.sleep(2)
