"""Characterize LeechHealthDamageNugget's payout (engine/combat/leech.refund)."""
from test_plans import small  # noqa: F401,I001  (puts experimental/cnv on the path)


def test_the_payout_is_what_the_victim_lost_at_most_and_one_claim_only():
    """engine/combat/leech.refund (step N2): a damage claim on a survivor pays by the smaller of its hit and what the
    victim lost (a floor kept the rest); a maximum claim on a survivor and two claims at once pay nothing (gaps)."""
    import types
    from engine.combat import leech
    mended, gaps = [], []

    def gap(tag, why):
        gaps.append(tag)
    healer = types.SimpleNamespace(alive=True, mend=mended.append)
    victim = types.SimpleNamespace(hp=95.0, max_hp=100.0)
    leech.refund([(healer, 'damage', 0.5, 20.0)], victim, 100.0, gap)
    assert mended == [2.5] and gaps == []           # lost 5 of the hit's 20
    leech.refund([(healer, 'maximum', 0.5, 0.0)], victim, 100.0, gap)
    assert mended == [2.5, 0.0] and gaps == ['LeechPercentMaxHealthDamageNugget']
    leech.refund([(healer, 'damage', 0.5, 20.0)] * 2, victim, 100.0, gap)
    leech.refund([], victim, 100.0, gap)
    assert mended == [2.5, 0.0] and gaps == ['LeechPercentMaxHealthDamageNugget', 'leech']
