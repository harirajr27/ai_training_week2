import json
import threading
import time
import urllib.error
import urllib.request
from uvicorn import Config, Server

# Explicitly use a dedicated port for the testing cycle to avoid any socket conflicts
PORT = 8002
BASE_URL = f"http://127.0.0.1:{PORT}"


def start_test_server():
    """Import and run the FastAPI app programmatically on a separate thread."""
    from src.main import app

    config = Config(app=app, host="127.0.0.1", port=PORT, log_level="warning")
    server = Server(config=config)
    server.run()


def run_tests():
    # 1. POST /customers -> 201
    try:
        url = f"{BASE_URL}/customers"
        payload = json.dumps(
            {
                "name": "Automated Tester",
                "email": f"tester_{int(time.time())}@example.com",
                "phone": "9999999999",
                "city": "Cyber City",
            }
        ).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=payload,
            headers={"X-API-Key": "valid_key", "Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req) as response:
            print(f"POST /customers -> {response.status}")
    except Exception as e:
        print(f"POST /customers -> Failed: {e}")

    # 2. GET /customers?page=1&per_page=10 -> 200
    try:
        url = f"{BASE_URL}/customers?page=1&per_page=10"
        req = urllib.request.Request(url, headers={"X-API-Key": "valid_key"})
        with urllib.request.urlopen(req) as response:
            print(f"GET /customers?page=1&per_page=10 -> {response.status}")
    except Exception as e:
        print(f"GET /customers?page=1&per_page=10 -> Failed: {e}")

    # 3. GET /customers/999 -> 404
    try:
        url = f"{BASE_URL}/customers/999"
        req = urllib.request.Request(url, headers={"X-API-Key": "valid_key"})
        with urllib.request.urlopen(req) as response:
            print(f"GET /customers/999 -> {response.status}")
    except urllib.error.HTTPError as e:
        print(f"GET /customers/999 -> {e.code}")

    # 4. No API key -> 401
    try:
        url = f"{BASE_URL}/customers"
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req) as response:
            print(f"No API key -> {response.status}")
    except urllib.error.HTTPError as e:
        print(f"No API key -> {e.code}")


if __name__ == "__main__":
    # Start the application server locally in a background worker thread
    server_thread = threading.Thread(target=start_test_server, daemon=True)
    server_thread.start()

    # Give the backend engine a small moment to initialize and bind to the port
    time.sleep(1.5)

    # Execute the requested test routing sequence
    run_tests()
