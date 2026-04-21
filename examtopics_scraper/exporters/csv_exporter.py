"""CSV exporter for exam questions."""

from __future__ import annotations

import csv
from pathlib import Path

from ..models import Exam


def export_to_csv(exam: Exam, output_path: Path) -> Path:
    """Export exam questions to CSV format.

    Args:
        exam: Exam object to export.
        output_path: Path to save CSV file.

    Returns:
        Path to saved file.
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)

        # Write header
        writer.writerow([
            "question_number",
            "question_text",
            "question_type",
            "answer_a",
            "answer_b",
            "answer_c",
            "answer_d",
            "answer_e",
            "correct_answer",
            "explanation",
            "exam_code",
        ])

        # Write questions
        for q in exam.questions:
            # Pad answers to 5 columns
            answers = [a.text for a in q.answers]
            while len(answers) < 5:
                answers.append("")

            correct = ", ".join(a.letter for a in q.answers if a.is_correct)

            writer.writerow([
                q.number,
                q.text,
                q.question_type.value,
                answers[0],
                answers[1],
                answers[2],
                answers[3],
                answers[4],
                correct,
                q.explanation or "",
                q.exam_code,
            ])

    return output_path
