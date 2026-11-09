
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import Optional
import pandas as pd

from backend.database.db import (
    initialize_database,
    upsert_reviews,
    get_all_reviews,
    get_review_by_id
)
from backend.paypal_client import create_sandbox_order, capture_sandbox_order

app = FastAPI(
    title="PayPal Sentinel API",
    description="API for submitting and retrieving PayPal app reviews.",
    version="1.0.0"
)


# ============================================================
# INITIALISE DATABASE
# ============================================================

@app.on_event("startup")
def startup():
    initialize_database()


# ============================================================
# REVIEW REQUEST MODEL
# ============================================================

class ReviewRequest(BaseModel):

    classification_id: str = Field(..., min_length=1)
    review_id: Optional[str] = None
    review_text: str = Field(..., min_length=1)
    rating: Optional[int] = Field(None, ge=1, le=5)
    platform: Optional[str] = None
    review_date: Optional[str] = None
    app_version: Optional[str] = None
    complaint_category: Optional[str] = None
    issue_nature: Optional[str] = None


# ============================================================
# HEALTH CHECK
# ============================================================

@app.get("/health")
def health_check():

    return {
        "status": "healthy",
        "application": "PayPal Sentinel API"
    }

# ============================================================
# PAYPAL SANDBOX ORDER
# ============================================================

@app.post("/paypal/create-order")
def create_paypal_order():

    try:
        order = create_sandbox_order()

        return {
            "success": True,
            "paypal_order_id": order["id"],
            "status": order["status"],
            "approval_url": next(
                (
                    link["href"]
                    for link in order.get("links", [])
                    if link["rel"] == "approve"
                ),
                None
            )
        }

    except Exception as e:
        raise HTTPException(
            status_code=502,
            detail=f"PayPal integration failed: {str(e)}"
        )

@app.post("/paypal/capture-order/{order_id}")
def capture_paypal_order(order_id: str):

    try:
        result = capture_sandbox_order(order_id)

        captures = (
            result.get("purchase_units", [{}])[0]
            .get("payments", {})
            .get("captures", [])
        )

        return {
            "success": True,
            "paypal_order_id": result.get("id"),
            "status": result.get("status"),
            "capture_id": captures[0].get("id") if captures else None
        }

    except Exception as e:
        raise HTTPException(
            status_code=502,
            detail=f"PayPal capture failed: {str(e)}"
        )

@app.get("/paypal/success")
def paypal_success(token: str):

    try:
        result = capture_sandbox_order(token)

        captures = (
            result.get("purchase_units", [{}])[0]
            .get("payments", {})
            .get("captures", [])
        )

        return {
            "success": True,
            "message": "PayPal payment completed successfully.",
            "paypal_order_id": result.get("id"),
            "status": result.get("status"),
            "capture_id": captures[0].get("id") if captures else None
        }

    except Exception as e:
        raise HTTPException(
            status_code=502,
            detail=f"PayPal payment capture failed: {str(e)}"
        )

# ============================================================
# SUBMIT REVIEW
# ============================================================

@app.post("/reviews")
def submit_review(review: ReviewRequest):

    try:

        review_data = review.model_dump()

        df = pd.DataFrame([{
            "classification_id": review_data["classification_id"],
            "review_id": review_data["review_id"],
            "review_text": review_data["review_text"],
            "review_rating": review_data["rating"],
            "android_or_ios": review_data["platform"],
            "review_timestamp": review_data["review_date"],
            "reviewCreatedVersion": review_data["app_version"],
            "complaint_category_primary": review_data["complaint_category"],
            "issue_nature_primary": review_data["issue_nature"]
        }])

        processed = upsert_reviews(df)

        return {
            "success": True,
            "message": "Review stored successfully.",
            "classification_id": review_data["classification_id"],
            "records_processed": processed
        }

    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


# ============================================================
# RETRIEVE ALL REVIEWS
# ============================================================

@app.get("/reviews")
def retrieve_reviews(limit: int = 100):

    if limit < 1 or limit > 1000:
        raise HTTPException(
            status_code=400,
            detail="Limit must be between 1 and 1000."
        )

    df = get_all_reviews(limit=limit)

    return {
        "total_returned": len(df),
        "reviews": df.astype(object).where(pd.notna(df), None).to_dict(orient="records")
    }

# ============================================================
# RETRIEVE ONE REVIEW
# ============================================================

@app.get("/reviews/{classification_id}")
def retrieve_review(classification_id: str):

    review = get_review_by_id(classification_id)

    if review is None:
        raise HTTPException(
            status_code=404,
            detail="Review not found."
        )

    return review
