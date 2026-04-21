"""Unit tests for settings configuration."""

from __future__ import annotations

from pathlib import Path

import pytest

from examtopics_scraper.settings import ExamTopicsSettings


class TestExamTopicsSettings:
    """Tests for ExamTopicsSettings configuration."""

    def test_default_values(self) -> None:
        """Settings should have sensible defaults."""
        s = ExamTopicsSettings()

        assert s.headless is True
        assert s.base_url == "https://www.examtopics.com"
        assert s.output_dir == Path("./output")
        assert s.cache_dir == Path("./.cache")
        assert s.request_delay_min == 2.0
        assert s.request_delay_max == 5.0
        assert s.max_retries == 3
        assert s.use_stealth is True
        assert s.rotate_user_agents is True
        assert s.use_proxy is False
        assert s.timeout == 30

    def test_explicit_values(self) -> None:
        """Settings should accept explicit values."""
        s = ExamTopicsSettings(
            headless=False,
            base_url="https://test.example.com",
            request_delay_min=1.0,
            request_delay_max=3.0,
            max_retries=5,
            use_stealth=False,
            rotate_user_agents=False,
            use_proxy=True,
            proxy_url="http://proxy:8080",
        )

        assert s.headless is False
        assert s.base_url == "https://test.example.com"
        assert s.request_delay_min == 1.0
        assert s.request_delay_max == 3.0
        assert s.max_retries == 5
        assert s.use_stealth is False
        assert s.rotate_user_agents is False
        assert s.use_proxy is True
        assert s.proxy_url == "http://proxy:8080"

    def test_delay_range_validation(self) -> None:
        """Test delay min/max relationship."""
        s = ExamTopicsSettings(
            request_delay_min=5.0,
            request_delay_max=10.0,
        )

        assert s.request_delay_min < s.request_delay_max

    def test_proxy_config_when_disabled(self) -> None:
        """Proxy config should be None when disabled."""
        s = ExamTopicsSettings(use_proxy=False, proxy_url="http://proxy:8080")
        assert s.proxy_config is None

    def test_proxy_config_when_enabled(self) -> None:
        """Proxy config should be returned when enabled."""
        s = ExamTopicsSettings(
            use_proxy=True,
            proxy_url="http://user:pass@proxy:8080"
        )
        assert s.proxy_config == {"server": "http://user:pass@proxy:8080"}

    def test_proxy_config_empty_url(self) -> None:
        """Proxy config should be None when URL is empty."""
        s = ExamTopicsSettings(use_proxy=True, proxy_url="")
        assert s.proxy_config is None

    def test_env_prefix_loading(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Settings should load from EXAMTOPICS_ prefixed env vars."""
        monkeypatch.setenv("EXAMTOPICS_HEADLESS", "false")
        monkeypatch.setenv("EXAMTOPICS_MAX_RETRIES", "10")
        monkeypatch.setenv("EXAMTOPICS_USE_STEALTH", "false")

        s = ExamTopicsSettings()
        assert s.headless is False
        assert s.max_retries == 10
        assert s.use_stealth is False

    def test_settings_with_dotenv_file(self, tmp_path: Path) -> None:
        """Settings should load from .env file."""
        env_file = tmp_path / ".env"
        env_file.write_text("""
EXAMTOPICS_HEADLESS=false
EXAMTOPICS_REQUEST_DELAY_MIN=1.5
EXAMTOPICS_MAX_PAGES=50
""")

        s = ExamTopicsSettings(_env_file=str(env_file))
        assert s.headless is False
        assert s.request_delay_min == 1.5
        assert s.max_pages == 50

    def test_max_pages_zero_means_unlimited(self) -> None:
        """max_pages=0 should mean unlimited."""
        s = ExamTopicsSettings(max_pages=0)
        assert s.max_pages == 0

    def test_max_questions_zero_means_unlimited(self) -> None:
        """max_questions=0 should mean unlimited."""
        s = ExamTopicsSettings(max_questions=0)
        assert s.max_questions == 0

    def test_retry_configuration(self) -> None:
        """Test retry-related settings."""
        s = ExamTopicsSettings(
            max_retries=5,
            retry_delay=10.0,
            retry_multiplier=3.0,
        )

        assert s.max_retries == 5
        assert s.retry_delay == 10.0
        assert s.retry_multiplier == 3.0

    def test_directories_as_path_objects(self) -> None:
        """Directory settings should be Path objects."""
        s = ExamTopicsSettings(
            output_dir="/custom/output",
            cache_dir="/custom/cache",
            user_data_dir="/custom/browser",
        )

        assert isinstance(s.output_dir, Path)
        assert isinstance(s.cache_dir, Path)
        assert isinstance(s.user_data_dir, Path)
