import pytest
from pathlib import Path
import httpx
import os
from httpx import AsyncClient, ASGITransport

import main as app_module

app = app_module.app


@pytest.mark.asyncio
async def test_validate_creates_and_finds_employee(tmp_path: Path):
    test_db_url = f"sqlite:///{tmp_path / 'test.db'}"
    from sqlmodel import create_engine, SQLModel

    test_engine = create_engine(test_db_url, echo=False)
    SQLModel.metadata.create_all(test_engine)

    app_module.engine = test_engine

    # Get the API key from the environment, or use the default one
    api_key = os.getenv("EMPLOYEE_API_KEY", "AgentAppWorks123@")
    headers = {"x-api-key": api_key}

    payload = {
        "payload": {
            "employee_id": "unit123",
            "first_name": "Unit",
            "last_name": "Tester",
            "email": "unit@test.com",
            "date_of_birth": "1990-01-01",
            "hire_date": "2020-01-01",
            "department": "ENGINEERING",
            "employment_type": "FULL_TIME",
        }
    }

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # First call -> employee is created
        resp1 = await client.post("/validate", json=payload, headers=headers)
        assert resp1.status_code == 200
        assert "created" in resp1.json()["agent_response"].lower()

        # Second call -> employee already exists
        resp2 = await client.post("/validate", json=payload, headers=headers)
        assert resp2.status_code == 200
        assert "up to date" in resp2.json()["agent_response"].lower()