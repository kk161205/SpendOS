"""
Unit tests for the procurement cache key generation utility.

Validates:
  - Deterministic output (same input → same key)
  - Field sensitivity (changing any field → different key)
  - String normalization (case, whitespace, certification order)
  - Parity between schema-based and dict-based entry points
"""

import pytest
from app.utils.cache_utils import (
    generate_procurement_hash,
    generate_procurement_hash_from_dict,
)
from app.schemas.procurement_schema import ProcurementRequest


# ── Helpers ────────────────────────────────────────────────────────────────────

def _base_dict():
    """Canonical payload used across tests."""
    return {
        "product_name": "Industrial Sensor",
        "product_category": "Electronics",
        "description": "High-precision temperature sensor",
        "quantity": 500,
        "budget_usd": 50000.0,
        "required_certifications": ["ISO 9001", "CE Mark"],
        "delivery_deadline_days": 30,
        "scoring_weights": {
            "cost_weight": 0.35,
            "reliability_weight": 0.40,
            "risk_weight": 0.25,
        },
    }


def _base_schema():
    return ProcurementRequest(**_base_dict())


# ── Determinism ────────────────────────────────────────────────────────────────

class TestDeterminism:
    def test_same_input_produces_same_hash(self):
        key_a = generate_procurement_hash(_base_schema())
        key_b = generate_procurement_hash(_base_schema())
        assert key_a == key_b

    def test_hash_starts_with_prefix(self):
        key = generate_procurement_hash(_base_schema())
        assert key.startswith("procurement_cache:")

    def test_hash_is_sha256_length(self):
        key = generate_procurement_hash(_base_schema())
        hex_part = key.split(":")[1]
        assert len(hex_part) == 64  # SHA-256 = 64 hex chars


# ── Field Sensitivity ─────────────────────────────────────────────────────────

class TestFieldSensitivity:
    """Changing ANY user-input field must produce a different cache key."""

    def test_different_quantity(self):
        base = _base_dict()
        alt = {**base, "quantity": 1000}
        assert generate_procurement_hash_from_dict(base) != generate_procurement_hash_from_dict(alt)

    def test_different_certifications(self):
        base = _base_dict()
        alt = {**base, "required_certifications": ["ISO 14001"]}
        assert generate_procurement_hash_from_dict(base) != generate_procurement_hash_from_dict(alt)

    def test_different_deadline(self):
        base = _base_dict()
        alt = {**base, "delivery_deadline_days": 60}
        assert generate_procurement_hash_from_dict(base) != generate_procurement_hash_from_dict(alt)

    def test_different_description(self):
        base = _base_dict()
        alt = {**base, "description": "Low-precision humidity sensor"}
        assert generate_procurement_hash_from_dict(base) != generate_procurement_hash_from_dict(alt)

    def test_different_product_name(self):
        base = _base_dict()
        alt = {**base, "product_name": "Pressure Gauge"}
        assert generate_procurement_hash_from_dict(base) != generate_procurement_hash_from_dict(alt)

    def test_different_budget(self):
        base = _base_dict()
        alt = {**base, "budget_usd": 100000.0}
        assert generate_procurement_hash_from_dict(base) != generate_procurement_hash_from_dict(alt)

    def test_different_weights(self):
        base = _base_dict()
        alt = {**base, "scoring_weights": {"cost_weight": 0.50, "reliability_weight": 0.30, "risk_weight": 0.20}}
        assert generate_procurement_hash_from_dict(base) != generate_procurement_hash_from_dict(alt)


# ── Normalization ──────────────────────────────────────────────────────────────

class TestNormalization:
    def test_case_insensitive_product_name(self):
        base = _base_dict()
        alt = {**base, "product_name": "INDUSTRIAL SENSOR"}
        assert generate_procurement_hash_from_dict(base) == generate_procurement_hash_from_dict(alt)

    def test_whitespace_insensitive(self):
        base = _base_dict()
        alt = {**base, "product_name": "  Industrial Sensor  "}
        assert generate_procurement_hash_from_dict(base) == generate_procurement_hash_from_dict(alt)

    def test_certification_order_independent(self):
        base = _base_dict()
        alt = {**base, "required_certifications": ["CE Mark", "ISO 9001"]}
        assert generate_procurement_hash_from_dict(base) == generate_procurement_hash_from_dict(alt)

    def test_certification_case_insensitive(self):
        base = _base_dict()
        alt = {**base, "required_certifications": ["iso 9001", "ce mark"]}
        assert generate_procurement_hash_from_dict(base) == generate_procurement_hash_from_dict(alt)


# ── Schema ↔ Dict Parity ──────────────────────────────────────────────────────

class TestParity:
    def test_schema_and_dict_produce_same_hash(self):
        """The API route (schema) and worker (dict) must agree on the key."""
        schema_key = generate_procurement_hash(_base_schema())
        dict_key = generate_procurement_hash_from_dict(_base_dict())
        assert schema_key == dict_key

    def test_parity_with_optional_fields_none(self):
        minimal = {
            "product_name": "Widget",
            "product_category": "General",
            "quantity": 10,
            "scoring_weights": {"cost_weight": 0.35, "reliability_weight": 0.40, "risk_weight": 0.25},
        }
        schema = ProcurementRequest(**minimal)
        assert generate_procurement_hash(schema) == generate_procurement_hash_from_dict(minimal)
