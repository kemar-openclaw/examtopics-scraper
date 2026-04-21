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

from .models import Answer, Exam, ExamInfo, Question, QuestionType, ScrapingSession, VendorInfo
from .settings import ExamTopicsSettings

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)

# Default exam mappings as fallback
DEFAULT_EXAMS = {
    # Google Cloud Professional Certifications
    "professional-cloud-architect": {
        "code": "GCP-PCA",
        "name": "Google Cloud Platform - Professional Cloud Architect",
        "provider": "Google",
        "provider_slug": "google",
        "path": "/exams/google/professional-cloud-architect/",
    },
    "professional-cloud-developer": {
        "code": "GCP-PCD",
        "name": "Google Cloud Platform - Professional Cloud Developer",
        "provider": "Google",
        "provider_slug": "google",
        "path": "/exams/google/professional-cloud-developer/",
    },
    "associate-cloud-engineer": {
        "code": "GCP-ACE",
        "name": "Google Cloud Platform - Associate Cloud Engineer",
        "provider": "Google",
        "provider_slug": "google",
        "path": "/exams/google/associate-cloud-engineer/",
    },
    "professional-data-engineer": {
        "code": "GCP-PDE",
        "name": "Google Cloud Platform - Professional Data Engineer",
        "provider": "Google",
        "provider_slug": "google",
        "path": "/exams/google/professional-data-engineer/",
    },
    "professional-cloud-security-engineer": {
        "code": "GCP-PSE",
        "name": "Google Cloud Platform - Professional Cloud Security Engineer",
        "provider": "Google",
        "provider_slug": "google",
        "path": "/exams/google/professional-cloud-security-engineer/",
    },
    "professional-cloud-network-engineer": {
        "code": "GCP-PNE",
        "name": "Google Cloud Platform - Professional Cloud Network Engineer",
        "provider": "Google",
        "provider_slug": "google",
        "path": "/exams/google/professional-cloud-network-engineer/",
    },
    "professional-cloud-devops-engineer": {
        "code": "GCP-PDOE",
        "name": "Google Cloud Platform - Professional Cloud DevOps Engineer",
        "provider": "Google",
        "provider_slug": "google",
        "path": "/exams/google/professional-cloud-devops-engineer/",
    },
    "professional-cloud-database-engineer": {
        "code": "GCP-PDBE",
        "name": "Google Cloud Platform - Professional Cloud Database Engineer",
        "provider": "Google",
        "provider_slug": "google",
        "path": "/exams/google/professional-cloud-database-engineer/",
    },
    "professional-security-operations-engineer": {
        "code": "GCP-PSOE",
        "name": "Google Cloud Platform - Professional Security Operations Engineer",
        "provider": "Google",
        "provider_slug": "google",
        "path": "/exams/google/professional-security-operations-engineer/",
    },
    "cloud-digital-leader": {
        "code": "GCP-CDL",
        "name": "Google Cloud Platform - Cloud Digital Leader",
        "provider": "Google",
        "provider_slug": "google",
        "path": "/exams/google/cloud-digital-leader/",
    },
    # Legacy aliases for backward compatibility
    "gcp-pca": {
        "code": "GCP-PCA",
        "name": "Google Cloud Platform - Professional Cloud Architect",
        "provider": "Google",
        "provider_slug": "google",
        "path": "/exams/google/professional-cloud-architect/",
    },
    "gcp-pcd": {
        "code": "GCP-PCD",
        "name": "Google Cloud Platform - Professional Cloud Developer",
        "provider": "Google",
        "provider_slug": "google",
        "path": "/exams/google/professional-cloud-developer/",
    },
    "gcp-ace": {
        "code": "GCP-ACE",
        "name": "Google Cloud Platform - Associate Cloud Engineer",
        "provider": "Google",
        "provider_slug": "google",
        "path": "/exams/google/associate-cloud-engineer/",
    },
    "gcp-pde": {
        "code": "GCP-PDE",
        "name": "Google Cloud Platform - Professional Data Engineer",
        "provider": "Google",
        "provider_slug": "google",
        "path": "/exams/google/professional-data-engineer/",
    },
    "gcp-pse": {
        "code": "GCP-PSE",
        "name": "Google Cloud Platform - Professional Cloud Security Engineer",
        "provider": "Google",
        "provider_slug": "google",
        "path": "/exams/google/professional-cloud-security-engineer/",
    },
    "gcp-pne": {
        "code": "GCP-PNE",
        "name": "Google Cloud Platform - Professional Cloud Network Engineer",
        "provider": "Google",
        "provider_slug": "google",
        "path": "/exams/google/professional-cloud-network-engineer/",
    },
    # AWS Exams
    "aws-saa-c03": {
        "code": "AWS-SAA-C03",
        "name": "AWS Certified Solutions Architect - Associate",
        "provider": "Amazon",
        "provider_slug": "amazon",
        "path": "/exams/amazon/aws-saa-c03/",
    },
    "aws-sap-c02": {
        "code": "AWS-SAP-C02",
        "name": "AWS Certified Solutions Architect - Professional",
        "provider": "Amazon",
        "provider_slug": "amazon",
        "path": "/exams/amazon/aws-sap-c02/",
    },
    "aws-dva-c02": {
        "code": "AWS-DVA-C02",
        "name": "AWS Certified Developer - Associate",
        "provider": "Amazon",
        "provider_slug": "amazon",
        "path": "/exams/amazon/aws-dva-c02/",
    },
    "aws-soa-c02": {
        "code": "AWS-SOA-C02",
        "name": "AWS Certified SysOps Administrator - Associate",
        "provider": "Amazon",
        "provider_slug": "amazon",
        "path": "/exams/amazon/aws-soa-c02/",
    },
    "aws-cli": {
        "code": "AWS-CLI",
        "name": "AWS Certified Cloud Practitioner",
        "provider": "Amazon",
        "provider_slug": "amazon",
        "path": "/exams/amazon/aws-cli/",
    },
    "azure-az-900": {
        "code": "AZ-900",
        "name": "Microsoft Azure Fundamentals",
        "provider": "Microsoft",
        "provider_slug": "microsoft",
        "path": "/exams/microsoft/azure-az-900/",
    },
    "azure-az-104": {
        "code": "AZ-104",
        "name": "Microsoft Azure Administrator",
        "provider": "Microsoft",
        "provider_slug": "microsoft",
        "path": "/exams/microsoft/azure-az-104/",
    },
    "azure-az-305": {
        "code": "AZ-305",
        "name": "Microsoft Azure Solutions Architect",
        "provider": "Microsoft",
        "provider_slug": "microsoft",
        "path": "/exams/microsoft/azure-az-305/",
    },
    "azure-az-204": {
        "code": "AZ-204",
        "name": "Microsoft Azure Developer",
        "provider": "Microsoft",
        "provider_slug": "microsoft",
        "path": "/exams/microsoft/azure-az-204/",
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
    - Dynamic vendor/exam discovery
    """

    def __init__(self, settings: ExamTopicsSettings | None = None) -> None:
        self.settings = settings or ExamTopicsSettings()
        self.ua = UserAgent() if self.settings.rotate_user_agents else None
        self.session: ScrapingSession | None = None
        self._exams_cache: dict[str, ExamInfo] | None = None
        self._vendors_cache: list[VendorInfo] | None = None

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
        self.settings.cache_dir.mkdir(parents=True, exist_ok=True)
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

    async def discover_vendors(self, use_cache: bool = True) -> list[VendorInfo]:
        """Discover all certification vendors from the website.

        Args:
            use_cache: Whether to use cached data.

        Returns:
            List of VendorInfo objects.
        """
        if self._vendors_cache:
            return self._vendors_cache

        url = f"{self.settings.base_url}/exams/"

        if use_cache:
            cached = await self._load_from_cache(url)
            if cached:
                vendors = self._parse_vendors_page(cached)
                if vendors:
                    self._vendors_cache = vendors
                    return vendors

        logger.info("Discovering vendors from %s", url)

        async with async_playwright() as p:
            browser, context = await self._create_browser_context(p)
            page = await context.new_page()

            try:
                await page.goto(url, wait_until="networkidle", timeout=30000)
                await self._random_delay()
                await self._scroll_page(page)

                content = await page.content()
                await self._save_to_cache(url, content)

                vendors = self._parse_vendors_page(content)
                self._vendors_cache = vendors
                return vendors

            except Exception as e:
                logger.error("Failed to discover vendors: %s", e)
                return []
            finally:
                await context.close()
                await browser.close()

    def _parse_vendors_page(self, html: str) -> list[VendorInfo]:
        """Parse vendor list from HTML."""
        vendors = []

        # Pattern 1: Vendor cards with links
        pattern = r'<a[^>]*href="/exams/([^/]+)/"[^>]*>.*?<h[^>]*>(.*?)</h[^>]*>.*?</a>'
        matches = re.findall(pattern, html, re.DOTALL | re.IGNORECASE)

        for slug, name in matches:
            name = self._clean_html(name)
            if name and slug:
                vendors.append(VendorInfo(
                    slug=slug.lower(),
                    name=name.strip(),
                    url=f"{self.settings.base_url}/exams/{slug}/",
                ))

        # Pattern 2: Alternative vendor list format
        if not vendors:
            pattern = r'href="/exams/([^/]+)/"[^>]*>([^<]+)<'
            matches = re.findall(pattern, html, re.IGNORECASE)
            seen = set()
            for slug, name in matches:
                slug = slug.lower()
                if slug not in seen and name.strip():
                    seen.add(slug)
                    vendors.append(VendorInfo(
                        slug=slug,
                        name=name.strip(),
                        url=f"{self.settings.base_url}/exams/{slug}/",
                    ))

        return vendors

    async def discover_exams(self, vendor_slug: str | None = None, use_cache: bool = True) -> list[ExamInfo]:
        """Discover all exams, optionally filtered by vendor.

        Args:
            vendor_slug: Optional vendor slug to filter by (e.g., "amazon").
            use_cache: Whether to use cached data.

        Returns:
            List of ExamInfo objects.
        """
        if vendor_slug:
            return await self._discover_vendor_exams(vendor_slug, use_cache)

        # Discover all exams from all vendors
        vendors = await self.discover_vendors(use_cache)
        all_exams = []

        for vendor in vendors:
            try:
                vendor_exams = await self._discover_vendor_exams(vendor.slug, use_cache)
                all_exams.extend(vendor_exams)
                await self._random_delay()
            except Exception as e:
                logger.warning("Failed to discover exams for %s: %s", vendor.slug, e)

        return all_exams

    async def _discover_vendor_exams(self, vendor_slug: str, use_cache: bool = True) -> list[ExamInfo]:
        """Discover exams for a specific vendor."""
        url = f"{self.settings.base_url}/exams/{vendor_slug}/"

        if use_cache:
            cached = await self._load_from_cache(url)
            if cached:
                exams = self._parse_exams_page(cached, vendor_slug)
                if exams:
                    return exams

        logger.info("Discovering exams for vendor: %s", vendor_slug)

        async with async_playwright() as p:
            browser, context = await self._create_browser_context(p)
            page = await context.new_page()

            try:
                await page.goto(url, wait_until="networkidle", timeout=30000)
                await self._random_delay()
                await self._scroll_page(page)

                content = await page.content()
                await self._save_to_cache(url, content)

                return self._parse_exams_page(content, vendor_slug)

            except Exception as e:
                logger.error("Failed to discover exams for %s: %s", vendor_slug, e)
                return []
            finally:
                await context.close()
                await browser.close()

    def _parse_exams_page(self, html: str, vendor_slug: str) -> list[ExamInfo]:
        """Parse exam list from vendor page HTML."""
        exams = []
        vendor_name = vendor_slug.title()

        # Try multiple patterns for exam links
        patterns = [
            # Pattern 1: Exam cards with exam-code class
            r'<a[^>]*href="/exams/[^/]+/([^/]+)/"[^>]*class="[^"]*exam[^"]*"[^>]*>.*?<h[^>]*>(.*?)</h[^>]*>.*?</a>',
            # Pattern 2: Simple exam links
            r'href="/exams/[^/]+/([^/]+)/"[^>]*>([^<]+)</a>',
            # Pattern 3: Exam list items
            r'<li[^>]*>.*?<a[^>]*href="/exams/[^/]+/([^/]+)/"[^>]*>(.*?)</a>.*?</li>',
        ]

        seen = set()
        for pattern in patterns:
            matches = re.findall(pattern, html, re.DOTALL | re.IGNORECASE)
            for exam_slug, name in matches:
                exam_slug = exam_slug.lower()
                if exam_slug in seen or not name.strip():
                    continue
                seen.add(exam_slug)

                name = self._clean_html(name).strip()
                code = self._extract_exam_code(name, exam_slug)

                exams.append(ExamInfo(
                    slug=exam_slug,
                    code=code,
                    name=name,
                    provider=vendor_name,
                    provider_slug=vendor_slug.lower(),
                    path=f"/exams/{vendor_slug}/{exam_slug}/",
                ))

        return exams

    def _extract_exam_code(self, name: str, slug: str) -> str:
        """Extract exam code from name or slug."""
        # Try to extract code from name (e.g., "AWS SAA-C03: Solutions Architect")
        code_match = re.search(r'([A-Z]{2,}-[A-Z0-9]+(?:-[A-Z0-9]+)?)', name)
        if code_match:
            return code_match.group(1).upper()

        # Use slug as fallback, formatted
        return slug.upper().replace("-", " ")

    @retry(
        retry=retry_if_exception_type((PlaywrightTimeout, Exception)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=2, min=5, max=30),
        reraise=True,
    )
    async def scrape_page(
        self,
        exam_slug: str,
        page_num: int,
        use_cache: bool = True,
    ) -> list[Question]:
        """Scrape a single page of exam questions.

        Args:
            exam_slug: Exam slug (e.g., "gcp-pca", "aws-saa-c03").
            page_num: Page number to scrape.
            use_cache: Whether to use cached data.

        Returns:
            List of Question objects.
        """
        # Get exam info
        exam_info = await self._get_exam_info(exam_slug)
        if not exam_info:
            raise ValueError(f"Unknown exam: {exam_slug}")

        url = f"{self.settings.base_url}{exam_info.path}{page_num}/"

        # Check cache
        if use_cache:
            cached = await self._load_from_cache(url)
            if cached:
                logger.info("Using cached content for %s", url)
                return self._parse_questions(cached, exam_info.code, page_num)

        logger.info("Scraping page %d from %s", page_num, url)

        async with async_playwright() as p:
            browser, context = await self._create_browser_context(p)
            page = await context.new_page()

            try:
                await page.goto(url, wait_until="networkidle", timeout=30000)
                await self._random_delay()

                await page.wait_for_selector(
                    ".exam-question-card, .question-card, [data-testid*='question']",
                    timeout=15000,
                )

                await self._scroll_page(page)

                content = await page.content()
                await self._save_to_cache(url, content)

                questions = self._parse_questions(content, exam_info.code, page_num)

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

    async def _get_exam_info(self, exam_slug: str) -> ExamInfo | None:
        """Get exam info by slug."""
        if self._exams_cache is None:
            self._exams_cache = {}
            # Try to discover from default mapping first
            for slug, info in DEFAULT_EXAMS.items():
                self._exams_cache[slug] = ExamInfo(
                    slug=slug,
                    code=info["code"],
                    name=info["name"],
                    provider=info["provider"],
                    provider_slug=info["provider_slug"],
                    path=info["path"],
                )

        if exam_slug in self._exams_cache:
            return self._exams_cache[exam_slug]

        # Try to discover it
        for vendor_slug in ["google", "amazon", "microsoft", "comptia", "cisco"]:
            exams = await self._discover_vendor_exams(vendor_slug)
            for exam in exams:
                self._exams_cache[exam.slug] = exam
                if exam.slug == exam_slug:
                    return exam

        return None

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
        patterns = [
            r'<div[^>]*class=["\'][^"\']*exam-question-card[^"\']*["\'][^>]*>.*?</div>\s*(?=<div[^>]*class=["\'][^"\']*exam-question-card|$)',
            r'<div[^>]*class=["\'][^"\']*question-card[^"\']*["\'][^>]*>.*?</div>\s*(?=<div[^>]*class=["\'][^"\']*question-card|$)',
            r'<article[^>]*>.*?</article>',
        ]

        for pattern in patterns:
            matches = re.findall(pattern, html, re.DOTALL | re.IGNORECASE)
            if matches:
                return matches

        return re.split(r'(?=<div[^>]*>\s*<h\d>\s*Question\s*\d+)', html)[1:]

    def _parse_single_question(
        self, html: str, exam_code: str, page_num: int, idx: int
    ) -> Question | None:
        """Parse a single question from HTML block."""
        num_match = re.search(r'Question\s*(\d+)', html, re.IGNORECASE)
        question_number = int(num_match.group(1)) if num_match else idx

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

        answers = self._extract_answers(html)
        correct_count = sum(1 for a in answers if a.is_correct)
        question_type = (
            QuestionType.MULTIPLE_CHOICE if correct_count > 1 else QuestionType.SINGLE_CHOICE
        )

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
        text = re.sub(r'<[^>]+>', ' ', html)
        text = ' '.join(text.split())
        text = text.replace('&nbsp;', ' ')
        text = text.replace('&lt;', '<')
        text = text.replace('&gt;', '>')
        text = text.replace('&amp;', '&')
        return text.strip()

    async def scrape_exam(
        self,
        exam_slug: str,
        max_pages: int | None = None,
        use_cache: bool = True,
    ) -> Exam:
        """Scrape entire exam with all pages.

        Args:
            exam_slug: Exam slug (e.g., "gcp-pca", "aws-saa-c03").
            max_pages: Maximum pages to scrape.
            use_cache: Whether to use cached data.

        Returns:
            Exam object with all questions.
        """
        exam_info = await self._get_exam_info(exam_slug)
        if not exam_info:
            raise ValueError(f"Unknown exam: {exam_slug}")

        self.session = ScrapingSession(exam_code=exam_info.code)
        max_pages = max_pages or self.settings.max_pages or 100

        exam = Exam(
            code=exam_info.code,
            name=exam_info.name,
            provider=exam_info.provider,
            url=f"{self.settings.base_url}{exam_info.path}",
        )

        try:
            for page_num in range(1, max_pages + 1):
                questions = await self.scrape_page(exam_slug, page_num, use_cache)

                if not questions:
                    logger.info("No more questions on page %d, stopping", page_num)
                    break

                exam.questions.extend(questions)

                if self.settings.max_questions and len(exam.questions) >= self.settings.max_questions:
                    exam.questions = exam.questions[: self.settings.max_questions]
                    break

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

    async def scrape_all_exams(
        self,
        vendor_slug: str | None = None,
        max_pages_per_exam: int | None = None,
        use_cache: bool = True,
    ) -> list[Exam]:
        """Scrape all available exams.

        Args:
            vendor_slug: Optional vendor to limit scraping.
            max_pages_per_exam: Max pages per exam.
            use_cache: Use cached data.

        Returns:
            List of Exam objects.
        """
        exams_info = await self.discover_exams(vendor_slug, use_cache)
        results = []

        for exam_info in exams_info:
            try:
                logger.info("Scraping exam: %s - %s", exam_info.code, exam_info.name)
                exam = await self.scrape_exam(
                    exam_info.slug,
                    max_pages=max_pages_per_exam,
                    use_cache=use_cache,
                )
                results.append(exam)
            except Exception as e:
                logger.error("Failed to scrape %s: %s", exam_info.slug, e)

        return results

    def get_available_exams(self) -> dict[str, ExamInfo]:
        """Get list of available exams from default mapping."""
        if self._exams_cache is None:
            self._exams_cache = {}
            for slug, info in DEFAULT_EXAMS.items():
                self._exams_cache[slug] = ExamInfo(
                    slug=slug,
                    code=info["code"],
                    name=info["name"],
                    provider=info["provider"],
                    provider_slug=info["provider_slug"],
                    path=info["path"],
                )
        return self._exams_cache.copy()
