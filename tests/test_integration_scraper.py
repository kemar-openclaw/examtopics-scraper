"""Integration tests for Exam Topics scraper."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from examtopics_scraper.models import Answer, Exam, Question, QuestionType
from examtopics_scraper.scraper import ExamTopicsScraper
from examtopics_scraper.settings import ExamTopicsSettings


class TestExamTopicsScraperIntegration:
    """Integration tests for scraper functionality."""

    @pytest.mark.asyncio
    async def test_get_available_exams(self) -> None:
        """Test getting list of available exams."""
        scraper = ExamTopicsScraper()
        exams = scraper.get_available_exams()

        assert "gcp-pca" in exams
        assert "gcp-ace" in exams
        assert exams["gcp-pca"]["provider"] == "Google"
        assert "name" in exams["gcp-pca"]

    @pytest.mark.asyncio
    async def test_clean_html(self) -> None:
        """Test HTML cleaning functionality."""
        scraper = ExamTopicsScraper()

        html = "<p>Test <strong>content</strong> with <br/>tags</p>"
        result = scraper._clean_html(html)

        assert "Test" in result
        assert "content" in result
        assert "<p>" not in result
        assert "<strong>" not in result

    @pytest.mark.asyncio
    async def test_clean_html_with_entities(self) -> None:
        """Test HTML entities are decoded."""
        scraper = ExamTopicsScraper()

        html = "Test &amp; example &lt;tag&gt;"
        result = scraper._clean_html(html)

        assert "&" in result
        assert "<tag>" in result
        assert "&amp;" not in result

    @pytest.mark.asyncio
    async def test_extract_question_blocks(self) -> None:
        """Test extraction of question blocks from HTML."""
        scraper = ExamTopicsScraper()

        html = """
        <div class="exam-question-card">Question 1 content</div>
        <div class="exam-question-card">Question 2 content</div>
        """
        blocks = scraper._extract_question_blocks(html)

        assert len(blocks) == 2
        assert "Question 1" in blocks[0]
        assert "Question 2" in blocks[1]

    @pytest.mark.asyncio
    async def test_extract_question_blocks_empty(self) -> None:
        """Test extraction with no question blocks."""
        scraper = ExamTopicsScraper()

        html = "<html><body>No questions here</body></html>"
        blocks = scraper._extract_question_blocks(html)

        # Should return list with fallback split
        assert isinstance(blocks, list)

    @pytest.mark.asyncio
    async def test_parse_single_question(self, settings: ExamTopicsSettings) -> None:
        """Test parsing a single question."""
        scraper = ExamTopicsScraper(settings)

        html = """
        <div class="exam-question-card">
            <h3>Question 10</h3>
            <p class="question-text">What is Cloud IAM used for?</p>
            <div class="answer">A. Billing management</div>
            <div class="answer correct">B. Access control</div>
            <div class="answer">C. Network monitoring</div>
            <div class="explanation">IAM manages access to GCP resources.</div>
        </div>
        """
        question = scraper._parse_single_question(html, "GCP-PCA", 1, 10)

        assert question is not None
        assert question.number == 10
        assert "Cloud IAM" in question.text
        assert question.exam_code == "GCP-PCA"
        assert len(question.answers) == 3
        assert question.explanation is not None

    @pytest.mark.asyncio
    async def test_parse_single_question_no_title(self, settings: ExamTopicsSettings) -> None:
        """Test parsing question without clear title."""
        scraper = ExamTopicsScraper(settings)

        html = """
        <div>
            <p>Some text without question structure</p>
        </div>
        """
        question = scraper._parse_single_question(html, "GCP-PCA", 1, 1)

        # Should still create question with extracted or default text
        assert question is not None
        # The text may be extracted from the HTML or default to "Unknown question"
        assert len(question.text) > 0

    @pytest.mark.asyncio
    async def test_extract_answers(self, settings: ExamTopicsSettings) -> None:
        """Test extracting answer options."""
        scraper = ExamTopicsScraper(settings)

        html = """
        <div class="answer">A. First option</div>
        <div class="answer correct">B. Second option</div>
        <div class="answer">C. Third option</div>
        """
        answers = scraper._extract_answers(html)

        assert len(answers) == 3
        assert answers[0].letter == "A"
        assert answers[1].letter == "B"
        assert answers[1].is_correct is True
        assert answers[2].text == "Third option"

    @pytest.mark.asyncio
    async def test_is_correct_answer(self, settings: ExamTopicsSettings) -> None:
        """Test detecting correct answers."""
        scraper = ExamTopicsScraper(settings)

        html_correct = '<div class="answer correct">B. Correct answer</div>'
        html_normal = '<div class="answer">A. Wrong answer</div>'

        assert scraper._is_correct_answer(html_correct, "B") is True
        assert scraper._is_correct_answer(html_normal, "A") is False

    @pytest.mark.asyncio
    async def test_extract_explanation(self, settings: ExamTopicsSettings) -> None:
        """Test extracting explanation text."""
        scraper = ExamTopicsScraper(settings)

        html = '<div class="explanation">This is the explanation text.</div>'
        explanation = scraper._extract_explanation(html)

        assert explanation is not None
        assert "explanation text" in explanation

    @pytest.mark.asyncio
    async def test_extract_explanation_not_found(self, settings: ExamTopicsSettings) -> None:
        """Test when explanation is not present."""
        scraper = ExamTopicsScraper(settings)

        html = "<div>No explanation here</div>"
        explanation = scraper._extract_explanation(html)

        assert explanation is None

    @pytest.mark.asyncio
    async def test_generate_id_consistency(self) -> None:
        """Test that question ID generation is deterministic."""
        id1 = Question.generate_id("GCP-PCA", 1, "Test question text")
        id2 = Question.generate_id("GCP-PCA", 1, "Test question text")

        assert id1 == id2
        assert len(id1) == 16

    @pytest.mark.asyncio
    async def test_generate_id_uniqueness(self) -> None:
        """Test that different questions get different IDs."""
        id1 = Question.generate_id("GCP-PCA", 1, "Question one")
        id2 = Question.generate_id("GCP-PCA", 2, "Question two")
        id3 = Question.generate_id("AWS-SAA", 1, "Question one")

        assert id1 != id2
        assert id1 != id3

    @pytest.mark.asyncio
    async def test_cache_operations(self, settings: ExamTopicsSettings, tmp_path: Path) -> None:
        """Test cache save and load operations."""
        settings.cache_dir = tmp_path / ".cache"
        settings.cache_dir.mkdir(parents=True, exist_ok=True)

        scraper = ExamTopicsScraper(settings)
        test_url = "https://example.com/test"
        test_content = "<html><body>Test content</body></html>"

        # Save to cache
        await scraper._save_to_cache(test_url, test_content)

        # Load from cache
        cached = await scraper._load_from_cache(test_url)
        assert cached == test_content

        # Load non-existent
        missing = await scraper._load_from_cache("https://example.com/missing")
        assert missing is None

    @pytest.mark.asyncio
    async def test_random_delay(self, settings: ExamTopicsSettings) -> None:
        """Test random delay respects settings."""
        scraper = ExamTopicsScraper(settings)

        import asyncio
        start = asyncio.get_event_loop().time()
        await scraper._random_delay()
        elapsed = asyncio.get_event_loop().time() - start

        assert elapsed >= settings.request_delay_min
        assert elapsed <= settings.request_delay_max + 0.1  # Small tolerance


class TestExamModel:
    """Tests for Exam model."""

    def test_exam_correct_answer_count(self, sample_exam: Exam) -> None:
        """Test counting questions with correct answers."""
        assert sample_exam.correct_answer_count == 2

        # Add question without correct answer
        sample_exam.questions.append(
            Question(
                id="q3",
                number=3,
                text="Question without correct answer",
                question_type=QuestionType.SINGLE_CHOICE,
                answers=[Answer(letter="A", text="Option", is_correct=False)],
                exam_code="GCP-PCA",
                page_number=1,
            )
        )
        assert sample_exam.correct_answer_count == 2


class TestQuestionModel:
    """Tests for Question model."""

    def test_question_str_representation(self, sample_question: Question) -> None:
        """Test question string representation."""
        str_repr = str(sample_question)
        assert "Q1" in str_repr
        assert "IAM" in str_repr
        assert "✓" in str_repr  # Has correct answer

    def test_question_str_no_correct(self) -> None:
        """Test question without correct answer."""
        question = Question(
            id="test",
            number=1,
            text="Test question",
            question_type=QuestionType.SINGLE_CHOICE,
            answers=[Answer(letter="A", text="Option", is_correct=False)],
            exam_code="TEST",
            page_number=1,
        )
        assert "?" in str(question)
