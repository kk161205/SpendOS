"""
Shared cache key generation for procurement pipeline.

Used by both the API route (cache-read) and the ARQ worker (cache-write)
to ensure identical key derivation from the same input data.
"""

import hashlib
import json
from typing import List, Optional


def _build_cache_payload(
    product_name: str,
    product_category: str,
    description: Optional[str],
    quantity: int,
    budget_usd: Optional[float],
    payment_terms: Optional[str],
    shipping_destination: Optional[str],
    vendor_region_preference: Optional[str],
    incoterms: Optional[str],
    required_certifications: Optional[List[str]],
    delivery_deadline_days: Optional[int],
    scoring_weights: dict,
) -> dict:
    """
    Build a normalized, deterministic dict of ALL user-input fields
    suitable for SHA-256 hashing.
    """
    return {
        "product": product_name.lower().strip(),
        "category": product_category.lower().strip(),
        "description": (description or "").lower().strip(),
        "quantity": quantity,
        "budget": budget_usd,
        "payment_terms": (payment_terms or "").lower().strip() if payment_terms else None,
        "shipping_destination": (shipping_destination or "").lower().strip() if shipping_destination else None,
        "vendor_region": (vendor_region_preference or "").lower().strip() if vendor_region_preference else None,
        "incoterms": (incoterms or "").lower().strip() if incoterms else None,
        "certifications": sorted(
            c.lower().strip() for c in (required_certifications or [])
        ),
        "deadline": delivery_deadline_days,
        "weights": scoring_weights,
    }


def _hash_payload(payload: dict) -> str:
    """SHA-256 hash a dict into a prefixed Redis key."""
    raw = json.dumps(payload, sort_keys=True).encode("utf-8")
    return f"procurement_cache:{hashlib.sha256(raw).hexdigest()}"


def generate_procurement_hash(schema) -> str:
    """
    Generate a deterministic cache key from a ProcurementRequest schema object.

    Used by the API route on cache-read path.
    """
    data = _build_cache_payload(
        product_name=schema.product_name,
        product_category=schema.product_category,
        description=schema.description,
        quantity=schema.quantity,
        budget_usd=schema.budget_usd,
        payment_terms=schema.payment_terms,
        shipping_destination=schema.shipping_destination,
        vendor_region_preference=schema.vendor_region_preference,
        incoterms=schema.incoterms,
        required_certifications=schema.required_certifications,
        delivery_deadline_days=schema.delivery_deadline_days,
        scoring_weights=schema.scoring_weights.model_dump(),
    )
    return _hash_payload(data)


def generate_procurement_hash_from_dict(payload: dict) -> str:
    """
    Generate a deterministic cache key from a raw payload dict.

    Used by the ARQ worker on cache-write path.
    """
    data = _build_cache_payload(
        product_name=payload["product_name"],
        product_category=payload["product_category"],
        description=payload.get("description"),
        quantity=payload["quantity"],
        budget_usd=payload["budget_usd"],
        payment_terms=payload.get("payment_terms"),
        shipping_destination=payload.get("shipping_destination"),
        vendor_region_preference=payload.get("vendor_region_preference"),
        incoterms=payload.get("incoterms"),
        required_certifications=payload.get("required_certifications"),
        delivery_deadline_days=payload["delivery_deadline_days"],
        scoring_weights=payload.get("scoring_weights", {}),
    )
    return _hash_payload(data)
