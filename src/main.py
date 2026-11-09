import hashlib
import hmac
import os
from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException, Request, Security, status
from fastapi.security.api_key import APIKeyHeader
from sqlalchemy import text
from sqlalchemy.orm import Session
from src.database import get_db
from src.models import Customer
from src.schemas import CustomerCreate, CustomerOut, CustomerUpdate

app = FastAPI(title="Customer Management API - Combined Project")

# --- WEEK 1 TASK 2: API KEY CONFIGURATION ---
API_KEY_NAME = "X-API-Key"
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False, scheme_name="X-API-Key")

def verify_api_key(api_key: str = Security(api_key_header)):
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API Key missing or invalid",
        )
    return api_key

# --- WEEK 2 TASK 1: WEBHOOK CONFIGURATION ---
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "my_shared_webhook_secret_key").encode('utf-8')

def process_webhook_event(payload_bytes: bytes):
    """Processes the verified event asynchronously in the background thread."""
    print(f"[Background Task] Processing verified event payload: {payload_bytes.decode('utf-8')}")


# --- WEEK 1 TASK 1: DIAGNOSTIC HEALTH ENDPOINT ---
@app.get("/health", status_code=status.HTTP_200_OK)
def health_check(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
        return {"status": "healthy", "database": "connected"}
    except Exception:
        raise HTTPException(status_code=500, detail="Database connection failed")


# --- WEEK 1 TASK 1 & 2: CUSTOMER CRUD ENDPOINTS ---

@app.post("/customers", response_model=CustomerOut, status_code=status.HTTP_201_CREATED, dependencies=[Depends(verify_api_key)])
def create_customer(customer: CustomerCreate, db: Session = Depends(get_db)):
    db_customer = db.query(Customer).filter(Customer.email == customer.email).first()
    if db_customer:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")

    new_customer = Customer(**customer.model_dump())
    db.add(new_customer)
    db.commit()
    db.refresh(new_customer)
    return new_customer

@app.get("/customers", response_model=list[CustomerOut], dependencies=[Depends(verify_api_key)])
def read_customers(page: int = 1, per_page: int = 10, db: Session = Depends(get_db)):
    skip = (page - 1) * per_page
    return db.query(Customer).offset(skip).limit(per_page).all()

@app.get("/customers/{customer_id}", response_model=CustomerOut, dependencies=[Depends(verify_api_key)])
def read_customer(customer_id: int, db: Session = Depends(get_db)):
    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    if not customer:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer not found")
    return customer

@app.put("/customers/{customer_id}", response_model=CustomerOut, dependencies=[Depends(verify_api_key)])
def update_customer(customer_id: int, updated_data: CustomerUpdate, db: Session = Depends(get_db)):
    customer_query = db.query(Customer).filter(Customer.id == customer_id)
    customer = customer_query.first()
    if not customer:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer not found")

    update_dict = updated_data.model_dump(exclude_unset=True)
    if "email" in update_dict and update_dict["email"] != customer.email:
        email_check = db.query(Customer).filter(Customer.email == update_dict["email"]).first()
        if email_check:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already in use")

    customer_query.update(update_dict, synchronize_session=False)
    db.commit()
    db.refresh(customer)
    return customer

@app.delete("/customers/{customer_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(verify_api_key)])
def delete_customer(customer_id: int, db: Session = Depends(get_db)):
    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    if not customer:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer not found")

    db.delete(customer)
    db.commit()
    return None


# --- WEEK 2 DAY 5 TASK 1: NEW WEBHOOK RECEIVER ENDPOINT ---

@app.post("/webhooks/customer-events")
async def receive_customer_webhook(request: Request, background_tasks: BackgroundTasks):
    signature = request.headers.get("X-Signature")
    if not signature:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing signature")
        
    body_bytes = await request.body()
    
    expected_signature = hmac.new(WEBHOOK_SECRET, body_bytes, hashlib.sha256).hexdigest()
    
    if not hmac.compare_digest(expected_signature, signature):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid signature")
        
    background_tasks.add_task(process_webhook_event, body_bytes)
    return {"status": "accepted"}
