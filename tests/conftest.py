# /tests/conftest.py
import pytest
import httpx

BACKEND = "http://localhost:8000"
CHANNELS = "http://localhost:8001"


@pytest.fixture(scope="session")
def backend():
    return BACKEND


@pytest.fixture(scope="session")
def channels():
    return CHANNELS


@pytest.fixture(scope="session")
def client():
    return httpx.Client(timeout=10)
