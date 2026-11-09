
import requests

from backend.config import (
    PAYPAL_CLIENT_ID,
    PAYPAL_CLIENT_SECRET,
    PAYPAL_BASE_URL
)


def get_access_token():

    if not PAYPAL_CLIENT_ID or not PAYPAL_CLIENT_SECRET:
        raise ValueError("PayPal Sandbox credentials are missing.")

    response = requests.post(
        f"{PAYPAL_BASE_URL}/v1/oauth2/token",
        auth=(PAYPAL_CLIENT_ID, PAYPAL_CLIENT_SECRET),
        data={"grant_type": "client_credentials"},
        headers={"Accept": "application/json"},
        timeout=20
    )

    response.raise_for_status()

    return response.json()["access_token"]


def create_sandbox_order(amount="10.00", currency="USD"):

    token = get_access_token()

    response = requests.post(
        f"{PAYPAL_BASE_URL}/v2/checkout/orders",
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}"
        },
        json={
            "intent": "CAPTURE",
            "purchase_units": [{
            "amount": {
                "currency_code": currency,
                "value": amount
            },
            "description": "PayPal Sentinel Sandbox Test"
        }],
        "application_context": {
            "return_url": "http://localhost:8000/paypal/success",
            "cancel_url": "http://localhost:8000/paypal/cancel"
        }
        },
        timeout=20
    )

    response.raise_for_status()

    return response.json()


def capture_sandbox_order(order_id):

    token = get_access_token()

    response = requests.post(
        f"{PAYPAL_BASE_URL}/v2/checkout/orders/{order_id}/capture",
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}"
        },
        timeout=20
    )

    response.raise_for_status()

    return response.json()
