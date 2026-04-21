"""Resilient scraper for Exam Topics with anti-detection measures."""

from __future__ import annotations

import asyncio
import json
import logging
import random
import re
from pathlib import Path
from typing import TYPE_CHECKING
from urllib.parse import urljoin, urlparse

import aiofiles
from fake_useragent import UserAgent
from playwright.async_api import Page, TimeoutError as PlaywrightTimeout
from playwright.async_api import async_playwright
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from .models import Answer, Exam, Question, QuestionType, ScrapingSession
from .settings import ExamTopicsSettings

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)

# Google Cloud exam mappings
GCP_EXAMS = {
    "gcp-pca": {
        "code": "GCP-PCA",
        "name": "Google Cloud Platform - Professional Cloud Architect",
        "provider": "Google",
        "path": "/exams/google/gcp-pca/",
    },
    "gcp-pcd": {
        "code": "GCP-PCD",
        "name": "Google Cloud Platform - Professional Cloud Developer",
        "provider": "Google",
        "path": "/exams/google/gcp-pcd/",
    },
    "gcp-ace": {
        "code": "GCP-ACE",
        "name": "Google Cloud Platform - Associate Cloud Engineer",
        "provider": "Google",
        "path": "/exams/google/gcp-ace/",
    },
    "gcp-pds": {
        "code": "GCP-PDS",
        "name": "Google Cloud Platform - Professional Data Engineer",
        "provider": "Google",
        "path": "/exams/google/gcp-pde/",
    },
    "gcp-pse": {
        "code": "GCP-PSE",
        "name": "Google Cloud Platform - Professional Security Engineer",
        "provider": "Google",
        "path": "/exams/google/gcp-pse/",
    },
    "gcp-pne": {
        "code": "GCP-PNE",
        "name": "Google Cloud Platform - Professional Network Engineer",
        "provider": "Google",
        "path": "/exams/google/gcp-pne/",
    },
}


class ExamTopicsScraper:
    """Resilient scraper for Exam Topics certification exams.

    Features:
    - Automatic retry with exponential backoff
    - Random delays between requests
    - User agent rotation
    - Stealth mode for anti-detection
    - Disk caching to avoid re-scraping
    - Proxy support
    """

    def __init__(self, settings: ExamTopicsSettings | None = None) -> None:
        self.settings = settings or ExamTopicsSettings()
        self.ua = UserAgent() if self.settings.rotate_user_agents else None
        self.session: ScrapingSession | None = None

    def _get_random_user_agent(self) -> str:
        """Get a random user agent string."""
        if self.ua:
            return self.ua.random
        return (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )

    def _get_cache_path(self, url: str) -> Path:
        """Get cache file path for a URL."""
        url_hash = str(hash(url) % 1000000).zfill(6)
        return self.settings.cache_dir / f"page_{url_hash}.html"

    async def _load_from_cache(self, url: str) -> str | None:
        """Load page content from cache if available."""
        cache_path = self._get_cache_path(url)
        if cache_path.exists():
            async with aiofiles.open(cache_path, "r", encoding="utf-8") as f:
                return await f.read()
        return None

    async def _save_to_cache(self, url: str, content: str) -> None:
        """Save page content to cache."""
        cache_path = self._get_cache_path(url)
        async with aiofiles.open(cache_path, "w", encoding="utf-8") as f:
            await f.write(content)

    async def _random_delay(self) -> None:
        """Wait for a random duration between requests."""
        delay = random.uniform(
            self.settings.request_delay_min,
            self.settings.request_delay_max,
        )
        await asyncio.sleep(delay)

    async def _create_browser_context(self, playwright):
        """Create a browser context with anti-detection settings."""
        browser = await playwright.chromium.launch(
            headless=self.settings.headless,
            proxy=self.settings.proxy_config,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--disable-web-security",
                "--disable-features=IsolateOrigins,site-per-process",
            ],
        )

        context = await browser.new_context(
            user_agent=self._get_random_user_agent(),
            viewport={"width": 1920, "height": 1080},
            locale="en-US",
            timezone_id="America/New_York",
            permissions=["geolocation"],
            geolocation={"latitude": 40.7128, "longitude": -74.0060},
        )

        # Add stealth scripts
        if self.settings.use_stealth:
            await context.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                });
                Object.defineProperty(navigator, 'plugins', {
                    get: () => [1, 2, 3, 4, 5]
                });
                window.chrome = { runtime: {} };
            """)

        return browser, context

    @retry(
        retry=retry_if_exception_type((PlaywrightTimeout, Exception)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=2, min=5, max=30),
        reraise=True,
    )
    async def scrape_page(
        self,
        exam_code: str,
        page_num: int,
        use_cache: bool = True,
    ) -> list[Question]:
        """Scrape a single page of exam questions.

        Args:
            exam_code: Exam code (e.g., "gcp-pca").
            page_num: Page number to scrape.
            use_cache: Whether to use cached data if available.

        Returns:
            List of Question objects.
        """
        exam_info = GCP_EXAMS.get(exam_code)
        if not exam_info:
            raise ValueError(f"Unknown exam code: {exam_code}")

        url = f"{self.settings.base_url}{exam_info['path']}{page_num}/"

        # Check cache first
        if use_cache:
            cached = await self._load_from_cache(url)
            if cached:
                logger.info("Using cached content for %s", url)
                return self._parse_questions(cached, exam_info["code"], page_num)

        logger.info("Scraping page %d from %s", page_num, url)

        async with async_playwright() as p:
            browser, context = await self._create_browser_context(p)
            page = await context.new_page()

            try:
                await page.goto(url, wait_until="networkidle", timeout=30000)
                await self._random_delay()

                # Wait for content to load
                await page.wait_for_selector(
                    ".exam-question-card, .question-card, [data-testid*='question']",
                    timeout=15000,
                )

                # Scroll to load lazy content
                await self._scroll_page(page)

                content = await page.content()
                await self._save_to_cache(url, content)

                questions = self._parse_questions(content, exam_info["code"], page_num)

                if self.session:
                    self.session.pages_scraped += 1
                    self.session.questions_found += len(questions)

                return questions

            except PlaywrightTimeout:
                logger.error("Timeout loading page %s", url)
                raise
            except Exception as e:
                logger.exception("Error scraping page %d", page_num)
                raise
            finally:
                await context.close()
                await browser.close()

    async def _scroll_page(self, page: Page) -> None:
        """Scroll page to load lazy content."""
        for _ in range(3):
            await page.evaluate("window.scrollBy(0, window.innerHeight)")
            await asyncio.sleep(0.5)

    def _parse_questions(
        self, html: str, exam_code: str, page_num: int
    ) -> list[Question]:
        """Parse questions from HTML content."""
        questions = []

        # Use regex patterns to extract questions
        # This is a simplified version - actual implementation would be more robust
        question_blocks = self._extract_question_blocks(html)

        for idx, block in enumerate(question_blocks, start=1):
            try:
                question = self._parse_single_question(
                    block, exam_code, page_num, idx
                )
                if question:
                    questions.append(question)
            except Exception as e:
                logger.warning("Failed to parse question %d: %s", idx, e)

        return questions

    def _extract_question_blocks(self, html: str) -> list[str]:
        """Extract individual question blocks from HTML."""
        # Look for common question container patterns
        patterns = [
            r'<div[^>]*class=["\'][^"\']*exam-question-card[^"\']*["\'][^>]*>.*?</div>\s*(?=<div[^>]*class=["\'][^"\']*exam-question-card|$)',
            r'<div[^>]*class=["\'][^"\']*question-card[^"\']*["\'][^>]*>.*?</div>\s*(?=<div[^>]*class=["\'][^"\']*question-card|$)',
            r'<article[^>]*>.*?</article>',
        ]

        for pattern in patterns:
            matches = re.findall(pattern, html, re.DOTALL | re.IGNORECASE)
            if matches:
                return matches

        # Fallback: split by question number pattern
        return re.split(r'(?=<div[^>]*>\s*<h\d>\s*Question\s*\d+)', html)[1:]

    def _parse_single_question(
        self, html: str, exam_code: str, page_num: int, idx: int
    ) -> Question | None:
        """Parse a single question from HTML block."""
        # Extract question number
        num_match = re.search(r'Question\s*(\d+)', html, re.IGNORECASE)
        question_number = int(num_match.group(1)) if num_match else idx

        # Extract question text
        text_match = re.search(
            r'<p[^>]*class=["\'][^"\']*question-text[^"\']*["\'][^>]*>(.*?)</p>',
            html,
            re.DOTALL | re.IGNORECASE,
        )
        if not text_match:
            text_match = re.search(r'<p[^>]*>(.*?)</p>', html, re.DOTALL)

        question_text = (
            self._clean_html(text_match.group(1)) if text_match else "Unknown question"
        )

        # Extract answers
        answers = self._extract_answers(html)

        # Determine question type
        correct_count = sum(1 for a in answers if a.is_correct)
        question_type = (
            QuestionType.MULTIPLE_CHOICE if correct_count > 1 else QuestionType.SINGLE_CHOICE
        )

        # Extract explanation
        explanation = self._extract_explanation(html)

        question_id = Question.generate_id(exam_code, question_number, question_text)

        return Question(
            id=question_id,
            number=question_number,
            text=question_text,
            question_type=question_type,
            answers=answers,
            explanation=explanation,
            exam_code=exam_code,
            page_number=page_num,
        )

    def _extract_answers(self, html: str) -> list[Answer]:
        """Extract answer options from HTML."""
        answers = []

        # Look for answer patterns
        answer_patterns = [
            r'<div[^>]*class=["\'][^"\']*answer[^"\']*["\'][^>]*>.*?([A-E])\.[\s]*(.*?)</div>',
            r'<li[^>]*>.*?([A-E])\.[\s]*(.*?)</li>',
            r'<label[^>]*>.*?([A-E])\.[\s]*(.*?)</label>',
        ]

        for pattern in answer_patterns:
            matches = re.findall(pattern, html, re.DOTALL | re.IGNORECASE)
            if matches:
                for letter, text in matches:
                    text = self._clean_html(text)
                    is_correct = self._is_correct_answer(html, letter)
                    answers.append(
                        Answer(letter=letter, text=text, is_correct=is_correct)
                    )
                break

        return answers

    def _is_correct_answer(self, html: str, letter: str) -> bool:
        """Determine if an answer is marked as correct."""
        # Look for correct answer indicators
        correct_patterns = [
            rf'class=["\'][^"\']*correct[^"\']*["\'][^>]*>\s*{letter}',
            rf'data-correct=["\']true["\'][^>]*>\s*{letter}',
            rf'<span[^>]*class=["\'][^"\']*correct[^"\']*["\'][^>]*>\s*{letter}',
        ]

        for pattern in correct_patterns:
            if re.search(pattern, html, re.IGNORECASE):
                return True

        return False

    def _extract_explanation(self, html: str) -> str | None:
        """Extract explanation text from HTML."""
        patterns = [
            r'<div[^>]*class=["\'][^"\']*explanation[^"\']*["\'][^>]*>(.*?)</div>',
            r'<p[^>]*class=["\'][^"\']*explanation[^"\']*["\'][^>]*>(.*?)</p>',
        ]

        for pattern in patterns:
            match = re.search(pattern, html, re.DOTALL | re.IGNORECASE)
            if match:
                return self._clean_html(match.group(1))

        return None

    def _clean_html(self, html: str) -> str:
        """Clean HTML tags and normalize text."""
        # Remove HTML tags
        text = re.sub(r'<[^>]+>', ' ', html)
        # Normalize whitespace
        text = ' '.join(text.split())
        # Decode HTML entities
        text = text.replace('&nbsp;', ' ')
        text = text.replace('&lt;', '<')
        text = text.replace('&gt;', '>')
        text = text.replace('&amp;', '&')
        return text.strip()

    async def scrape_exam(
        self,
        exam_code: str,
        max_pages: int | None = None,
        use_cache: bool = True,
    ) -> Exam:
        """Scrape entire exam with all pages.

        Args:
            exam_code: Exam code (e.g., "gcp-pca").
            max_pages: Maximum pages to scrape (None = unlimited).
            use_cache: Whether to use cached data.

        Returns:
            Exam object with all questions.
        """
        exam_info = GCP_EXAMS.get(exam_code)
        if not exam_info:
            raise ValueError(f"Unknown exam code: {exam_code}")

        self.session = ScrapingSession(exam_code=exam_info["code"])
        max_pages = max_pages or self.settings.max_pages or 100

        exam = Exam(
            code=exam_info["code"],
            name=exam_info["name"],
            provider=exam_info["provider"],
            url=f"{self.settings.base_url}{exam_info['path']}",
        )

        try:
            for page_num in range(1, max_pages + 1):
                questions = await self.scrape_page(exam_code, page_num, use_cache)

                if not questions:
                    logger.info("No more questions on page %d, stopping", page_num)
                    break

                exam.questions.extend(questions)

                if self.settings.max_questions and len(exam.questions) >= self.settings.max_questions:
                    exam.questions = exam.questions[: self.settings.max_questions]
                    break

                # Random delay between pages
                await self._random_delay()

            exam.last_scraped = exam.questions[0].scraped_at if exam.questions else None
            exam.question_count = len(exam.questions)

            if self.session:
                self.session.complete()

        except Exception as e:
            if self.session:
                self.session.fail(str(e))
            raise

        return exam

    def get_available_exams(self) -> dict[str, dict]:
        """Get list of available exams."""
        return GCP_EXAMS.copy()
