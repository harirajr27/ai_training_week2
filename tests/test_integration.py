import hashlib
import hmac
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.database import Base, get_db
from src.main import app

# --- 1. SETUP SEPARATE TEST DATABASE ---
TEST_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Clean and rebuild the test database tables before running tests
Base.metadata.drop_all(bind=engine)
Base.metadata.create_all(bind=engine)

# Dependency override fixture
def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)

API_KEY_HEADERS = {"X-API-Key": "test_secret_key"}
WEBHOOK_SECRET = b"my_shared_webhook_secret_key"


# --- 2. SECURITY TEST CASES (401 CASES) ---

def test_crud_endpoints_unauthorized_401():
    # Attempting to fetch customers without API Key header
    response = client.get("/customers")
    assert response.status_code == 401
    assert response.json()["detail"] == "API Key missing or invalid"


# --- 3. CUSTOMER CRUD TESTS (HAPPY PATHS & ERROR BOUNDARIES) ---

def test_create_customer_happy_path_201():
    payload = {
        "name": "Jane Doe",
        "email": "jane.doe@example.com",
        "phone": "1234567890",
        "city": "Boston"
    }
    response = client.post("/customers", json=payload, headers=API_KEY_HEADERS)
    assert response.status_code == 201
    assert response.json()["name"] == "Jane Doe"
    assert "id" in response.json()

def test_create_customer_duplicate_email_409():
    payload = {
        "name": "Duplicate User",
        "email": "jane.doe@example.com", # Already created in test above
        "phone": "0000000000",
        "city": "Boston"
    }
    response = client.post("/customers", json=payload, headers=API_KEY_HEADERS)
    assert response.status_code == 409
    assert response.json()["detail"] == "Email already registered"

def test_create_customer_validation_error_422():
    payload = {
        "name": "Bad Email User",
        "email": "not-an-email-address", # Invalid email syntax
    }
    response = client.post("/customers", json=payload, headers=API_KEY_HEADERS)
    assert response.status_code == 422


def test_read_customers_pagination_200():
    response = client.get("/customers?page=1&per_page=5", headers=API_KEY_HEADERS)
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_read_customer_by_id_404():
    response = client.get("/customers/999", headers=API_KEY_HEADERS)
    assert response.status_code == 404
    assert response.json()["detail"] == "Customer not found"


# --- 4. WEBHOOK EVENT TEST CASES (VALID, TAMPERED, MISSING) ---

def test_webhook_valid_signature_200():
    payload = {"event": "customer.tier_upgraded", "id": 1}
    body_bytes = bytes(str(payload).replace(" ", ""), 'utf-8')
    
    valid_signature = hmac.new(WEBHOOK_SECRET, body_bytes, hashlib.sha256).hexdigest()
    
    response = client.post(
        "/webhooks/customer-events",
        content=body_bytes,
        headers={"X-Signature": valid_signature, "Content-Type": "application/json"}
    )
    assert response.status_code == 200
    assert response.json() == {"status": "accepted"}

def test_webhook_tampered_signature_401():
    payload = {"event": "customer.tier_upgraded", "id": 1}
    body_bytes = bytes(str(payload).replace(" ", ""), 'utf-8')
    
    response = client.post(
        "/webhooks/customer-events",
        content=body_bytes,
        headers={"X-Signature": "completely_fake_signature_hash", "Content-Type": "application/json"}
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid signature"

def test_webhook_missing_signature_401():
    payload = {"event": "customer.tier_upgraded", "id": 1}
    response = client.post("/webhooks/customer-events", json=payload)
    assert response.status_code == 401
    assert response.json()["detail"] == "Missing signature"
