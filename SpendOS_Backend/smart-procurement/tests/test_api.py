"""
API endpoint tests using pytest + httpx.
Tests health, auth, and procurement endpoints.
"""

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from unittest.mock import AsyncMock, patch
import time

from app.main import app
from app.graph.state import ProcurementWorkflowState, ScoredVendor, VendorData


# ── Fixtures ───────────────────────────────────────────────────────────────────

@pytest_asyncio.fixture(scope="session")
async def client():
    """Async HTTP client connected to the FastAPI test app with cookie support."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest_asyncio.fixture(scope="session")
async def authenticated_client(client: AsyncClient):
    """Register a test user and ensure the client has the auth cookie and headers."""
    timestamp = int(time.time() * 1000)
    email = f"test{timestamp}@example.com"
    password = "StrongP@ss123"
    
    # 1. Register
    await client.post("/api/auth/register", json={
        "email": email,
        "password": password,
        "full_name": "Test User",
    })
    
    # 2. Login (This sets the 'access_token' cookie in the client)
    resp = await client.post("/api/auth/token", data={
        "username": email,
        "password": password,
    })
    
    # Also set Authorization header as a backup (more robust for ASGITransport tests)
    token_with_prefix = resp.cookies.get("access_token")
    if token_with_prefix:
        client.headers.update({"Authorization": token_with_prefix.strip('"')})
    
    return client


# ── Health Check ───────────────────────────────────────────────────────────────

class TestHealth:
    @pytest.mark.asyncio(scope="session")
    async def test_health_endpoint_returns_200(self, client):
        resp = await client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "healthy"

    @pytest.mark.asyncio(scope="session")
    async def test_root_returns_service_info(self, client):
        resp = await client.get("/")
        assert resp.status_code == 200
        assert "service" in resp.json()


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
    def _mock_workflow_state(self):
        sv = ScoredVendor(
            vendor_data=VendorData(
                vendor_id="v1",
                name="Best Vendor Inc",
                category="electronics",
                country="Germany",
                price_per_unit_usd=45.0,
            ),
            risk_score=25.0,
            reliability_score=80.0,
            cost_score=90.0,
            final_score=78.0,
            rank=1,
            risk_reasoning="Low risk due to strong financials.",
            reliability_reasoning="Highly reliable with strong track record.",
        )
        return ProcurementWorkflowState(
            ranked_vendors=[sv],
            ai_explanation="Best Vendor Inc is the recommended vendor based on analysis.",
        )

    @pytest.mark.asyncio(scope="session")
    async def test_procurement_analyze_returns_results(self, authenticated_client):
        mock_state = self._mock_workflow_state()

        with patch(
            "app.api.procurement_routes.run_procurement_workflow",
            new_callable=AsyncMock,
            return_value=mock_state,
        ):
            resp = await authenticated_client.post(
                "/api/procurement/analyze",
                json={
                    "product_name": "Industrial Sensor",
                    "product_category": "electronics",
                    "quantity": 500,
                    "budget_usd": 50000,
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
            task_id = data["task_id"]
            
            # Follow-up: check status (should be completed as background tasks run sync in these tests)
            status_resp = await authenticated_client.get(f"/api/procurement/status/{task_id}")
            assert status_resp.status_code == 200
            status_data = status_resp.json()
            assert status_data["status"] == "completed"
            assert status_data["result"]["ranked_vendors"][0]["vendor_name"] == "Best Vendor Inc"

    @pytest.mark.asyncio(scope="session")
    async def test_invalid_weights_rejected(self, authenticated_client):
        """Weights that don't sum to 1.0 should be rejected."""
        resp = await authenticated_client.post(
            "/api/procurement/analyze",
            json={
                "product_name": "Test",
                "product_category": "test",
                "quantity": 10,
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
