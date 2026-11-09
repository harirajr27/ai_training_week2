import hmac
import hashlib
import json
import time
import threading
import urllib.request
import urllib.error
from uvicorn import Config, Server

# Explicitly use a dedicated test port to avoid socket clashes
PORT = 8005
URL = f"http://127.0.0.1:{PORT}/webhooks/customer-events"
SECRET = b"my_shared_webhook_secret_key"
payload = json.dumps({"event": "customer.created", "id": 123})
payload_bytes = payload.encode('utf-8')

def start_test_server():
    """Starts the actual combined FastAPI application framework in a background worker."""
    from src.main import app
    config = Config(app=app, host="127.0.0.1", port=PORT, log_level="warning")
    server = Server(config=config)
    server.run()

def send_request(data_bytes, headers):
    req = urllib.request.Request(URL, data=data_bytes, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req) as response:
            return response.status, response.read().decode('utf-8')
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode('utf-8')

def run_tests():
    print("--- Running Webhook Verification Tests ---")

    # 1. Test Valid Signature
    valid_sig = hmac.new(SECRET, payload_bytes, hashlib.sha256).hexdigest()
    status_valid, res_valid = send_request(payload_bytes, {"X-Signature": valid_sig, "Content-Type": "application/json"})
    print(f"Valid signature    -> {status_valid} {res_valid.strip()}")

    # 2. Test Tampered Payload
    tampered_payload = payload + "tampered_modification"
    status_tampered, res_tampered = send_request(tampered_payload.encode('utf-8'), {"X-Signature": valid_sig, "Content-Type": "application/json"})
    print(f"Tampered payload   -> {status_tampered} {res_tampered.strip()}")

    # 3. Test Missing Signature
    status_missing, res_missing = send_request(payload_bytes, {"Content-Type": "application/json"})
    print(f"Missing signature  -> {status_missing} {res_missing.strip()}")

if __name__ == "__main__":
    # Spin up the app inside the same script session
    server_thread = threading.Thread(target=start_test_server, daemon=True)
    server_thread.start()
    
    # Give the backend engine a brief moment to map the ports cleanly
    time.sleep(1.5)

    # Fire off requests
    run_tests()
