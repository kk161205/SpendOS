import asyncio
import os
import sys
from dotenv import load_dotenv

sys.path.append("C:/Users/lenovo/Desktop/SpendOS/SpendOS_Backend/smart-procurement")

from app.llm.groq_client import invoke_llm

async def test_risk():
    load_dotenv("C:/Users/lenovo/Desktop/SpendOS/SpendOS_Backend/smart-procurement/.env")
    
    system_prompt = "You are a risk analyst. Return ONLY JSON: {\"risk_score\": 50, \"reasoning\": \"test\"}"
    user_prompt = "Vendor: Test Corp. Category: Office. Region: Germany."
    
    # Test Risk Model (Qwen)
    print("\n--- Testing Qwen (Risk) ---")
    res_qwen = await invoke_llm("qwen/qwen3-32b", system_prompt, user_prompt)
    print(f"RAW QWEN RESPONSE:\n{res_qwen}\n")
    
    # Test Reliability Model (Llama 8B)
    print("\n--- Testing Llama 8B (Reliability) ---")
    res_llama = await invoke_llm("llama-3.1-8b-instant", system_prompt, user_prompt)
    print(f"RAW LLAMA 8B RESPONSE:\n{res_llama}\n")

if __name__ == "__main__":
    asyncio.run(test_risk())
