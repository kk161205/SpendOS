from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

# Test 1: Request from trusted proxy (localhost - default in settings)
# It should respect X-Forwarded-For and X-Forwarded-Proto
print("--- TEST 1: Trusted Proxy (127.0.0.1) ---")
# The TestClient sends requests originating from 127.0.0.1 by default (or we can inject it as the actual client).
# ProxyHeadersMiddleware checks if the actual client IP is in trusted_hosts.
# To simulate the actual client IP in TestClient, we shouldn't pass it in headers, we pass it in the scope or use default.
# TestClient defaults to client=("testclient", 50000). Let's explicitly set the client IP.
client = TestClient(app)

@app.get("/test-ip")
async def test_ip(request):
    return {
        "client_host": request.client.host,
        "scheme": request.scope.get("scheme"),
    }

# TestClient default client is usually set in ASGI scope as ["testclient", 50000] which is NOT in trusted hosts (127.0.0.1).
# We can pass client=("127.0.0.1", 1234) into the request.
response = client.get(
    "/test-ip", 
    headers={
        "X-Forwarded-For": "203.0.113.1",
        "X-Forwarded-Proto": "https"
    },
    # Note: older versions of httpx/TestClient didn't allow passing client easily without transport.
)
print("Request from default TestClient (untrusted):", response.json())

response = client.get("/test-ip")
print("No headers:", response.json())
