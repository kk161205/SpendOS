"""
API endpoint tests using pytest + httpx.
Tests health, auth, and procurement endpoints.
"""

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from unittest.mock import AsyncMock
import time

from app.main import app


# ── Health Check ───────────────────────────────────────────────────────────────

class TestHealth:
    @pytest.mark.asyncio(scope="session")
    async def test_health_endpoint_returns_200(self, client):
        # Mock the ARQ pool that the health check uses
        mock_pool = AsyncMock()
        mock_pool.all_job_definitions = AsyncMock(return_value=[])
        app.state.arq_pool = mock_pool
        
        resp = await client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        # Accept "ok" or "degraded" (DB may not exist in test env)
        assert data["status"] in ("ok", "degraded")

    @pytest.mark.asyncio(scope="session")
    async def test_root_returns_service_info(self, client):
        resp = await client.get("/")
        assert resp.status_code == 200
        assert "message" in resp.json()


# ── Auth ───────────────────────────────────────────────────────────────────────

class TestAuth:
    @pytest.mark.asyncio(scope="session")
    async def test_register_new_user(self, client):
        timestamp = int(time.time() * 1000)
        resp = await client.post("/api/auth/register", json={
            "email": f"new{timestamp}@example.com",
            "password": "StrongP@ss123",
            "full_name": "New User",
        })
        assert resp.status_code == 201
        assert "user_id" in resp.json()

    @pytest.mark.asyncio(scope="session")
    async def test_duplicate_email_rejected(self, client):
        timestamp = int(time.time() * 1000)
        email = f"dup{timestamp}@example.com"
        payload = {"email": email, "password": "StrongP@ss123", "full_name": "Dup"}
        await client.post("/api/auth/register", json=payload)
        resp = await client.post("/api/auth/register", json=payload)
        assert resp.status_code == 400

    @pytest.mark.asyncio(scope="session")
    async def test_login_returns_token_in_cookie(self, client):
        timestamp = int(time.time() * 1000)
        email = f"login{timestamp}@example.com"
        password = "StrongP@ss123"
        await client.post("/api/auth/register", json={
            "email": email, "password": password, "full_name": "Login Test"
        })
        resp = await client.post("/api/auth/token", data={
            "username": email, "password": password
        })
        assert resp.status_code == 200
        assert "access_token" in resp.cookies

    @pytest.mark.asyncio(scope="session")
    async def test_wrong_password_rejected(self, client):
        timestamp = int(time.time() * 1000)
        email = f"wrongpw{timestamp}@example.com"
        await client.post("/api/auth/register", json={
            "email": email, "password": "CorrectP@ss123", "full_name": "X"
        })
        resp = await client.post("/api/auth/token", data={
            "username": email, "password": "wrongpassword"
        })
        assert resp.status_code == 401

    @pytest.mark.asyncio(scope="session")
    async def test_protected_endpoint_requires_auth(self, client):
        # Fresh client without cookies or auth headers
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as clean_client:
            resp = await clean_client.post("/api/procurement/analyze", json={
                "product_name": "Test", "product_category": "test", "quantity": 1
            })
            assert resp.status_code == 401


# ── Procurement ────────────────────────────────────────────────────────────────

class TestProcurement:
    @pytest.mark.asyncio(scope="session")
    async def test_procurement_analyze_enqueues_arq_job(self, authenticated_client):
        """Verify that /analyze creates a task and enqueues an ARQ job."""
        # Mock the ARQ pool that the endpoint uses to enqueue jobs
        mock_pool = AsyncMock()
        mock_pool.enqueue_job = AsyncMock(return_value=None)
        mock_pool.get = AsyncMock(return_value=None)
        app.state.arq_pool = mock_pool

        resp = await authenticated_client.post(
            "/api/procurement/analyze",
            json={
                "product_name": "Industrial Sensor",
                "product_category": "electronics",
                "quantity": 500,
                "budget_usd": 50000,
                "payment_terms": "Net 30",
                "delivery_deadline_days": 30,
                "shipping_destination": "Chicago, IL, USA",
                "scoring_weights": {
                    "cost_weight": 0.35,
                    "reliability_weight": 0.40,
                    "risk_weight": 0.25,
                },
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "pending"
        assert "task_id" in data

        # Verify the ARQ job was enqueued with correct function name
        mock_pool.enqueue_job.assert_called_once()
        call_args = mock_pool.enqueue_job.call_args
        assert call_args[0][0] == "run_procurement_task"  # function name
        assert call_args[1]["task_id"] == data["task_id"]
        assert call_args[1]["payload"]["product_name"] == "Industrial Sensor"
        assert call_args[1]["user_id"] is not None

    @pytest.mark.asyncio(scope="session")
    async def test_procurement_status_returns_pending_task(self, authenticated_client):
        """Verify that /status returns the correct status for a pending task."""
        # Mock ARQ pool for the analyze call
        mock_pool = AsyncMock()
        mock_pool.enqueue_job = AsyncMock(return_value=None)
        mock_pool.get = AsyncMock(return_value=None)
        app.state.arq_pool = mock_pool

        # Create a task
        resp = await authenticated_client.post(
            "/api/procurement/analyze",
            json={
                "product_name": "Status Check Test",
                "product_category": "test",
                "quantity": 1,
                "budget_usd": 1000,
                "payment_terms": "Net 30",
                "delivery_deadline_days": 30,
                "shipping_destination": "Chicago, IL, USA",
                "scoring_weights": {
                    "cost_weight": 0.35,
                    "reliability_weight": 0.40,
                    "risk_weight": 0.25,
                },
            },
        )
        task_id = resp.json()["task_id"]

        # Check status — should be pending since worker hasn't processed it
        status_resp = await authenticated_client.get(f"/api/procurement/status/{task_id}")
        assert status_resp.status_code == 200
        status_data = status_resp.json()
        assert status_data["status"] == "pending"
        assert status_data["result"] is None

    @pytest.mark.asyncio(scope="session")
    async def test_invalid_weights_rejected(self, authenticated_client):
        """Weights that don't sum to 1.0 should be rejected."""
        resp = await authenticated_client.post(
            "/api/procurement/analyze",
            json={
                "product_name": "Test",
                "product_category": "test",
                "quantity": 10,
                "budget_usd": 1000,
                "payment_terms": "Net 30",
                "delivery_deadline_days": 30,
                "shipping_destination": "Chicago, IL, USA",
                "scoring_weights": {
                    "cost_weight": 0.5,
                    "reliability_weight": 0.5,
                    "risk_weight": 0.5,  # Sum = 1.5
                },
            },
        )
        assert resp.status_code == 422

    @pytest.mark.asyncio(scope="session")
    async def test_missing_required_fields_rejected(self, authenticated_client):
        resp = await authenticated_client.post(
            "/api/procurement/analyze",
            json={"quantity": 100},
        )
        assert resp.status_code == 422

    @pytest.mark.asyncio(scope="session")
    async def test_procurement_history_returns_sessions(self, authenticated_client):
        resp = await authenticated_client.get("/api/procurement/history")
        assert resp.status_code == 200
        data = resp.json()
        assert "total" in data
        assert "items" in data

    @pytest.mark.asyncio(scope="session")
    async def test_procurement_export_unauthorized_if_no_session(self, authenticated_client):
        resp = await authenticated_client.get("/api/procurement/export/non-existent-id")
        assert resp.status_code == 404

    @pytest.mark.asyncio(scope="session")
    async def test_auth_logout_clears_cookies(self, authenticated_client):
        resp = await authenticated_client.post("/api/auth/logout")
        assert resp.status_code == 200
        set_cookies = resp.headers.get_list("set-cookie")
        # Starlette's delete_cookie sets Max-Age=0 or an empty value with an old expires date
        assert any("access_token=" in c and ("Max-Age=0" in c or "expires=" in c) for c in set_cookies)
