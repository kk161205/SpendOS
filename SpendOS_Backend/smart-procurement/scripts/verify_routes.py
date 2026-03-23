import time
import requests

BASE_URL = "http://127.0.0.1:8000"
session = requests.Session()

def test_routes():
    print("1. Testing Health Check")
    r = session.get(f"{BASE_URL}/health")
    print(f"Health Check: {r.status_code} - {r.json()}")
    assert r.status_code == 200

    print("\n2. Testing Root")
    r = session.get(f"{BASE_URL}/")
    print(f"Root: {r.status_code} - {r.json()}")
    assert r.status_code == 200

    print("\n3. Testing User Registration")
    username = f"test_{int(time.time())}@example.com"
    r = session.post(f"{BASE_URL}/api/auth/register", json={
        "email": username,
        "password": "StrongPassword123!",
        "full_name": "Test User"
    })
    print(f"Register: {r.status_code} - {r.json()}")
    assert r.status_code == 201

    print("\n4. Testing User Login")
    r = session.post(f"{BASE_URL}/api/auth/token", data={
        "username": username,
        "password": "StrongPassword123!"
    })
    print(f"Login: {r.status_code} - {r.cookies}")
    assert r.status_code == 200
    # Auth cookie is set in the session

    print("\n5. Testing Procurement Analysis Submission")
    r = session.post(f"{BASE_URL}/api/procurement/analyze", json={
        "product_name": "Industrial Robots",
        "product_category": "machinery",
        "quantity": 10,
        "budget_usd": 150000,
        "scoring_weights": {
            "cost_weight": 0.4,
            "reliability_weight": 0.4,
            "risk_weight": 0.2
        }
    })
    print(f"Analyze: {r.status_code} - {r.json()}")
    assert r.status_code == 200
    task_id = r.json()["task_id"]

    print(f"\n6. Polling Procurement Status (Task ID: {task_id})")
    status = "pending"
    for _ in range(15):
        r = session.get(f"{BASE_URL}/api/procurement/status/{task_id}")
        data = r.json()
        print(f"Status check ({_}): {data['status']}")
        status = data["status"]
        if status in ["completed", "failed"]:
            print(f"Final Result: {data['result']}")
            break
        time.sleep(2)
    
    assert status in ["completed", "failed"]

    print("\n7. Testing Procurement History")
    r = session.get(f"{BASE_URL}/api/procurement/history")
    print(f"History: {r.status_code} - {r.json()}")
    assert r.status_code == 200
    
    print("\n8. Testing User Logout")
    r = session.post(f"{BASE_URL}/api/auth/logout")
    print(f"Logout: {r.status_code} - {r.json()}")
    assert r.status_code == 200
    
    print("\n✅ All routes successfully verified manually.")

if __name__ == "__main__":
    time.sleep(2) # Give server time to start
    test_routes()
