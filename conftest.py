"""
Shared pytest fixtures.

The app's "database" is just two module-level dictionaries (app.jobs,
app.applications). Without resetting them, a job created in one test
would still be sitting there in the next one — so every test gets a
clean slate via the autouse reset_storage fixture below.
"""

import pytest
from fastapi.testclient import TestClient

import app as app_module


@pytest.fixture(autouse=True)
def reset_storage():
    """Runs before AND after every test, so state never leaks between
    tests regardless of run order."""
    app_module.jobs.clear()
    app_module.applications.clear()
    yield
    app_module.jobs.clear()
    app_module.applications.clear()


@pytest.fixture()
def client() -> TestClient:
    return TestClient(app_module.app)


@pytest.fixture()
def open_job(client: TestClient) -> dict:
    """A ready-made OPEN job for tests that need one to already exist."""
    response = client.post(
        "/jobs",
        json={
            "title": "Backend Engineer",
            "description": "Build and maintain our core APIs.",
            "location": "Remote",
        },
    )
    return response.json()
