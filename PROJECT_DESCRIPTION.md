\# PayPal Sentinel

\## AI-Powered Review Intelligence \& Issue Analysis Platform



\### Overview



PayPal Sentinel is an AI-powered review intelligence platform designed to transform unstructured customer feedback into actionable insights for investigating customer complaints, potential fraud signals, and engineering-related issues.



Payment platforms receive large volumes of customer feedback across app stores and other channels. These reviews often contain valuable information about transaction failures, account access problems, suspicious activity, payment delays, and application performance. However, extracting meaningful patterns and identifying issues across this feedback can be challenging.



PayPal Sentinel addresses this challenge through multi-dimensional review classification, interactive analytics, and a supervisor-based multi-agent AI architecture.



\### The Solution



The platform combines structured review intelligence with specialist AI agents to support systematic investigation of customer-reported problems.



Its capabilities include:



\- \*\*Review Intelligence:\*\* Classifies customer reviews across multiple dimensions, including business context, stakeholder, product module, feature, workflow stage, complaint category, sentiment, and reported symptoms.

\- \*\*Advanced Analytics:\*\* Explores relationships between reported issues, product features, customer sentiment, and business impact through cross-dimensional, temporal, and text analytics.

\- \*\*Complaint Investigation:\*\* Uses a specialist AI agent to investigate customer complaints and their reported impact.

\- \*\*Potential Fraud Signal Analysis:\*\* Examines suspicious patterns and potential fraud-related indicators within customer feedback.

\- \*\*Engineering Issue Analysis:\*\* Investigates technical symptoms, application performance complaints, and reported engineering concerns.

\- \*\*Supervisor-Based AI Orchestration:\*\* Coordinates the specialist agents and consolidates their findings into a unified response.

\- \*\*Review Management API:\*\* Provides REST endpoints for submitting and retrieving customer reviews, backed by SQLite persistence.



\### Multi-Agent AI Architecture



PayPal Sentinel uses four AI agents:



1\. \*\*Complaint Agent:\*\* Analyses customer complaints, reported problems, and their potential business impact.

2\. \*\*Fraud Agent:\*\* Investigates potential fraud-related signals and suspicious patterns mentioned in reviews.

3\. \*\*Engineering Agent:\*\* Examines technical symptoms, application failures, and performance-related complaints.

4\. \*\*Supervisor Agent:\*\* Coordinates specialist agents, routes investigation requests, and combines their findings.



The agents use evidence from available review data. Their findings are intended to support investigation and prioritisation; they do not independently establish fraud, confirm security incidents, or verify engineering root causes.



\### PayPal Developer Platform Integration



PayPal Sentinel includes a working PayPal Sandbox checkout integration using the PayPal REST API.



The integration demonstrates:



\- OAuth 2.0 authentication with PayPal REST API credentials.

\- Sandbox order creation through the PayPal Orders API.

\- Buyer approval through the PayPal-hosted checkout experience.

\- Automatic payment capture following successful buyer approval.

\- A manual capture endpoint for testing and fallback.



The checkout and capture workflow has been successfully tested using separate PayPal Sandbox Business and Personal accounts, with a transaction reaching the `COMPLETED` status.



This is a Sandbox demonstration, not a production payment-processing integration.



\### Technology Stack



\- \*\*Programming:\*\* Python

\- \*\*Dashboard:\*\* Streamlit

\- \*\*Data Processing:\*\* Pandas, NumPy

\- \*\*Visualisation:\*\* Plotly, Matplotlib, WordCloud

\- \*\*AI \& Agent Orchestration:\*\* LangChain, LangGraph

\- \*\*LLM Provider:\*\* Groq

\- \*\*Backend API:\*\* FastAPI, Uvicorn

\- \*\*Database:\*\* SQLite

\- \*\*PayPal Integration:\*\* PayPal REST API, OAuth 2.0, Orders API

\- \*\*Additional Tools:\*\* Scikit-learn, SciPy, BeautifulSoup



\### Project Impact



PayPal Sentinel demonstrates how AI-powered review intelligence can help payment platforms move beyond individual customer complaints towards structured issue investigation.



By connecting customer feedback with product areas, reported symptoms, sentiment, and specialist AI analysis, the platform provides a foundation for:



\- Identifying recurring customer-reported problems.

\- Understanding which product areas attract negative feedback.

\- Exploring potential fraud-related signals for further investigation.

\- Supporting engineering teams with structured issue evidence.

\- Improving visibility into customer experience trends.

\- Organising investigation workflows through specialised AI agents.



\### Repository



\*\*GitHub:\*\* https://github.com/shyammodi11/Paypal-AI-Analytics



\### Project Disclaimer



PayPal Sentinel is an independent hackathon project and is not an official PayPal product or service. PayPal Sandbox transactions are simulated and do not involve real money.

