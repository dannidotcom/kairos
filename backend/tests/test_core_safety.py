import pytest

from app.services.campaign import effective_warmup_limit, has_quota, has_shared_contact_lock, stop_campaign_lead_on_reply
from app.services.scoring import score_profile_with_rules


def test_warmup_limits_growth():
    assert effective_warmup_limit(100, 7, warmup_days=0) == 25
    assert effective_warmup_limit(100, 7, warmup_days=14) == 50
    assert effective_warmup_limit(100, 7, warmup_days=28) == 100


def test_quota_and_shared_contact_lock_are_organization_isolated():
    assert has_quota(used=3, limit=5)
    assert not has_quota(used=5, limit=5)
    assert has_shared_contact_lock(org_a="a", prospect_id="p", seat_id="1", org_b="a")
    assert not has_shared_contact_lock(org_a="a", prospect_id="p", seat_id="1", org_b="b")


def test_reply_always_stops_sequence():
    lead_state = {"status": "messaged", "current_step": 2}
    stopped = stop_campaign_lead_on_reply(lead_state)
    assert stopped["status"] == "replied"
    assert stopped["stopped"] is True


def test_deterministic_score_never_fabricates():
    result = score_profile_with_rules(profile={}, icp={})
    assert 0 <= result["score"] <= 100
    assert result["justification"] == "Aucun critère vérifié disponible."
