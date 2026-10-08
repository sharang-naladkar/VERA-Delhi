"""Tests for the VERA TLS intelligence provider."""

import ssl
from datetime import datetime, timezone
from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from app.contracts.status import AnalysisStatus
from app.providers.tls_intelligence import TLSIntelligenceProvider


@pytest.mark.asyncio
async def test_tls_provider_health_check() -> None:
    provider = TLSIntelligenceProvider()

    result = await provider.health_check()

    assert provider.is_available is True
    assert result["status"] == AnalysisStatus.SUCCESS.value
    assert result["provider"] == "tls_intelligence"


@pytest.mark.asyncio
async def test_tls_missing_hostname() -> None:
    provider = TLSIntelligenceProvider()

    result = await provider.inspect_certificate(
        investigation_id=uuid4(),
        hostname="",
    )

    assert result["status"] == AnalysisStatus.FAILED.value
    assert result["error"] == "Hostname is missing."


@pytest.mark.asyncio
async def test_tls_invalid_port() -> None:
    provider = TLSIntelligenceProvider()

    result = await provider.inspect_certificate(
        investigation_id=uuid4(),
        hostname="example.com",
        port=70000,
    )

    assert result["status"] == AnalysisStatus.FAILED.value
    assert result["error"] == "Port must be between 1 and 65535."


@pytest.mark.asyncio
async def test_tls_success_with_mocked_socket(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider = TLSIntelligenceProvider()

    fake_socket = MagicMock()
    fake_socket.getpeercert.return_value = {
        "subject": ((("commonName", "example.com"),),),
        "issuer": ((("commonName", "Example CA"),),),
        "subjectAltName": (
            ("DNS", "example.com"),
            ("DNS", "www.example.com"),
        ),
        "notBefore": "Jan 01 00:00:00 2026 GMT",
        "notAfter": "Jan 01 00:00:00 2027 GMT",
    }
    fake_socket.version.return_value = "TLSv1.3"
    fake_socket.cipher.return_value = (
        "TLS_AES_256_GCM_SHA384",
        "TLSv1.3",
        256,
    )

    fake_context = MagicMock()
    fake_context.wrap_socket.return_value.__enter__.return_value = fake_socket

    monkeypatch.setattr(
        "app.providers.tls_intelligence.ssl.create_default_context",
        lambda: fake_context,
    )

    fake_raw_socket = MagicMock()
    fake_raw_socket.__enter__.return_value = fake_raw_socket

    monkeypatch.setattr(
        "app.providers.tls_intelligence.socket.create_connection",
        lambda address, timeout: fake_raw_socket,
    )

    result = await provider.inspect_certificate(
        investigation_id=uuid4(),
        hostname="Example.COM.",
    )

    assert result["status"] == AnalysisStatus.SUCCESS.value
    assert result["hostname"] == "example.com"
    assert result["hostname_verified"] is True
    assert result["certificate_valid"] is True
    assert result["tls_version"] == "TLSv1.3"
    assert result["subject_alt_names"] == [
        "example.com",
        "www.example.com",
    ]
    assert result["issuer"]["commonName"] == ["Example CA"]


@pytest.mark.asyncio
async def test_tls_certificate_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider = TLSIntelligenceProvider()

    def raise_certificate_error(
        address: tuple[str, int],
        timeout: float,
    ) -> None:
        raise ssl.CertificateError("hostname mismatch")

    monkeypatch.setattr(
        "app.providers.tls_intelligence.socket.create_connection",
        raise_certificate_error,
    )

    result = await provider.inspect_certificate(
        investigation_id=uuid4(),
        hostname="example.com",
    )

    assert result["status"] == AnalysisStatus.FAILED.value
    assert result["hostname_verified"] is False
    assert "hostname verification failed" in result["error"]


@pytest.mark.asyncio
async def test_tls_network_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider = TLSIntelligenceProvider()

    def raise_os_error(
        address: tuple[str, int],
        timeout: float,
    ) -> None:
        raise OSError("connection refused")

    monkeypatch.setattr(
        "app.providers.tls_intelligence.socket.create_connection",
        raise_os_error,
    )

    result = await provider.inspect_certificate(
        investigation_id=uuid4(),
        hostname="example.com",
    )

    assert result["status"] == AnalysisStatus.FAILED.value
    assert "TLS connection failed" in result["error"]


def test_parse_certificate_date() -> None:
    provider = TLSIntelligenceProvider()

    parsed = provider._parse_certificate_date(
        "Jan 01 00:00:00 2026 GMT"
    )

    assert parsed == datetime(
        2026,
        1,
        1,
        tzinfo=timezone.utc,
    )