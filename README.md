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

```env
GROQ_API_KEY=your_groq_api_key
GROQ_MODEL=openai/gpt-oss-120b
```

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