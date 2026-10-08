"""Tests for the VERA HTTP intelligence provider."""

from unittest.mock import MagicMock
from uuid import uuid4

import httpx
import pytest

from app.contracts.status import AnalysisStatus
from app.providers.http_intelligence import HTTPIntelligenceProvider


@pytest.mark.asyncio
async def test_http_provider_health_check() -> None:
    provider = HTTPIntelligenceProvider()

    result = await provider.health_check()

    assert provider.is_available is True
    assert result["status"] == AnalysisStatus.SUCCESS.value
    assert result["provider"] == "http_intelligence"


@pytest.mark.asyncio
async def test_http_missing_url() -> None:
    provider = HTTPIntelligenceProvider()

    result = await provider.inspect_url(
        investigation_id=uuid4(),
        url="",
    )

    assert result["status"] == AnalysisStatus.FAILED.value
    assert result["error"] == "URL is missing."


@pytest.mark.asyncio
async def test_http_invalid_timeout() -> None:
    provider = HTTPIntelligenceProvider()

    result = await provider.inspect_url(
        investigation_id=uuid4(),
        url="https://example.com",
        timeout_seconds=0,
    )

    assert result["status"] == AnalysisStatus.FAILED.value
    assert result["error"] == "Timeout must be greater than zero."


@pytest.mark.asyncio
async def test_http_invalid_max_redirects() -> None:
    provider = HTTPIntelligenceProvider()

    result = await provider.inspect_url(
        investigation_id=uuid4(),
        url="https://example.com",
        max_redirects=-1,
    )

    assert result["status"] == AnalysisStatus.FAILED.value
    assert result["error"] == "Maximum redirects cannot be negative."


@pytest.mark.asyncio
async def test_http_success_with_mocked_client(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider = HTTPIntelligenceProvider()

    response = MagicMock(spec=httpx.Response)
    response.status_code = 200
    response.url = httpx.URL("https://example.com/login")
    response.history = []
    response.headers = {
        "content-type": "text/html; charset=utf-8",
        "content-length": "1234",
        "server": "example-server",
    }
    response.text = "<html><title>Login Portal</title></html>"

    fake_client = MagicMock()
    fake_client.__enter__.return_value = fake_client
    fake_client.get.return_value = response

    monkeypatch.setattr(
        "app.providers.http_intelligence.httpx.Client",
        lambda **kwargs: fake_client,
    )

    result = await provider.inspect_url(
        investigation_id=uuid4(),
        url="https://example.com/login",
    )

    assert result["status"] == AnalysisStatus.SUCCESS.value
    assert result["status_code"] == 200
    assert result["final_url"] == "https://example.com/login"
    assert result["redirect_count"] == 0
    assert result["content_type"] == "text/html; charset=utf-8"
    assert result["content_length"] == 1234
    assert result["server"] == "example-server"
    assert result["html_title"] == "Login Portal"
    assert result["https_to_http_downgrade"] is False
    assert "html_response" in result["indicators"]


@pytest.mark.asyncio
async def test_http_redirect_chain_and_downgrade(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider = HTTPIntelligenceProvider()

    redirect_one = MagicMock(spec=httpx.Response)
    redirect_one.status_code = 301
    redirect_one.url = httpx.URL("https://example.com/start")
    redirect_one.headers = {
        "location": "http://example.com/final",
    }

    redirect_two = MagicMock(spec=httpx.Response)
    redirect_two.status_code = 302
    redirect_two.url = httpx.URL("http://example.com/intermediate")
    redirect_two.headers = {
        "location": "http://example.com/final",
    }

    response = MagicMock(spec=httpx.Response)
    response.status_code = 200
    response.url = httpx.URL("http://example.com/final")
    response.history = [redirect_one, redirect_two]
    response.headers = {
        "content-type": "text/plain",
    }
    response.text = "final response"

    fake_client = MagicMock()
    fake_client.__enter__.return_value = fake_client
    fake_client.get.return_value = response

    monkeypatch.setattr(
        "app.providers.http_intelligence.httpx.Client",
        lambda **kwargs: fake_client,
    )

    result = await provider.inspect_url(
        investigation_id=uuid4(),
        url="https://example.com/start",
    )

    assert result["status"] == AnalysisStatus.SUCCESS.value
    assert result["redirect_count"] == 2
    assert result["final_url"] == "http://example.com/final"
    assert result["https_to_http_downgrade"] is True
    assert result["redirect_chain"][0]["status_code"] == 301
    assert "https_to_http_downgrade" in result["indicators"]


@pytest.mark.asyncio
async def test_http_timeout_is_fail_safe(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider = HTTPIntelligenceProvider()

    def raise_timeout(
        *args: object,
        **kwargs: object,
    ) -> None:
        raise httpx.TimeoutException("request timed out")

    fake_client = MagicMock()
    fake_client.__enter__.return_value = fake_client
    fake_client.get.side_effect = raise_timeout

    monkeypatch.setattr(
        "app.providers.http_intelligence.httpx.Client",
        lambda **kwargs: fake_client,
    )

    result = await provider.inspect_url(
        investigation_id=uuid4(),
        url="https://example.com",
    )

    assert result["status"] == AnalysisStatus.FAILED.value
    assert "timed out" in result["error"]


def test_http_title_requires_html_content_type() -> None:
    provider = HTTPIntelligenceProvider()

    assert (
        provider._extract_html_title(
            "<title>Example</title>",
            "text/plain",
        )
        is None
    )


def test_http_content_length_parser() -> None:
    provider = HTTPIntelligenceProvider()

    assert provider._parse_content_length("123") == 123
    assert provider._parse_content_length("invalid") is None
    assert provider._parse_content_length(None) is None