# AgentShield Backend

Modular FastAPI backend for AgentShield.

## Tech Stack
- Python 3.11+
- FastAPI
- Pydantic
- SQLAlchemy
- Pandas, NumPy, Scikit-learn, XGBoost, Joblib

## Directory Structure
- `app/`: FastAPI app, database models, policies, agent structures, ML scripts, and schemas.
- `tests/`: Automated backend checks and endpoint testing.

## Local Execution
1. Create and activate a Python virtual environment:
   ```bash
   python -m venv .venv
   .venv\Scripts\activate # On Windows
   ```
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Run the development server:
   ```bash
   uvicorn app.main:app --reload
   ```
4. Check the API docs at `http://127.0.0.1:8000/docs` or `http://127.0.0.1:8000/redoc`.
