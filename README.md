# PayPal Sentinel

**AI-Powered Review Intelligence & Issue Analysis Platform**

PayPal Sentinel is an AI-powered platform designed to analyse PayPal app reviews, identify reported issues, understand customer impact, and support structured investigation across complaints, potential fraud signals, and engineering-related problems.

The platform combines multi-dimensional review classification, advanced analytics, and a multi-agent AI system to turn unstructured customer feedback into actionable intelligence.

## Key Features

### 1. Review Intelligence & Classification

- Multi-dimensional classification of customer reviews.
- Identification of business context, stakeholder, business operation, and request intent.
- Analysis of business impact, product modules, product features, and workflow stages.
- Detection of reported symptoms, sentiment, complaint categories, and issue nature.
- Primary and secondary classification insights with confidence information.

### 2. Advanced Analytics

- Review intelligence overview and classification distributions.
- Cross-dimensional analytics to explore relationships between reported issues and product areas.
- Temporal analytics to understand trends over time.
- Text analytics and word-cloud exploration.
- Product feature, workflow, sentiment, and complaint analysis.

### 3. Multi-Agent AI System

PayPal Sentinel uses a supervisor-based architecture with three specialist agents:

- **Complaint Agent:** Investigates customer complaints, reported problems, and their business impact.
- **Fraud Agent:** Analyses potential fraud-related signals and suspicious patterns in customer feedback.
- **Engineering Agent:** Examines technical symptoms, app performance issues, and potential engineering concerns.
- **Supervisor Agent:** Coordinates specialist agents, routes requests, and consolidates their findings into a unified response.

The agents use evidence from available review data and analytics. Potential fraud signals and reported engineering symptoms should be treated as investigation leads, not independently verified findings.

### 4. Review Management API

A FastAPI interface provides endpoints to submit and retrieve reviews.

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/health` | API health check |
| POST | `/reviews` | Submit a review |
| GET | `/reviews` | Retrieve reviews |
| GET | `/reviews/{classification_id}` | Retrieve a specific review |

| POST | `/paypal/create-order` | Create a PayPal Sandbox order |
| GET | `/paypal/success` | Automatically capture an approved payment |
| POST | `/paypal/capture-order/{order_id}` | Manually capture an approved order |

Interactive API documentation is available through Swagger UI at `/docs`.

### 5. Review Database

- SQLite-based review storage.
- Upsert support using `classification_id`.
- Review retrieval and analytics queries.
- Expanded classification data support.

## Technology Stack

- **Language:** Python
- **Dashboard:** Streamlit
- **Data Processing:** Pandas, NumPy
- **Visualisation:** Plotly, Matplotlib, WordCloud
- **AI Frameworks:** LangChain, LangGraph
- **LLM Provider:** Groq
- **API:** FastAPI, Uvicorn
- **Database:** SQLite
- **Utilities:** Scikit-learn, SciPy, BeautifulSoup

## Project Structure

```text
PayPal_Hackathon/
│
├── backend/
│   ├── agents/
│   ├── analytics/
│   ├── database/
│   ├── tools/
│   ├── api.py
│   ├── config.py
│   ├── ingest.py
│   └── llm.py
│
├── dashboard/
│   ├── analytics/
│   └── app.py
│
├── notebooks/
│   └── test.ipynb
│
├── data/
│   ├── raw/
│   └── processed/
│
├── .env.example
├── .gitignore
├── README.md
└── requirements.txt
```

## Installation & Setup

### Prerequisites

- Python 3.10 or later (use a version compatible with the installed dependencies).
- A Groq API key.

### 1. Clone the repository

```bash
git clone https://github.com/shyammodi11/Paypal-AI-Analytics
cd PayPal_Hackathon
```

### 2. Create a virtual environment

```bash
python -m venv venv
```

Activate it on Windows:

```powershell
.\venv\Scripts\Activate.ps1
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment variables

Create your local `.env` file:

```powershell
Copy-Item .env.example .env
```

Add your Groq API key:

GROQ_API_KEY=your_groq_api_key
GROQ_MODEL=openai/gpt-oss-120b

PAYPAL_CLIENT_ID=your_paypal_sandbox_client_id
PAYPAL_CLIENT_SECRET=your_paypal_sandbox_client_secret
PAYPAL_BASE_URL=https://api-m.sandbox.paypal.com

Do not commit `.env` or expose API credentials publicly.

### 5. Configure review datasets

The review datasets and SQLite database are excluded from this repository because of their size.

To reproduce the populated analytics dashboard, obtain the following two datasets separately and place them inside `data/processed/`:

```text
data/
└── processed/
    ├── classified_reviews_stage1.csv
    └── classified_reviews_full.csv
```

Both datasets are required for the complete database setup.

### 6. Initialise the database

First, run the initial ingestion script:

```bash
python -m backend.ingest
```

This script:

- Reads `classified_reviews_stage1.csv`.
- Initialises the SQLite database.
- Inserts or updates the base review records.
- Displays a database summary.

### 7. Migrate expanded classifications

After successful initial ingestion, run:

```bash
python -m backend.database.migrate_expanded_classifications
```

This script:

- Reads `classified_reviews_full.csv`.
- Validates the expanded classification dataset.
- Creates a timestamped backup of the existing database.
- Migrates the expanded classification dimensions into the database.
- Verifies that every review has a corresponding classification record.

**Important:** Run the initial ingestion before the expanded classification migration. The migration expects an existing SQLite database.

## Running the Application

### Streamlit Dashboard

From the project root, run:

```bash
streamlit run dashboard/app.py
```

### FastAPI Service

Open a separate terminal, activate the virtual environment, and run:

```bash
uvicorn backend.api:app --reload
```

Open the API documentation:

- Dashboard: `http://localhost:8501`
- API: `http://127.0.0.1:8000`
- Swagger UI: `http://127.0.0.1:8000/docs`

## API Usage

Example review submission:

```json
{
  "classification_id": "DEMO_001",
  "review_id": "REVIEW_001",
  "review_text": "Unable to transfer money. The payment keeps failing.",
  "rating": 1,
  "platform": "Android",
  "review_date": "2026-11-10",
  "app_version": "8.5.0",
  "complaint_category": "Payments",
  "issue_nature": "Transaction Failure"
}
```

Submit the payload using `POST /reviews`.

The API currently supports review intake and retrieval. It does not automatically trigger AI classification when a review is submitted.

## Real-Time Data Ingestion Through REST API

PayPal Sentinel provides a FastAPI-based REST API that allows external applications, payment platforms, review collection systems, and data pipelines to submit customer reviews directly to its database.

This enables near-real-time review ingestion without manually importing CSV files.

### 1. Start the API Server

Activate the project virtual environment and run:

```bash
uvicorn backend.api:app --reload
```

By default, the API runs at:

```text
http://127.0.0.1:8000
```

Interactive API documentation is available at:

```text
http://127.0.0.1:8000/docs
```

### 2. API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| GET | `/health` | Check API health |
| POST | `/reviews` | Submit a new review |
| GET | `/reviews` | Retrieve stored reviews |
| GET | `/reviews/{classification_id}` | Retrieve a specific review |

### 3. Submit Customer Reviews

**Endpoint:**

```http
POST /reviews
```

**Content-Type:**

```http
application/json
```

Each incoming review must contain two required fields:

- `classification_id`: Unique identifier used to identify and update a review record.
- `review_text`: Original customer review text.

Additional metadata can be supplied to enrich downstream analytics.

**Sample JSON payload:**

```json
{
    "classification_id": "LIVE_REVIEW_001",
    "review_id": "PAYPAL_REVIEW_001",
    "review_text": "My payment was deducted but the recipient has not received the money. The transaction has been pending for several hours.",
    "rating": 1,
    "platform": "Android",
    "review_date": "2026-11-10T10:30:00",
    "app_version": "8.98.1",
    "complaint_category": "payment_issue",
    "issue_nature": "transaction_pending"
}
```

**Field reference:**

| Field | Requirement | Description |
|---|---|---|
| `classification_id` | Required | Unique record identifier |
| `review_text` | Required | Customer review or feedback |
| `review_id` | Optional | Original review identifier |
| `rating` | Optional | Customer rating from 1 to 5 |
| `platform` | Optional | Android, iOS, Web, etc. |
| `review_date` | Optional | Review submission date/time |
| `app_version` | Optional | Application version |
| `complaint_category` | Optional | Complaint category, if available |
| `issue_nature` | Optional | Nature of the reported issue |

### 4. Send Data Using Python

An external application or data collection pipeline can use the `requests` library to submit reviews programmatically.

```python
import requests

API_URL = "http://127.0.0.1:8000/reviews"

review = {
    "classification_id": "LIVE_REVIEW_002",
    "review_id": "PAYPAL_REVIEW_002",
    "review_text": (
        "I cannot log in to my account after "
        "the latest application update."
    ),
    "rating": 1,
    "platform": "Android",
    "review_date": "2026-11-10T11:00:00",
    "app_version": "8.98.1",
    "complaint_category": "login_issue",
    "issue_nature": "authentication_failure"
}

try:
    response = requests.post(
        API_URL,
        json=review,
        timeout=15
    )

    response.raise_for_status()

    print("Review submitted successfully:")
    print(response.json())

except requests.exceptions.RequestException as error:
    print("Review submission failed:", error)
```

For continuous ingestion, the same request can be triggered whenever a new customer review or feedback event is received by the source application.

### 5. Successful API Response

A successful submission returns a JSON response similar to:

```json
{
    "success": true,
    "message": "Review stored successfully.",
    "classification_id": "LIVE_REVIEW_002",
    "records_processed": 1
}
```

The review is persisted in the PayPal Sentinel SQLite database.

**Record handling:** The API uses `classification_id` as the upsert identifier. Submitting another record with the same identifier updates the existing record rather than creating a duplicate.

### 6. Retrieve Stored Reviews

To retrieve reviews already submitted to the database:

```http
GET /reviews
```

Optional query parameter:

```text
?limit=100
```

The API supports a limit between 1 and 1,000 records.

To retrieve a specific review:

```http
GET /reviews/LIVE_REVIEW_002
```

If the requested record does not exist, the API returns HTTP 404.

### 7. Integration With External Systems

The API can be integrated into different data ingestion workflows:

- **Payment platforms:** Submit customer complaints generated after payment failures, refunds, or transaction disputes.
- **Mobile applications:** Forward customer feedback and application-related issue reports.
- **Review collection systems:** Submit newly collected app-store reviews.
- **Webhook integrations:** Trigger API requests whenever a new review event is received.
- **Data pipelines:** Forward processed review records from scheduled or continuously running ETL workflows.

A typical ingestion workflow is:

```text
External Application / Review Source
                 |
                 v
        New Review Event
                 |
                 v
       PayPal Sentinel REST API
                 |
                 v
       Request Validation
                 |
                 v
        SQLite Database
                 |
                 v
       PayPal Sentinel Dashboard
```

### 8. Important Implementation Notes

- The API currently accepts individual review submissions through `POST /reviews`; it does not provide a bulk-upload endpoint.
- Newly submitted records are stored in the database, but automatic AI classification and agent execution are not triggered by the API.
- The dashboard uses cached data with a five-minute cache duration. Newly ingested reviews may therefore take up to five minutes to appear automatically; use the dashboard's refresh option to reload data sooner.
- Use a stable, unique `classification_id` for each review to support reliable updates.
- For continuous integrations, implement retry handling for temporary network failures and server errors.
- The current API does not implement authentication. Do not expose it publicly or send sensitive customer information until appropriate authentication, authorization, HTTPS, and data-protection controls are implemented.

**Note:** PayPal Sentinel's REST API provides the data ingestion and retrieval layer, while its analytics modules and specialist AI agents provide separate review intelligence and investigation capabilities.

## PayPal Sandbox Integration

PayPal Sentinel integrates with the PayPal Developer Platform to demonstrate a working payment checkout and capture workflow using PayPal Sandbox.

### Features

- OAuth 2.0 authentication using PayPal REST API credentials.
- Creation of PayPal Sandbox checkout orders.
- Buyer approval through the PayPal-hosted checkout page.
- Automatic payment capture after successful buyer approval.
- Manual payment capture endpoint for testing and fallback.

### Payment Workflow

```text
PayPal Sentinel API
        |
        v
  OAuth Authentication
        |
        v
  Create Sandbox Order
        |
        v
  PayPal Checkout URL
        |
        v
  Buyer Approval
        |
        v
  /paypal/success
        |
        v
  Automatic Payment Capture
        |
        v
  COMPLETED
```

### PayPal API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| POST | `/paypal/create-order` | Creates a Sandbox payment order |
| GET | `/paypal/success` | Captures the approved order automatically |
| POST | `/paypal/capture-order/{order_id}` | Manually captures an approved order |

### Configuration

Configure the following environment variables in your local `.env` file:

```env
PAYPAL_CLIENT_ID=your_sandbox_client_id
PAYPAL_CLIENT_SECRET=your_sandbox_client_secret
PAYPAL_BASE_URL=https://api-m.sandbox.paypal.com
```

Use credentials from your PayPal Developer Dashboard Sandbox REST API application. Never commit actual credentials to the repository.

### Testing the Checkout Flow

1. Start the FastAPI server:

   ```bash
   uvicorn backend.api:app --reload
   ```

2. Open Swagger UI:

   `http://127.0.0.1:8000/docs`

3. Execute `POST /paypal/create-order`.

4. Open the returned `approval_url` in a browser.

5. Sign in using a PayPal Personal Sandbox buyer account and approve the payment.

6. PayPal redirects the buyer to `/paypal/success`, where the backend automatically captures the approved order.

7. Verify the response contains:

   ```json
   {
       "success": true,
       "message": "PayPal payment completed successfully.",
       "status": "COMPLETED"
   }
   ```

│   ├── paypal_client.py

### Sandbox Testing Notice

This integration uses PayPal Sandbox exclusively. Transactions are simulated and do not involve real money or production PayPal accounts.

Testing requires a Sandbox Business account configured with a REST API application and a separate Sandbox Personal buyer account.

## Data & Security

- Review datasets and local SQLite databases are excluded from the public repository.
- API credentials are managed through environment variables.
- The API currently does not implement authentication; it is intended as a basic development and demonstration interface, not a production-secured public endpoint.
- Do not upload confidential, personally identifiable, or unauthorised customer review data.

## Project Scope

PayPal Sentinel is an independent hackathon project and is not an official PayPal product or service.

Its purpose is to demonstrate how AI agents, structured review classification, and analytics can support customer feedback intelligence and issue investigation.

## Future Enhancements

- Secure API authentication and access control.
- Automated review classification during ingestion.
- Integration with external review sources.
- Enhanced agent evaluation and evidence traceability.
- Deployment as a publicly accessible application.

---

**PayPal Sentinel — Turning customer feedback into actionable intelligence.**