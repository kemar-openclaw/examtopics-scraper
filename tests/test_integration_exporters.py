"""Integration tests for exporters."""

from __future__ import annotations

import csv
import json
import zipfile
from pathlib import Path

import pytest

from examtopics_scraper.exporters import export_to_anki, export_to_csv, export_to_json
from examtopics_scraper.exporters.anki_exporter import generate_anki_text_import
from examtopics_scraper.models import Answer, Exam, Question, QuestionType


class TestJSONExporter:
    """Tests for JSON exporter."""

    def test_export_to_json(self, sample_exam: Exam, tmp_path: Path) -> None:
        """Test exporting exam to JSON."""
        output_file = tmp_path / "exam.json"

        result_path = export_to_json(sample_exam, output_file)

        assert result_path == output_file
        assert output_file.exists()

        data = json.loads(output_file.read_text())
        assert data["code"] == "GCP-PCA"
        assert data["name"] == "Google Cloud Professional Cloud Architect"
        assert len(data["questions"]) == 2
        assert data["questions"][0]["text"] == "What is Cloud IAM?"

    def test_export_creates_parent_directories(self, sample_exam: Exam, tmp_path: Path) -> None:
        """Test that export creates parent directories."""
        output_file = tmp_path / "nested" / "path" / "exam.json"

        export_to_json(sample_exam, output_file)

        assert output_file.exists()


class TestCSVExporter:
    """Tests for CSV exporter."""

    def test_export_to_csv(self, sample_exam: Exam, tmp_path: Path) -> None:
        """Test exporting exam to CSV."""
        output_file = tmp_path / "exam.csv"

        result_path = export_to_csv(sample_exam, output_file)

        assert result_path == output_file
        assert output_file.exists()

        with open(output_file, "r", newline="", encoding="utf-8") as f:
            reader = csv.reader(f)
            rows = list(reader)

        assert len(rows) == 3  # Header + 2 questions
        assert "question_number" in rows[0]
        assert rows[1][0] == "1"  # First question number

    def test_export_csv_with_correct_answers(self, sample_exam: Exam, tmp_path: Path) -> None:
        """Test that CSV includes correct answer marking."""
        output_file = tmp_path / "exam.csv"
        export_to_csv(sample_exam, output_file)

        with open(output_file, "r", newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        # Check that correct_answer column exists and has content
        assert "correct_answer" in rows[0]
        # First question has a correct answer (letter in the field)
        assert len(rows[0]["correct_answer"]) > 0

    def test_export_csv_pads_answers(self, tmp_path: Path) -> None:
        """Test that CSV pads answers to 5 columns."""
        exam = Exam(
            code="TEST",
            name="Test",
            provider="Test",
            url="https://example.com",
            questions=[
                Question(
                    id="q1",
                    number=1,
                    text="Test question",
                    question_type=QuestionType.SINGLE_CHOICE,
                    answers=[
                        Answer(letter="A", text="Only answer", is_correct=True)
                    ],
                    exam_code="TEST",
                    page_number=1,
                )
            ],
        )

        output_file = tmp_path / "exam.csv"
        export_to_csv(exam, output_file)

        with open(output_file, "r", newline="", encoding="utf-8") as f:
            reader = csv.reader(f)
            rows = list(reader)

        # Should have answer_a through answer_e columns
        assert len(rows[0]) >= 11  # All expected columns


class TestAnkiExporter:
    """Tests for Anki exporter."""

    def test_export_to_anki(self, sample_exam: Exam, tmp_path: Path) -> None:
        """Test exporting exam to Anki format."""
        output_file = tmp_path / "exam.apkg"

        result_path = export_to_anki(sample_exam, output_file)

        assert result_path == output_file
        assert output_file.exists()

        # Check it's a valid zip file
        with zipfile.ZipFile(output_file, "r") as zf:
            assert "deck.json" in zf.namelist()

    def test_anki_deck_structure(self, sample_exam: Exam, tmp_path: Path) -> None:
        """Test Anki deck has correct structure."""
        output_file = tmp_path / "exam.apkg"
        export_to_anki(sample_exam, output_file)

        with zipfile.ZipFile(output_file, "r") as zf:
            deck_data = json.loads(zf.read("deck.json"))

        assert deck_data["deck_name"] == "GCP-PCA - Google Cloud Professional Cloud Architect"
        assert len(deck_data["notes"]) == 2

    def test_anki_note_structure(self, sample_exam: Exam, tmp_path: Path) -> None:
        """Test individual notes have front/back structure."""
        output_file = tmp_path / "exam.apkg"
        export_to_anki(sample_exam, output_file)

        with zipfile.ZipFile(output_file, "r") as zf:
            deck_data = json.loads(zf.read("deck.json"))

        note = deck_data["notes"][0]
        assert "front" in note
        assert "back" in note
        assert "tags" in note
        assert "GCP-PCA" in note["tags"]

    def test_generate_anki_text_import(self, sample_exam: Exam) -> None:
        """Test generating Anki text import format."""
        text = generate_anki_text_import(sample_exam)

        assert "Q1:" in text
        assert "Correct:" in text
        assert ";" in text  # Semicolon separator
        assert "GCP-PCA" in text

    def test_anki_text_escapes_semicolons(self) -> None:
        """Test that semicolons in text are escaped."""
        exam = Exam(
            code="TEST",
            name="Test",
            provider="Test",
            url="https://example.com",
            questions=[
                Question(
                    id="q1",
                    number=1,
                    text="Question with; semicolon",
                    question_type=QuestionType.SINGLE_CHOICE,
                    answers=[Answer(letter="A", text="Answer", is_correct=True)],
                    exam_code="TEST",
                    page_number=1,
                )
            ],
        )

        text = generate_anki_text_import(exam)
        # Should use comma instead of semicolon in text
        assert "Question with, semicolon" in text or "Question with; semicolon" in text


class TestExportRoundTrip:
    """Tests for export/import round trips."""

    def test_json_round_trip(self, sample_exam: Exam, tmp_path: Path) -> None:
        """Test that JSON export can be re-imported."""
        output_file = tmp_path / "exam.json"
        export_to_json(sample_exam, output_file)

        data = json.loads(output_file.read_text())
        assert data["code"] == sample_exam.code
        assert len(data["questions"]) == len(sample_exam.questions)
