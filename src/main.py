from fastapi import Depends, FastAPI, HTTPException, Security, status
from fastapi.security.api_key import APIKeyHeader
from sqlalchemy import text
from sqlalchemy.orm import Session
from src.database import get_db
from src.models import Customer
from src.schemas import CustomerCreate, CustomerOut, CustomerUpdate

app = FastAPI(title="Customer Management API - Task 2")

# API Key header requirement (Matches "No API key -> 401")
API_KEY_NAME = "X-API-Key"
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)


def verify_api_key(api_key: str = Security(api_key_header)):
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API Key missing or invalid",
        )
    return api_key


# --- HEALTH ENDPOINT ---
@app.get("/health", status_code=status.HTTP_200_OK)
def health_check(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
        return {"status": "healthy", "database": "connected"}
    except Exception:
        raise HTTPException(status_code=500, detail="Database connection failed")


# --- CRUD ENDPOINTS PROTECTED WITH API KEY ---


@app.post(
    "/customers",
    response_model=CustomerOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(verify_api_key)],
)
def create_customer(customer: CustomerCreate, db: Session = Depends(get_db)):
    db_customer = (
        db.query(Customer).filter(Customer.email == customer.email).first()
    )

    # CRITICAL FIX: Returns 409 Conflict instead of 400 for duplicate emails
    if db_customer:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        )

    new_customer = Customer(**customer.model_dump())
    db.add(new_customer)
    db.commit()
    db.refresh(new_customer)
    return new_customer


# Matches "GET /customers?page=1&per_page=10 -> 200"
@app.get(
    "/customers",
    response_model=list[CustomerOut],
    dependencies=[Depends(verify_api_key)],
)
def read_customers(
    page: int = 1, per_page: int = 10, db: Session = Depends(get_db)
):
    skip = (page - 1) * per_page
    return db.query(Customer).offset(skip).limit(per_page).all()


# Matches "GET /customers/999 -> 404"
@app.get(
    "/customers/{customer_id}",
    response_model=CustomerOut,
    dependencies=[Depends(verify_api_key)],
)
def read_customer(customer_id: int, db: Session = Depends(get_db)):
    customer = db.query(Customer).filter(Customer.id == customer_id).first()

    # Returns 404 for unknown ids
    if not customer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Customer not found",
        )
    return customer


@app.put(
    "/customers/{customer_id}",
    response_model=CustomerOut,
    dependencies=[Depends(verify_api_key)],
)
def update_customer(
    customer_id: int, updated_data: CustomerUpdate, db: Session = Depends(get_db)
):
    customer_query = db.query(Customer).filter(Customer.id == customer_id)
    customer = customer_query.first()
    if not customer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Customer not found",
        )

    update_dict = updated_data.model_dump(exclude_unset=True)
    if "email" in update_dict and update_dict["email"] != customer.email:
        email_check = (
            db.query(Customer).filter(Customer.email == update_dict["email"]).first()
        )
        if email_check:
            # Returns 409 Conflict if updating email to one that already exists
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email already in use",
            )

    customer_query.update(update_dict, synchronize_session=False)
    db.commit()
    db.refresh(customer)
    return customer


@app.delete(
    "/customers/{customer_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(verify_api_key)],
)
def delete_customer(customer_id: int, db: Session = Depends(get_db)):
    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    if not customer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Customer not found",
        )

    db.delete(customer)
    db.commit()
    return None
