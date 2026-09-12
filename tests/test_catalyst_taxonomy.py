import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import pytest
from pydantic import ValidationError

from stock_intel.models.catalyst import CATALYST_PRIORS, Catalyst, CatalystType, Direction, Horizon, Impact


def test_every_catalyst_type_has_priors():
    for catalyst_type in CatalystType:
        assert catalyst_type in CATALYST_PRIORS, f"Missing priors for {catalyst_type}"


def test_catalyst_cannot_be_constructed_without_evidence():
    """Every Catalyst/sentiment claim must be traceable to a source
    (Specification.md Section 8) — enforced as a model-level invariant."""
    with pytest.raises(ValidationError):
        Catalyst(
            id="cat_no_evidence",
            ticker="TEST",
            catalyst_type=CatalystType.EARNINGS_BEAT,
            headline="Unsourced claim",
            direction=Direction.POSITIVE,
            impact=Impact.HIGH,
            horizon=Horizon.IMMEDIATE,
            confidence=0.9,
            evidence=[],
        )


def test_catalyst_confidence_must_be_in_unit_interval():
    from stock_intel.models.catalyst import Evidence

    evidence = [
        Evidence(
            source_name="Test",
            url="https://example.com",
            published_at=datetime.now(timezone.utc),
            summary="A paraphrased summary.",
        )
    ]
    with pytest.raises(ValidationError):
        Catalyst(
            id="cat_bad_confidence",
            ticker="TEST",
            catalyst_type=CatalystType.EARNINGS_BEAT,
            headline="Test",
            direction=Direction.POSITIVE,
            impact=Impact.HIGH,
            horizon=Horizon.IMMEDIATE,
            confidence=1.5,  # out of range
            evidence=evidence,
        )
