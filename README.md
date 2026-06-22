# HR Agentic Portal

A conversational HR management system that allows administrators to manage employee records using natural language.

## Features
- **Agentic Workflow:** Uses an AI agent to reason and execute database operations (CRUD) based on user intent.
- **Hybrid Interface:** Combines a structured Pydantic-validated form for onboarding and a conversational chat interface for quick updates and queries.
- **Tool-Calling Logic:** The agent autonomously decides when to search, fetch, create, update, or delete records.
- **Data Validation:** Strict type-checking and cross-field validation (e.g., ensuring hire date is after birth date) using Pydantic.

## Tech Stack
- **Backend:** FastAPI, SQLModel (SQLite)
- **Frontend:** Streamlit
- **AI Orchestration:** Portkey AI / LLM Tool Calling
- **Validation:** Pydantic V2

## Installation & Setup

1. **Clone the repository**
    git clone <your-repo-url>
    cd EMPLOYEE_AGENT_APP

2. **Set up a virtual environment**
    python -m venv .venv
    source .venv/bin/activate  # On Windows: .venv\Scripts\activate

3. **Install dependencies**
    pip install -r requirements.txt

4. **Environment Variables**
    Create a `.env` file in the root directory and add your keys:
    EMPLOYEE_API_KEY=your_api_key_here
    PORTKEY_API_KEY=your_portkey_key_here

## How to Run

1. **Start the Backend API:**
    python main.py

2. **Start the Frontend UI:**
    streamlit run ui.py

## Testing
Run the unit tests to verify the validation logic:
    pytest tests/test_validate.py