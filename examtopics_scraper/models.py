"""Pydantic data models for Exam Topics scraper."""

from __future__ import annotations

import hashlib
from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, HttpUrl


class QuestionType(str, Enum):
    """Type of exam question."""

    SINGLE_CHOICE = "single_choice"
    MULTIPLE_CHOICE = "multiple_choice"
    UNKNOWN = "unknown"


class Answer(BaseModel):
    """A single answer option for a question."""

    letter: str = Field(description="Answer letter (A, B, C, D, etc.)")
    text: str = Field(description="Answer text content")
    is_correct: bool = Field(
        default=False, description="Whether this is the correct answer"
    )
    explanation: Optional[str] = Field(
        default=None, description="Explanation for this answer"
    )


class Question(BaseModel):
    """A single exam question with answers."""

    id: str = Field(description="Unique identifier (hash of content)")
    number: int = Field(description="Question number in the exam")
    text: str = Field(description="Question text/content")
    question_type: QuestionType = Field(default=QuestionType.UNKNOWN)
    answers: list[Answer] = Field(default_factory=list)
    explanation: Optional[str] = Field(
        default=None, description="General explanation for the question"
    )
    discussion_url: Optional[HttpUrl] = Field(
        default=None, description="URL to discussion page"
    )
    exam_code: str = Field(description="Exam code (e.g., GCP-PCA)")
    page_number: int = Field(description="Page number where found")
    scraped_at: datetime = Field(default_factory=datetime.utcnow)
    votes: int = Field(default=0, description="Number of upvotes/community votes")

    def __str__(self) -> str:
        status = "✓" if any(a.is_correct for a in self.answers) else "?"
        return f"{status} Q{self.number}: {self.text[:80]}..."

    @classmethod
    def generate_id(
        cls, exam_code: str, question_number: int, question_text: str
    ) -> str:
        """Generate a deterministic ID from question content."""
        content = f"{exam_code}:{question_number}:{question_text[:200]}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]


class ExamInfo(BaseModel):
    """Lightweight exam metadata for listing/discovery."""

    slug: str = Field(description="URL slug (e.g., aws-saa-c03)")
    code: str = Field(description="Exam code (e.g., AWS-SAA-C03)")
    name: str = Field(description="Full exam name")
    provider: str = Field(description="Certification provider (Google, Amazon, Microsoft)")
    provider_slug: str = Field(description="URL slug for provider (e.g., amazon)")
    path: str = Field(description="URL path (e.g., /exams/amazon/aws-saa-c03/)")


class VendorInfo(BaseModel):
    """A certification vendor/provider."""

    slug: str = Field(description="URL slug (e.g., amazon)")
    name: str = Field(description="Display name (e.g., Amazon)")
    url: str = Field(description="Full URL to vendor page")
    exam_count: int = Field(default=0, description="Number of exams available")


class Exam(BaseModel):
    """An exam with metadata and questions."""

    code: str = Field(description="Exam code (e.g., GCP-PCA)")
    name: str = Field(description="Full exam name")
    provider: str = Field(description="Certification provider (Google, AWS, Azure)")
    url: HttpUrl = Field(description="Base URL for the exam")
    question_count: Optional[int] = Field(
        default=None, description="Total number of questions"
    )
    last_scraped: Optional[datetime] = Field(default=None)
    questions: list[Question] = Field(default_factory=list)

    @property
    def correct_answer_count(self) -> int:
        """Count questions with identified correct answers."""
        return sum(
            1
            for q in self.questions
            if any(a.is_correct for a in q.answers)
        )


class ScrapingSession(BaseModel):
    """A scraping session with progress tracking."""

    exam_code: str
    started_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    pages_scraped: int = 0
    questions_found: int = 0
    errors: list[str] = Field(default_factory=list)
    status: str = Field(default="running")  # running, completed, failed

    def complete(self) -> None:
        """Mark session as completed."""
        self.completed_at = datetime.utcnow()
        self.status = "completed"

    def fail(self, error: str) -> None:
        """Mark session as failed."""
        self.completed_at = datetime.utcnow()
        self.status = "failed"
        self.errors.append(error)

    @property
    def duration_seconds(self) -> Optional[float]:
        """Get session duration in seconds."""
        if self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None
