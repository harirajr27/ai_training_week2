# Customer Management API — Integration Tests & Demo

This repository contains the complete implementation and comprehensive testing suite for the Customer Management API.

## 🚀 Implemented Concepts & Requirements

### 1. Automated Integration Testing (`pytest`)
* **Framework:** Built using `pytest` and FastAPI's `TestClient` to test structural API routing integration.
* **Isolated Environment:** Configured a **Separate Test Database** using a transient SQLite instance (`test.db`) to ensure tests do not alter production tables.
* **Endpoint Coverage:** 
  * **Happy Paths:** Valid customer creations (201) and paginated list fetches (200).
  * **Error Boundaries:** Explicitly handled validation boundaries covering **401 Unauthorized** (missing API keys), **404 Not Found** (unknown customer IDs), **409 Conflict** (duplicate emails), and **422 Unprocessable Entity** (invalid email payload schemas).

### 2. Webhook Verification Architecture
* Covered full security lifecycle tracking for the HMAC-SHA256 Webhook verification scheme:
  * **Valid Signatures:** Asserts processing acceptance state (200).
  * **Tampered Signatures:** Confirms blocking behavior for modified payloads (401).
  * **Missing Signatures:** Catching payload delivery failures when header signatures are omitted (401).

### 3. Execution & Coverage Reporting (`pytest-cov`)
* Enforced strict testing verification matrix targeting `src/` modules.
* **Test Report Summary:** All 9 execution scenario test fixtures pass smoothly with 0 error collection failures.

---

## 🛠️ How to Set Up & Run the Project

### 1. Environment Setup
Activate your isolated environment and install requirements:
```powershell
.\venv\Scripts\Activate.ps1
pip install -r pyproject.toml
```

### 2. Run Integration Tests & View Coverage Metrics
Execute the automated test client suite to view the coverage table report:
```powershell
python -m pytest --cov=src
```

### 3. Launch Local Live Server
Spin up the backend framework server to view the interactive documentation:
```powershell
python -m uvicorn main:app --reload --app-dir src
```
*Interactive panel available at:* `http://127.0.0`
