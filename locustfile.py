
import json
import time
from locust import HttpUser, task, between
import google.auth
import google.auth.transport.requests
from google.oauth2 import id_token

# Load the JSON payload
try:
    with open("test.json", "r") as f:
        payload = json.load(f)
except Exception:
    payload = {"error": "payload load failed"}

class YourIngestUser(HttpUser):
    wait_time = between(0.001, 0.005)
    
    def on_start(self):
        """ Runs once per virtual user when they start """
        self.auth_token = self.get_id_token()
        self.token_expiry = time.time() + 3500 # Tokens usually last 1 hour

    def get_id_token(self):
        """ Fetches a Google ID Token for the Cloud Run URL """
        # The 'audience' must be the base URL of your Cloud Run service
        audience = "https://your-ingest-service-13679166946.europe-west1.run.app"
        auth_req = google.auth.transport.requests.Request()
        return id_token.fetch_id_token(auth_req, audience)

    @task
    def post_golden(self):
        # Refresh token if it's close to expiring
        if time.time() > self.token_expiry:
            self.auth_token = self.get_id_token()
            self.token_expiry = time.time() + 3500

        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {self.auth_token}',
            'User-Agent': 'Locust-CloudRun-Tester'
        }
        
        self.client.post("/", json=payload, headers=headers)
