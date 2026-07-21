"""
Building Health Index (0-100): combines strain, tilt, vibration, battery,
and communication health into a single decision-support number, as
specified in the platform's architecture doc.

Design: start at 100 and subtract weighted penalties as each metric
moves further from its safe baseline. Weights sum to 100 so the worst
possible reading across every factor bottoms out at 0.
"""

WEIGHTS = {
    "strain": 30,
    "tilt": 25,
    "vibration": 25,
    "battery": 10,
    "comm": 10,
}


def _ratio_penalty(value: float, threshold: float, weight: float) -> float:
    """Linear penalty that reaches `weight` once value hits 1.5x threshold."""
    if threshold <= 0:
        return 0
    ratio = abs(value) / threshold
    penalty = min(ratio / 1.5, 1.0) * weight
    return penalty


def compute_health_index(strain, tilt, vibration, battery, comm_ok, thresholds) -> int:
    penalty = 0
    penalty += _ratio_penalty(strain, thresholds["strain_threshold"], WEIGHTS["strain"])
    penalty += _ratio_penalty(tilt, thresholds["tilt_threshold"], WEIGHTS["tilt"])
    penalty += _ratio_penalty(vibration, thresholds["vibration_threshold"], WEIGHTS["vibration"])

    if battery is not None and battery < thresholds["battery_threshold"]:
        deficit = (thresholds["battery_threshold"] - battery) / thresholds["battery_threshold"]
        penalty += min(deficit, 1.0) * WEIGHTS["battery"]

    if not comm_ok:
        penalty += WEIGHTS["comm"]

    return max(0, round(100 - penalty))


def determine_status(strain, tilt, vibration, thresholds) -> str:
    """SAFE / WARNING / CRITICAL based on how far past threshold each metric is."""
    ratios = [
        abs(strain) / thresholds["strain_threshold"] if thresholds["strain_threshold"] else 0,
        abs(tilt) / thresholds["tilt_threshold"] if thresholds["tilt_threshold"] else 0,
        abs(vibration) / thresholds["vibration_threshold"] if thresholds["vibration_threshold"] else 0,
    ]
    worst = max(ratios)
    if worst >= 1.0:
        return "CRITICAL"
    if worst >= 0.7:
        return "WARNING"
    return "SAFE"
