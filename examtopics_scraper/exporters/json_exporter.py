"""JSON exporter for exam data."""

from __future__ import annotations

import json
from pathlib import Path

from ..models import Exam


def export_to_json(exam: Exam, output_path: Path) -> Path:
    """Export exam to JSON format.

    Args:
        exam: Exam object to export.
        output_path: Path to save JSON file.

    Returns:
        Path to saved file.
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    data = exam.model_dump(mode="json")

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    return output_path
