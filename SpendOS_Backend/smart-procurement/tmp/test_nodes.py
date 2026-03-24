import asyncio
import os
import sys
from dotenv import load_dotenv

# Add project root to path
sys.path.append("C:/Users/lenovo/Desktop/SpendOS/SpendOS_Backend/smart-procurement")

from app.graph.state import ProcurementWorkflowState, UserRequirements, VendorData, ScoredVendor
from app.agents.vendor_discovery import vendor_discovery_node
from app.agents.vendor_enrichment import vendor_enrichment_node
from app.agents.risk_analysis import risk_analysis_node
from app.agents.reliability_analysis import reliability_analysis_node
from app.agents.explanation import explanation_node

async def test_node_fn(name, node_fn, state):
    print(f"\n[TEST] Testing node: {name}...")
    try:
        new_state = await node_fn(state)
        print(f"[SUCCESS] {name} completed.")
        return new_state
    except Exception as e:
        print(f"[FAILURE] {name} failed: {e}")
        # Diagnostic logs are now inside the agent code, but we can print stack trace here too
        import traceback
        traceback.print_exc()
        return None

async def main():
    load_dotenv("C:/Users/lenovo/Desktop/SpendOS/SpendOS_Backend/smart-procurement/.env")
    
    req = UserRequirements(
        product_name="Office Chairs",
        product_category="Office Supplies",
        quantity=10,
        budget_usd=2000,
        delivery_deadline_days=30,
        payment_terms="Net 30",
        shipping_destination="New York"
    )
    
    vendor = VendorData(
        vendor_id="test-123",
        name="Steelcase",
        category="Office Supplies",
        website="https://www.steelcase.com"
    )

    # 1. Enrichment (Model: groq/compound)
    print("\n>>> Node: Enrichment (Target: groq/compound)")
    state1 = ProcurementWorkflowState(user_requirements=req, vendors=[vendor])
    await test_node_fn("Enrichment", vendor_enrichment_node, state1)

    # 2. Risk (Target: qwen/qwen3-32b)
    print("\n>>> Node: Risk Analysis (Target: qwen/qwen3-32b)")
    state2 = ProcurementWorkflowState(user_requirements=req, enriched_vendors=[vendor])
    await test_node_fn("Risk", risk_analysis_node, state2)

    # 3. Reliability (Target: llama-3.1-8b-instant)
    print("\n>>> Node: Reliability Analysis (Target: llama-3.1-8b-instant)")
    state3 = ProcurementWorkflowState(user_requirements=req, enriched_vendors=[vendor])
    await test_node_fn("Reliability", reliability_analysis_node, state3)

    # 4. Explanation (Target: llama-3.3-70b-versatile)
    print("\n>>> Node: Explanation (Target: llama-3.3-70b-versatile)")
    scored = ScoredVendor(vendor_data=vendor, final_score=85, rank=1)
    state4 = ProcurementWorkflowState(user_requirements=req, ranked_vendors=[scored])
    await test_node_fn("Explanation", explanation_node, state4)

if __name__ == "__main__":
    asyncio.run(main())
