"""Tests for VERA DNS intelligence provider."""

import socket
from uuid import uuid4

import pytest

from app.contracts.status import AnalysisStatus
from app.providers.dns_intelligence import DNSIntelligenceProvider


@pytest.mark.asyncio
async def test_dns_provider_health_check() -> None:
    """Verifies the DNS provider reports system resolver availability."""
    provider = DNSIntelligenceProvider()

    assert provider.provider_name == "dns_intelligence"
    assert provider.is_available is True

    health = await provider.health_check()

    assert health["status"] == AnalysisStatus.SUCCESS.value
    assert health["provider"] == "dns_intelligence"


@pytest.mark.asyncio
async def test_dns_resolves_known_hostname(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verifies successful DNS resolution produces structured addresses."""
    provider = DNSIntelligenceProvider()

    def fake_getaddrinfo(*args: object, **kwargs: object) -> list[tuple]:
        return [
            (
                socket.AF_INET,
                socket.SOCK_STREAM,
                6,
                "",
                ("93.184.216.34", 0),
            ),
            (
                socket.AF_INET6,
                socket.SOCK_STREAM,
                6,
                "",
                ("2001:db8::1", 0, 0, 0),
            ),
        ]

    monkeypatch.setattr(socket, "getaddrinfo", fake_getaddrinfo)

    result = await provider.resolve_domain(
        investigation_id=uuid4(),
        hostname="Example.COM.",
    )

    assert result["status"] == AnalysisStatus.SUCCESS.value
    assert result["hostname"] == "example.com"
    assert result["addresses"] == [
        "2001:db8::1",
        "93.184.216.34",
    ]
    assert result["address_count"] == 2


@pytest.mark.asyncio
async def test_dns_resolution_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    """DNS failure must not fabricate an address or imply safety."""
    provider = DNSIntelligenceProvider()

    def fake_getaddrinfo(*args: object, **kwargs: object) -> list[tuple]:
        raise socket.gaierror("name or service not known")

    monkeypatch.setattr(socket, "getaddrinfo", fake_getaddrinfo)

    result = await provider.resolve_domain(
        investigation_id=uuid4(),
        hostname="does-not-exist.invalid",
    )

    assert result["status"] == AnalysisStatus.FAILED.value
    assert result["addresses"] == []
    assert result["hostname"] == "does-not-exist.invalid"
    assert "DNS resolution failed:" in result["error"]


@pytest.mark.asyncio
async def test_dns_missing_hostname() -> None:
    """Missing hostname must fail without performing DNS resolution."""
    provider = DNSIntelligenceProvider()

    result = await provider.resolve_domain(
        investigation_id=uuid4(),
        hostname="   ",
    )

    assert result["status"] == AnalysisStatus.FAILED.value
    assert result["addresses"] == []
    assert result["error"] == "Hostname is missing."


@pytest.mark.asyncio
async def test_dns_os_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """OS-level DNS failures must be represented as FAILED."""
    provider = DNSIntelligenceProvider()

    def fake_getaddrinfo(*args: object, **kwargs: object) -> list[tuple]:
        raise OSError("resolver unavailable")

    monkeypatch.setattr(socket, "getaddrinfo", fake_getaddrinfo)

    result = await provider.resolve_domain(
        investigation_id=uuid4(),
        hostname="example.com",
    )

    assert result["status"] == AnalysisStatus.FAILED.value
    assert result["addresses"] == []
    assert "DNS resolution failed:" in result["error"]