"""Confidence calibration metrics for loan review outputs."""

from dataclasses import dataclass

from loan_pipeline.eval.metrics import CaseScore
from loan_pipeline.graph.state import ReviewPacket


@dataclass(frozen=True)
class CalibrationPoint:
    case_id: str
    tier: str
    confidence: float
    correct: bool


def risk_calibration_points(
    packets_by_case: dict[str, ReviewPacket],
    scores: list[CaseScore],
) -> list[CalibrationPoint]:
    points: list[CalibrationPoint] = []
    for score in scores:
        packet = packets_by_case[score.case_id]
        points.append(
            CalibrationPoint(
                case_id=score.case_id,
                tier=score.tier,
                confidence=packet.risk.confidence,
                correct=score.risk_correct,
            )
        )
    return points


def summarize_confidence_calibration(
    points: list[CalibrationPoint],
    bins: tuple[tuple[float, float], ...] = ((0.0, 0.7), (0.7, 0.8), (0.8, 0.9), (0.9, 1.0)),
) -> dict[str, object]:
    if not points:
        return {"cases": 0, "expected_calibration_error": 0.0, "buckets": []}

    buckets = []
    total = len(points)
    expected_calibration_error = 0.0

    for lower, upper in bins:
        bucket_points = [
            point
            for point in points
            if _in_bucket(point.confidence, lower, upper)
        ]
        if not bucket_points:
            continue

        average_confidence = sum(point.confidence for point in bucket_points) / len(bucket_points)
        observed_accuracy = sum(1 for point in bucket_points if point.correct) / len(bucket_points)
        calibration_gap = abs(observed_accuracy - average_confidence)
        expected_calibration_error += (len(bucket_points) / total) * calibration_gap
        buckets.append(
            {
                "confidence_bucket": f"{lower:.1f}-{upper:.1f}",
                "cases": len(bucket_points),
                "average_confidence": round(average_confidence, 4),
                "observed_accuracy": round(observed_accuracy, 4),
                "calibration_gap": round(calibration_gap, 4),
                "case_ids": [point.case_id for point in bucket_points],
            }
        )

    return {
        "cases": total,
        "expected_calibration_error": round(expected_calibration_error, 4),
        "buckets": buckets,
    }


def _in_bucket(confidence: float, lower: float, upper: float) -> bool:
    if upper == 1.0:
        return lower <= confidence <= upper
    return lower <= confidence < upper
