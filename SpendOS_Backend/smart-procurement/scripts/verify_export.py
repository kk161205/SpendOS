import asyncio
import httpx
import os
import sys

# Mocking environment secrets if needed
os.environ["SECRET_KEY"] = "super-secret"
os.environ["ALGORITHM"] = "HS256"

# Adding the app directory to sys.path
sys.path.append(os.getcwd())

async def test_export():
    # We'll use a mock approach since we don't have a live DB with sessions
    from app.main import app
    from app.auth import create_access_token
    from app.database import async_session_factory
    from app.models.procurement import ProcurementSession, VendorResult
    from sqlalchemy import select
    
    # 1. Create a mock token
    token = create_access_token(data={"sub": "test-user-123"})
    headers = {"Authorization": f"Bearer {token}"}
    
    async with async_session_factory() as db:
        # 2. Create a dummy session for testing
        session = ProcurementSession(
            user_id="test-user-123",
            product_name="Verification Test Item",
            category="Test Cat",
            budget=1000.0,
            ai_explanation="Test explanation"
        )
        db.add(session)
        await db.commit()
        await db.refresh(session)
        
        vendor = VendorResult(
            session_id=session.id,
            vendor_name="Test Vendor",
            final_score=90.0,
            risk_score=10.0,
            reliability_score=95.0,
            cost_score=85.0,
            rank=1,
            explanation="Great vendor"
        )
        db.add(vendor)
        await db.commit()
        
        session_id = session.id
        print(f"Created test session: {session_id}")

    # 3. Call the export endpoint
    async with httpx.AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get(f"/api/procurement/export/{session_id}", headers=headers)
        
        print(f"Status: {response.status_code}")
        print(f"Headers: {response.headers}")
        
        if response.status_code == 200:
            content = response.text
            print("CSV Content Snippet:")
            print("\n".join(content.splitlines()[:10]))
            
            # Basic assertions
            assert "Procurement Analysis Report" in content
            assert "Verification Test Item" in content
            assert "Test Vendor" in content
            assert "90.00" in content
            print("\n--- VERIFICATION SUCCESS ---")
        else:
            print(f"FAILED: {response.text}")
            sys.exit(1)

    # Cleanup (Optional, but good for local dev)
    async with async_session_factory() as db:
        res = await db.execute(select(ProcurementSession).where(ProcurementSession.id == session_id))
        s = res.scalar_one_or_none()
        if s:
            await db.delete(s)
            await db.commit()
            print("Cleaned up test session.")

if __name__ == "__main__":
    asyncio.run(test_export())
