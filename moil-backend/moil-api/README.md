# MOIL Mining Intelligence – backend (core)
Docker: cp .env.example .env && docker compose up --build   -> http://localhost:8000/docs
Local:  pip install -r requirements.txt && python -m scripts.seed && uvicorn app.main:app --reload
Tests:  pytest
Demo logins (after seeding): <role>@moil.in e.g. mine_manager@moil.in, password Moil@12345
