# AI Credit Underwriting Engine 🏦

An intelligent, multi-agent credit risk assessment system built with [LangGraph](https://langchain-ai.github.io/langgraph/) and [FastMCP](https://github.com/jlowin/fastmcp). This application orchestrates multiple specialized AI agents to evaluate credit applications, assess various risk factors, and make explainable credit decisions.

## 🚀 Overview

The **AI Credit Underwriting Engine** automates the complex process of credit underwriting. It ingests applicant data and processes it through a graph of specialized nodes, each responsible for a specific aspect of risk analysis. The system provides a transparent, auditable decision-making process with detailed explanations and simplified user interaction via a Streamlit interface.

## ✨ Key Features

-   **Multi-Agent Architecture**: Uses distinct agents for creditworthiness, fraud detection, income stability, and macroeconomic risk.
-   **Orchestrated Workflow**: Powered by **LangGraph** to manage the state and dependencies between different analysis stages.
-   **Tool Integration via MCP**: Utilizes the **Model Context Protocol (MCP)** to modularize functionality into separate servers.
-   **Interactive UI**: A user-friendly web interface built with **Streamlit** for submitting applications and viewing results.
-   **Explainable AI**: Provides detailed explanations for every credit decision, ensuring transparency.
-   **Automated Auditing**: Includes a dedicated audit step to verify the decision logic.
-   **Dynamic Offers**: Generates tailored credit offers for approved applicants.
-   **User Authentication**: Secure signup and login functionality.

## 🏗️ Architecture

The system is composed of a frontend application and a backend workflow graph.

### 1. Frontend (`app.py`)
-   Built with Streamlit.
-   Handles user authentication (Login/Signup).
-   Collects applicant details (Name, Age, Income, Debt, etc.).
-   Visualizes the decision, risk scores, and offers.

### 2. Backend Graph (`graph.py`)
The core logic is a state machine defined using LangGraph. It coordinates the following MCP servers:
-   **Credit Application Intake**: Normalizes and structures input data.
-   **Creditworthiness Scoring**: Estimates a credit score/risk level.
-   **Fraud Risk Evaluation**: Checks for potential fraud indicators.
-   **Macroeconomic Risk Evaluation**: Considers broader market conditions.
-   **Income Stability Evaluation**: Analyzes employment and income history.
-   **Credit Decision Engine**: Aggregates all scores to make a final APPROVE/REJECT decision.
-   **Credit Decision Explanation**: Generates a natural language explanation for the decision.
-   **Credit Decision Audit**: Reviews the decision for compliance and logic.
-   **Credit Offer**: (Conditional) Generates loan terms if the application is approved.

### 3. MCP Servers (Tools)
Each specific task is handled by a standalone Python script acting as an MCP server:
-   `credit_application_intake_server.py`
-   `creditworthiness_scoring_server.py`
-   `fraud_risk_server.py`
-   `income_stability_server.py`
-   `macroeconomic_risk_server.py`
-   `credit_decision_engine_server.py`
-   `credit_decision_explanation_server.py`
-   `credit_decision_audit_server.py`
-   `credit_offer_server.py`

## 🛠️ Installation

1.  **Clone the repository**:
    ```bash
    git clone <repository-url>
    cd <repository-directory>
    ```

2.  **Install Dependencies**:
    Ensure you have Python installed. It is recommended to use a virtual environment.
    ```bash
    pip install -r requirements.txt
    ```

3.  **Environment Setup**:
    Ensure you have the necessary API keys (e.g., OpenAI API Key) set in your environment or a `.env` file, as the MCP servers likely rely on an LLM for reasoning.

## 🏃 Usage

1.  **Start the Application**:
    Run the Streamlit app:
    ```bash
    streamlit run app.py
    ```

2.  **Access the UI**:
    Open your browser and navigate to the URL provided (usually `http://localhost:8501`).

3.  **Login/Signup**:
    -   Create a new account or log in with existing credentials.
    -   Default users are stored in `users.yaml` (if pre-configured).

4.  **Submit an Application**:
    -   Fill out the credit application form with the applicant's financial details.
    -   Click **Submit** to trigger the underwriting workflow.

5.  **View Results**:
    -   See the final Decision (Approved/Rejected).
    -   Review individual risk scores (Fraud, Income, Macro).
    -   Read the detailed explanation.
    -   If approved, view the generated Credit Offer.

## 📂 File Structure

-   **`app.py`**: Main entry point for the Streamlit web application.
-   **`graph.py`**: Defines the LangGraph workflow and edges.
-   **`state.py`**: Defines the Pydantic models for the application state (`ApplicantState`, `CreditState`).
-   **`auth_utils.py`**: Helper functions for user authentication.
-   **`*_server.py`**: Individual MCP server implementations for each step of the workflow.
-   **`requirements.txt`**: List of Python project dependencies.
