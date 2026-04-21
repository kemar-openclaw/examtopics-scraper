"""Pydantic Settings for Exam Topics scraper."""

from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class ExamTopicsSettings(BaseSettings):
    """Configuration for the Exam Topics scraper.

    Includes anti-detection settings for resilient scraping.

    Attributes:
        headless: Run browser in headless mode.
        base_url: Base URL for Exam Topics.
        output_dir: Directory for output files.
        cache_dir: Directory for caching scraped pages.
        request_delay_min: Minimum delay between requests (seconds).
        request_delay_max: Maximum delay between requests (seconds).
        max_retries: Maximum retry attempts for failed requests.
        retry_delay: Base delay between retries (seconds).
        use_stealth: Enable stealth mode (anti-detection).
        use_proxy: Whether to use proxy (if configured).
        proxy_url: Proxy URL (http://user:pass@host:port).
        timeout: Page load timeout (seconds).
        user_data_dir: Persistent browser profile directory.
    """

    model_config = SettingsConfigDict(
        env_prefix="EXAMTOPICS_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    headless: bool = True
    base_url: str = "https://www.examtopics.com"
    output_dir: Path = Path("./output")
    cache_dir: Path = Path("./.cache")

    # Rate limiting
    request_delay_min: float = 2.0
    request_delay_max: float = 5.0

    # Retry configuration
    max_retries: int = 3
    retry_delay: float = 5.0
    retry_multiplier: float = 2.0

    # Anti-detection
    use_stealth: bool = True
    rotate_user_agents: bool = True

    # Proxy settings
    use_proxy: bool = False
    proxy_url: str = ""

    # Browser settings
    timeout: int = 30
    user_data_dir: Path = Path("./.browser_data")

    # Scraping limits
    max_pages: int = 0  # 0 = unlimited
    max_questions: int = 0  # 0 = unlimited

    def __post_init__(self) -> None:
        """Ensure directories exist."""
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.user_data_dir.mkdir(parents=True, exist_ok=True)

    @property
    def proxy_config(self) -> dict | None:
        """Get proxy configuration for Playwright."""
        if self.use_proxy and self.proxy_url:
            return {"server": self.proxy_url}
        return None
