"""Test fixtures for examtopics-scraper."""

from __future__ import annotations

import pytest

from examtopics_scraper.models import (
    Answer,
    Exam,
    Question,
    QuestionType,
    ScrapingSession,
)
from examtopics_scraper.settings import ExamTopicsSettings


@pytest.fixture
def settings() -> ExamTopicsSettings:
    """Default test settings."""
    return ExamTopicsSettings(
        headless=True,
        request_delay_min=0.1,
        request_delay_max=0.2,
        max_retries=1,
    )


@pytest.fixture
def sample_question() -> Question:
    """Sample exam question."""
    return Question(
        id="abc123def456",
        number=1,
        text="What is the primary purpose of Google Cloud IAM?",
        question_type=QuestionType.SINGLE_CHOICE,
        answers=[
            Answer(letter="A", text="Manage billing", is_correct=False),
            Answer(letter="B", text="Control access to resources", is_correct=True),
            Answer(letter="C", text="Monitor performance", is_correct=False),
            Answer(letter="D", text="Deploy applications", is_correct=False),
        ],
        explanation="IAM (Identity and Access Management) is used to control access to resources.",
        exam_code="GCP-PCA",
        page_number=1,
        votes=42,
    )


@pytest.fixture
def sample_exam() -> Exam:
    """Sample exam with multiple questions."""
    return Exam(
        code="GCP-PCA",
        name="Google Cloud Professional Cloud Architect",
        provider="Google",
        url="https://www.examtopics.com/exams/google/gcp-pca/",
        question_count=2,
        questions=[
            Question(
                id="q1abc123",
                number=1,
                text="What is Cloud IAM?",
                question_type=QuestionType.SINGLE_CHOICE,
                answers=[
                    Answer(letter="A", text="Identity management", is_correct=True),
                    Answer(letter="B", text="Network tool", is_correct=False),
                ],
                exam_code="GCP-PCA",
                page_number=1,
            ),
            Question(
                id="q2def456",
                number=2,
                text="Which storage is best for unstructured data?",
                question_type=QuestionType.SINGLE_CHOICE,
                answers=[
                    Answer(letter="A", text="Cloud SQL", is_correct=False),
                    Answer(letter="B", text="Cloud Storage", is_correct=True),
                ],
                exam_code="GCP-PCA",
                page_number=1,
            ),
        ],
    )


@pytest.fixture
def sample_session() -> ScrapingSession:
    """Sample scraping session."""
    return ScrapingSession(
        exam_code="GCP-PCA",
        pages_scraped=5,
        questions_found=50,
    )


@pytest.fixture
def mock_html_content() -> dict[str, str]:
    """Mock HTML content for testing."""
    return {
        "exam_page": """
        <html>
        <body>
            <div class="exam-question-card">
                <h3>Question 1</h3>
                <p class="question-text">What is the purpose of IAM?</p>
                <div class="answer">A. Manage billing</div>
                <div class="answer correct">B. Control access</div>
                <div class="answer">C. Monitor performance</div>
                <div class="explanation">IAM controls access to resources.</div>
            </div>
            <div class="exam-question-card">
                <h3>Question 2</h3>
                <p class="question-text">Which is a compute service?</p>
                <div class="answer">A. Cloud Storage</div>
                <div class="answer correct">B. Compute Engine</div>
            </div>
        </body>
        </html>
        """,
        "empty_page": """
        <html>
        <body>
            <p>No questions found</p>
        </body>
        </html>
        """,
        "question_card": """
        <div class="exam-question-card">
            <h3>Question 5</h3>
            <p class="question-text">Best practice for security?</p>
            <div class="answer" data-correct="true">A. Principle of least privilege</div>
            <div class="answer">B. Share credentials</div>
            <div class="explanation">Least privilege minimizes attack surface.</div>
        </div>
        """,
    }
