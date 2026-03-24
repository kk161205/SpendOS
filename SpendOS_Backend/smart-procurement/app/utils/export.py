import io
import csv
from app.models.procurement import ProcurementSession

class ProcurementExporter:
    """
    Utility to handle data exports for procurement sessions.
    Separates CSV formatting logic from the routing layer.
    """
    
    @staticmethod
    def generate_csv(session: ProcurementSession) -> io.StringIO:
        """
        Generates a formatted CSV report from a ProcurementSession.
        """
        output = io.StringIO()
        writer = csv.writer(output)
        
        # 1. Report Metadata
        writer.writerow(["Procurement Analysis Report"])
        writer.writerow(["Product Name", session.product_name])
        writer.writerow(["Category", session.category])
        writer.writerow(["Budget (USD)", session.budget or "N/A"])
        writer.writerow(["Shipping Destination", session.shipping_destination or "N/A"])
        writer.writerow(["Payment Terms", session.payment_terms or "N/A"])
        writer.writerow(["Incoterms", session.incoterms or "N/A"])
        writer.writerow(["Deadline (Days)", session.delivery_deadline_days or "N/A"])
        writer.writerow(["Date", session.created_at.strftime("%Y-%m-%d %H:%M:%S")])
        writer.writerow([])
        
        # 2. AI Recommendation Summary
        writer.writerow(["AI Recommendation Summary"])
        writer.writerow([session.ai_explanation or "No explanation available"])
        writer.writerow([])
        
        # 3. Detailed Vendor Table
        writer.writerow(["Vendor List"])
        writer.writerow([
            "Rank", 
            "Vendor Name", 
            "Final Score", 
            "Reliability Score", 
            "Risk Score", 
            "Cost Score", 
            "Reasoning"
        ])
        
        for v in session.vendor_results:
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
        return output
