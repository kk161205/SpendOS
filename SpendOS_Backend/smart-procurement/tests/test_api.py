"""
API endpoint tests using pytest + httpx.
Tests health, auth, and procurement endpoints.
"""

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from unittest.mock import AsyncMock, patch

from app.main import app
from app.graph.state import ProcurementWorkflowState, ScoredVendor, VendorData


# ── Fixtures ───────────────────────────────────────────────────────────────────

@pytest_asyncio.fixture
async def client():
    """Async HTTP client connected to the FastAPI test app."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest_asyncio.fixture
async def auth_token(client: AsyncClient):
    """Register a test user and return a valid JWT token string."""
    import time
    # Use higher precision for uniqueness
    email = f"test{int(time.time() * 1000)}@example.com"
    await client.post("/api/auth/register", json={
        "email": email,
        "password": "testpassword",
        "full_name": "Test User",
    })
    resp = await client.post("/api/auth/token", data={
        "username": email,
        "password": "testpassword",
    })
    # The cookie value from the server is "Bearer <jwt>"
    token_with_prefix = resp.cookies.get("access_token")
    if token_with_prefix and " " in token_with_prefix:
         return token_with_prefix.split(" ")[1]
    return token_with_prefix


@pytest.fixture
def auth_headers(auth_token):
    """Fixture to provide authentication headers with the JWT token."""
    if auth_token:
        # We need to send the EXACT cookie value the app expects: "Bearer <jwt>"
        return {"Cookie": f"access_token=Bearer {auth_token}"}
    return {}


# ── Health Check ───────────────────────────────────────────────────────────────

class TestHealth:
    @pytest.mark.asyncio
    async def test_health_endpoint_returns_200(self, client):
        resp = await client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "healthy"

    @pytest.mark.asyncio
    async def test_root_returns_service_info(self, client):
        resp = await client.get("/")
        assert resp.status_code == 200
        assert "service" in resp.json()


# ── Auth ───────────────────────────────────────────────────────────────────────

class TestAuth:
    @pytest.mark.asyncio
    async def test_register_new_user(self, client):
        import time
        resp = await client.post("/api/auth/register", json={
            "email": f"new{int(time.time())}@example.com",
            "password": "securepassword",
            "full_name": "New User",
        })
        assert resp.status_code == 201
        assert "user_id" in resp.json()

    @pytest.mark.asyncio
    async def test_duplicate_email_rejected(self, client):
        import time
        email = f"dup{int(time.time())}@example.com"
        payload = {"email": email, "password": "password123", "full_name": "Dup"}
        await client.post("/api/auth/register", json=payload)
        resp = await client.post("/api/auth/register", json=payload)
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_login_returns_token(self, client):
        import time
        email = f"login{int(time.time())}@example.com"
        await client.post("/api/auth/register", json={
            "email": email, "password": "mypassword", "full_name": "Login Test"
        })
        # Token endpoint expects form data
        resp = await client.post("/api/auth/token", data={
            "username": email, "password": "mypassword"
        })
        assert resp.status_code == 200
        assert "access_token" in resp.json()

    @pytest.mark.asyncio
    async def test_wrong_password_rejected(self, client):
        import time
        email = f"wrongpw{int(time.time())}@example.com"
        await client.post("/api/auth/register", json={
            "email": email, "password": "correctpass", "full_name": "X"
        })
        resp = await client.post("/api/auth/token", data={
            "username": email, "password": "wrongpass"
        })
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_protected_endpoint_requires_auth(self, client):
        resp = await client.post("/api/procurement/analyze", json={
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

    @pytest.mark.asyncio
    async def test_procurement_analyze_returns_results(self, client, auth_headers):
        mock_state = self._mock_workflow_state()

        with patch(
            "app.api.procurement_routes.run_procurement_workflow",
            new_callable=AsyncMock,
            return_value=mock_state,
        ):
            resp = await client.post(
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
                headers=auth_headers,
            )
            assert resp.status_code == 200
            data = resp.json()
            assert data["status"] == "completed"
            assert len(data["ranked_vendors"]) == 1
            assert data["ranked_vendors"][0]["vendor_name"] == "Best Vendor Inc"

    @pytest.mark.asyncio
    async def test_invalid_weights_rejected(self, client, auth_headers):
        """Weights that don't sum to 1.0 should be rejected."""
        resp = await client.post(
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
            headers=auth_headers,
        )
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_missing_required_fields_rejected(self, client, auth_headers):
        resp = await client.post(
            "/api/procurement/analyze",
            json={"quantity": 100},
            headers=auth_headers,
        )
        assert resp.status_code == 422
