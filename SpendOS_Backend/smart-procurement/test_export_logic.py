import asyncio
import csv
import io
import json
from datetime import datetime, timezone
from unittest.mock import MagicMock, AsyncMock
from fastapi.responses import StreamingResponse

# Mocking the models and response structure to test the logic in isolation
class MockVendor:
    def __init__(self, rank, name, final, reliability, risk, cost, explanation):
        self.rank = rank
        self.vendor_name = name
        self.final_score = final
        self.reliability_score = reliability
        self.risk_score = risk
        self.cost_score = cost
        self.explanation = explanation

class MockSession:
    def __init__(self, id, name, category, budget, explanation, vendors):
        self.id = id
        self.product_name = name
        self.category = category
        self.budget = budget
        self.ai_explanation = explanation
        self.vendor_results = vendors
        self.created_at = datetime.now(timezone.utc)

async def simulate_export_logic(session):
    # This mirrors the logic in procurement_routes.py
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Headers - Session Metadata
    writer.writerow(["Procurement Analysis Report"])
    writer.writerow(["Product Name", session.product_name])
    writer.writerow(["Category", session.category])
    writer.writerow(["Budget (USD)", session.budget or "N/A"])
    writer.writerow(["Date", session.created_at.strftime("%Y-%m-%d %H:%M:%S")])
    writer.writerow([])
    
    # AI Explanation
    writer.writerow(["AI Recommendation Summary"])
    writer.writerow([session.ai_explanation or "No explanation available"])
    writer.writerow([])
    
    # Vendor Results
    writer.writerow(["Vendor List"])
    writer.writerow(["Rank", "Vendor Name", "Final Score", "Reliability Score", "Risk Score", "Cost Score", "Reasoning"])
    
    # Sort vendors by rank
    sorted_vendors = sorted(session.vendor_results, key=lambda v: v.rank)
    for v in sorted_vendors:
        writer.writerow([
            v.rank,
            v.vendor_name,
            f"{v.final_score:.2f}",
            f"{v.reliability_score:.2f}",
            f"{v.risk_score:.2f}",
            f"{v.cost_score:.2f}",
            v.explanation or ""
        ])
    
    output.seek(0)
    return output.getvalue()

async def test_csv_format():
    print("Starting Isolated CSV Export Logic Test...")
    
    # Create mock data
    vendors = [
        MockVendor(1, "Top Vendor", 95.5, 98.0, 5.0, 92.0, "Excellent choice"),
        MockVendor(2, "Budget Option", 88.2, 85.0, 15.0, 98.0, "Cheaper but risky")
    ]
    session = MockSession(
        "session-123", 
        "Industrial Sensors", 
        "Electronics", 
        5000.0, 
        "Recommendation based on reliability.", 
        vendors
    )
    
    # Run the logic
    csv_content = await simulate_export_logic(session)
    
    print("Generated CSV Content:")
    print(csv_content)
    
    # Assertions
    lines = csv_content.splitlines()
    assert "Procurement Analysis Report" in lines[0]
    assert "Product Name,Industrial Sensors" in lines[1]
    assert "Category,Electronics" in lines[2]
    assert "Budget (USD),5000.0" in lines[3]
    
    assert "AI Recommendation Summary" in csv_content
    assert "Recommendation based on reliability." in csv_content
    
    assert "Vendor List" in csv_content
    assert "1,Top Vendor,95.50,98.00,5.00,92.00,Excellent choice" in csv_content
    assert "2,Budget Option,88.20,85.00,15.00,98.00,Cheaper but risky" in csv_content
    
    print("\n--- CSV LOGIC VERIFICATION SUCCESS ---")

if __name__ == "__main__":
    asyncio.run(test_csv_format())
