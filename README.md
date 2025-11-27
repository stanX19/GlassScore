# GlassScore

[Repo Link Placeholder]

## Solution Overview

**Problem:** Traditional credit scoring systems are often "black boxes," relying solely on rigid financial history and failing to capture the full picture of an applicant's trustworthiness. They struggle with thin-file applicants and lack transparency.

**Target User:** Financial institutions, loan officers, and credit analysts seeking a more holistic and explainable risk assessment tool.

**Fix:** GlassScore is an advanced, multi-modal credit scoring platform that combines traditional Machine Learning with Large Language Models (LLMs) and real-time Web Search. It provides a transparent, explainable, and comprehensive credit score by analyzing structured data, personal statements, and external digital footprints.

## Demo Video

[Watch on YouTube](https://youtu.be/j1ak08jdrBQ)

## Slides

[GlassScore Presentation (PDF)](assets/GlassScore%20Presentation.pdf) | [View on Canva](https://www.canva.com/design/DAG55fYZJBw/RUf1vQOBvf8XYlziJRxWIA/edit?utm_content=DAG55fYZJBw&utm_campaign=designshare&utm_medium=link2&utm_source=sharebutton)

## Getting Started

### Prerequisites
*   Python 3.10+
*   Node.js 18+
*   API Keys for OpenAI/Google Gemini and Tavily.

### Installation

1.  Clone the repository:
    ```bash
    git clone https://github.com/stanx19/GlassScore.git
    ```
2.  Navigate to the root directory:
    ```bash
    cd GlassScore
    ```

### Backend Setup
1.  Navigate to the backend directory:
    ```bash
    cd backend
    ```
2.  Create and activate a virtual environment:
    ```bash
    python -m venv venv
	```
    Windows
    ```bash
    .\venv\Scripts\activate
	```
    Linux/Mac
    ```bash
    source venv/bin/activate
	```
3.  Install dependencies:
    ```bash
    pip install -r requirements.txt
    ```
4.  Set up environment variables:
    ```bash
    cp .env.example .env
    ```
	Remember to fill in the API keys for OpenAI/Google Gemini and Tavily accordingly.


5.  Run the server:
    ```bash
    uvicorn main:app --reload
    ```

### Frontend Setup
1.  Navigate to the frontend directory:
    ```bash
    cd frontend/GlassScore
    ```
2.  Install dependencies:
    ```bash
    npm install
    ```
3.  Start the development server:
    ```bash
    npm run dev
    ```

## Tech Stack

*   **Frontend:** React, TypeScript, Vite, Axios, Tailwind CSS.
*   **Backend:** Python, FastAPI, Uvicorn.
*   **AI & ML:** LangChain, OpenAI GPT-4 / Google Gemini, Scikit-learn, SHAP, Tavily Search API.
*   **Database:** PostgreSQL (Production) / In-Memory (Dev).

## System Architecture

GlassScore operates on a modern client-server architecture:

![System Architecture](assets/system_architecture.png)

**Data Flow:**
1.  **Input:** User submits loan application data (structured) and supporting documents/statements (unstructured).
2.  **Processing:**
    *   **ML Engine:** Predicts default risk using historical loan data.
    *   **LLM Engine:** Analyzes text for behavioral risk markers (e.g., gambling references, inconsistencies).
    *   **Web Engine:** Verifies claims against live web data (e.g., employment verification).
3.  **Output:** Real-time stream of "Evidence" points (Positive/Negative) that dynamically adjust the GlassScore.

## Key Features

*   **Multi-Modal Evaluation:** Seamlessly integrates structured financial data (Random Forest Model), unstructured text analysis (LLM), and real-time web verification.
*   **Pipeline:** Automated preprocessing pipeline including median imputation for numerical values and one-hot encoding for categorical variables.
*   **Real-Time Streaming:** Results are pushed to the frontend instantly as they are processed, providing immediate feedback.
*   **Explainable AI (XAI):** Every score adjustment is backed by specific evidence, citations, and reasoning.
*   **Interactive Dashboard:** A modern, responsive UI that visualizes the scoring process and allows deep dives into specific risk factors.
*   **Dynamic Risk Assessment:** Adapts to new information found during the web search and text analysis phases.

## Machine Learning Model

GlassScore employs a robust **Random Forest Classifier** to predict loan default risk based on historical data.

*   **Algorithm:** Random Forest Classifier (Scikit-learn).
*   **Training:** Optimized using `RandomizedSearchCV` with 3-fold cross-validation for hyperparameter tuning.
*   **Features:**
    *   **Numerical:** Age, Income, Employment Length, Loan Amount, Interest Rate, Loan/Income Ratio, Credit History Length.
    *   **Categorical:** Home Ownership, Loan Intent, Loan Grade, Default History.
*   **Explainability:** Integrated **SHAP (SHapley Additive exPlanations)** values to provide local interpretability, explaining exactly *why* a specific applicant received a certain risk score (e.g., "High Loan Amount" or "Low Income").

## Innovation & Differentiation

*   **Beyond the FICO Score:** Moves beyond simple number crunching to understand the *context* of a borrower.
*   **Agentic Verification:** Uses autonomous agents to verify user claims on the web, reducing fraud risk.
*   **Transparent Decisioning:** Unlike traditional models, GlassScore tells you *why* a decision was made.
