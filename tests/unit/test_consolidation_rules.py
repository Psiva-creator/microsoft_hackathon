from app.jobs.consolidate import compute_decay_weight


def test_compute_decay_weight_calculation():
    # If age is 0 days, weight should remain unchanged (1.0)
    w_now = compute_decay_weight(0, half_life_days=90)
    assert round(w_now, 4) == 1.0

    # If age equals half-life (90 days), weight should be exactly 0.5
    w_half = compute_decay_weight(90, half_life_days=90)
    assert round(w_half, 2) == 0.50

    # If age is 180 days (two half-lives), weight should be capped by min_weight (0.3)
    w_two_half = compute_decay_weight(180, half_life_days=90, min_weight=0.1)
    assert round(w_two_half, 2) == 0.25

    # Verify default min_weight cap
    w_old = compute_decay_weight(1000, half_life_days=90, min_weight=0.3)
    assert round(w_old, 2) == 0.30
