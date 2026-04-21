"""Anki deck exporter for exam questions."""

from __future__ import annotations

import json
import zipfile
from pathlib import Path

from ..models import Exam


def export_to_anki(exam: Exam, output_path: Path) -> Path:
    """Export exam questions to Anki deck format (.apkg).

    Creates a basic Anki package file that can be imported.
    Note: This is a simplified implementation that creates a JSON representation.
    For full APKG support, install python-anki or genanki.

    Args:
        exam: Exam object to export.
        output_path: Path to save APKG file.

    Returns:
        Path to saved file.
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Create a JSON representation that can be imported into Anki
    # In production, use genanki library for proper APKG generation
    deck_data = {
        "deck_name": f"{exam.code} - {exam.name}",
        "notes": [],
    }

    for q in exam.questions:
        # Front: Question text
        front = f"<h3>Question {q.number}</h3>\n<p>{q.text}</p>\n<ul>"
        for ans in q.answers:
            front += f"<li>{ans.letter}. {ans.text}</li>"
        front += "</ul>"

        # Back: Correct answers with explanation
        correct = [a for a in q.answers if a.is_correct]
        back = "<h3>Correct Answer:</h3>\n<ul>"
        for ans in correct:
            back += f"<li><strong>{ans.letter}. {ans.text}</strong></li>"
        back += "</ul>"

        if q.explanation:
            back += f"<h3>Explanation:</h3>\n<p>{q.explanation}</p>"

        deck_data["notes"].append({
            "front": front,
            "back": back,
            "tags": [exam.code, exam.provider, q.question_type.value],
        })

    # For now, save as JSON that can be imported via Anki's import feature
    # A proper APKG requires the genanki library
    json_path = output_path.with_suffix(".json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(deck_data, f, indent=2, ensure_ascii=False)

    # Create a simple zip as placeholder for .apkg
    with zipfile.ZipFile(output_path, "w") as zf:
        zf.writestr("deck.json", json.dumps(deck_data, ensure_ascii=False))

    return output_path


def generate_anki_text_import(exam: Exam) -> str:
    """Generate text format for Anki import.

    Format: question;answer;tags (semicolon-separated)

    Returns:
        String in Anki text import format.
    """
    lines = []

    for q in exam.questions:
        # Question text (front)
        front = f"Q{q.number}: {q.text}\n\n"
        for ans in q.answers:
            front += f"{ans.letter}. {ans.text}\n"

        # Answer (back)
        correct = [a for a in q.answers if a.is_correct]
        back = "Correct: " + ", ".join(a.letter for a in correct)

        if q.explanation:
            back += f"\n\nExplanation: {q.explanation}"

        # Tags
        tags = f"{exam.code}::{q.question_type.value}"

        # Escape semicolons in text
        front = front.replace(";", ",")
        back = back.replace(";", ",")

        lines.append(f"{front};{back};{tags}")

    return "\n".join(lines)
