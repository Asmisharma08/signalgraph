"""
SignalGraph — Signal Detectors (Milestone 5)
=============================================
Four anomaly detection functions, each returning 0–100.
"""


def price_anomaly_score(return_pct: float, rolling_avg_return: float, rolling_std_return: float) -> float:
    """
    How unusual this tick's return is relative to the instrument's own
    recent behavior, expressed as a z-score-like distance scaled to 0-100.
    A floor is applied to the standard deviation so a brand-new instrument
    with no seeded volatility yet doesn't produce a divide-by-zero blowup.
    """
    # Floored at 1%: a std estimate built from only a handful of ticks
    # (as in a short demo replay) is too noisy to trust below this, and
    # without a floor a near-zero early std turns ordinary small ticks
    # into false anomalies.
    std = max(rolling_std_return, 0.01)
    z = abs(return_pct - rolling_avg_return) / std
    return min(100.0, max(0.0, z * 25.0))


def volume_anomaly_score(volume: float, rolling_avg_volume: float) -> float:
    """
    How far today's volume is above (or below) its rolling average.
    A ratio of 1x (exactly average) scores 0; 3x scores 100.
    """
    if rolling_avg_volume <= 0:
        # No baseline yet to compare against — nothing can be called
        # anomalous relative to an unknown history.
        return 0.0
    ratio = volume / rolling_avg_volume
    return min(100.0, max(0.0, (ratio - 1.0) * 50.0))


def sector_divergence_score(instrument_return: float, sector_basket_return: float) -> float:
    """
    How far this instrument's return has diverged from its sector peer
    basket's average return. A 5-percentage-point gap scores 100.
    """
    diff = abs(instrument_return - sector_basket_return)
    return min(100.0, diff * 2000.0)


def structural_trigger_score(price: float, historical_high: float, historical_low: float) -> float:
    """
    Fires when price breaks outside the instrument's prior observed
    range. A 10% breakout beyond the prior high (or below the prior
    low) scores 100.
    """
    if historical_high and price > historical_high:
        breakout = (price - historical_high) / historical_high
        return min(100.0, max(0.0, breakout * 1000.0))
    if historical_low and price < historical_low:
        breakdown = (historical_low - price) / historical_low
        return min(100.0, max(0.0, breakdown * 1000.0))
    return 0.0
