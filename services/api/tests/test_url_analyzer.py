"""Unit tests for the deterministic VERA URL analyzer."""

from app.providers.url_analyzer import URLAnalyzer


def test_valid_https_url() -> None:
    """A normal HTTPS URL should be accepted without suspicious indicators."""
    analyzer = URLAnalyzer()

    result = analyzer.analyze("https://example.com")

    assert result.is_valid is True
    assert result.scheme == "https"
    assert result.hostname == "example.com"
    assert result.path == "/"
    assert result.has_ip_host is False
    assert result.has_punycode is False
    assert result.has_credentials is False
    assert result.has_explicit_port is False
    assert result.subdomain_count == 0
    assert result.indicators == []


def test_https_url_with_standard_explicit_port() -> None:
    """HTTPS port 443 is explicit but should not be flagged as nonstandard."""
    analyzer = URLAnalyzer()

    result = analyzer.analyze("https://example.com:443/login")

    assert result.is_valid is True
    assert result.port == 443
    assert result.has_explicit_port is True
    assert "explicit_nonstandard_port" not in result.indicators


def test_http_url_with_standard_explicit_port() -> None:
    """HTTP port 80 is explicit but should not be flagged as nonstandard."""
    analyzer = URLAnalyzer()

    result = analyzer.analyze("http://example.com:80/login")

    assert result.is_valid is True
    assert result.port == 80
    assert result.has_explicit_port is True
    assert "explicit_nonstandard_port" not in result.indicators
    assert "insecure_http" in result.indicators


def test_nonstandard_explicit_port() -> None:
    """A non-standard explicit port should produce the expected indicator."""
    analyzer = URLAnalyzer()

    result = analyzer.analyze("https://example.com:8080/login")

    assert result.is_valid is True
    assert result.port == 8080
    assert result.has_explicit_port is True
    assert "explicit_nonstandard_port" in result.indicators


def test_ip_host_has_zero_subdomains() -> None:
    """IP addresses must not be interpreted as having domain subdomains."""
    analyzer = URLAnalyzer()

    result = analyzer.analyze("http://127.0.0.1:8080/login")

    assert result.is_valid is True
    assert result.hostname == "127.0.0.1"
    assert result.has_ip_host is True
    assert result.subdomain_count == 0
    assert "ip_address_host" in result.indicators
    assert "explicit_nonstandard_port" in result.indicators


def test_punycode_hostname() -> None:
    """Punycode hostnames should produce a deterministic indicator."""
    analyzer = URLAnalyzer()

    result = analyzer.analyze("https://xn--example-9za.com/login")

    assert result.is_valid is True
    assert result.has_punycode is True
    assert "punycode_hostname" in result.indicators
    assert "login" in result.suspicious_keyword_hits
    assert "suspicious_keywords" in result.indicators


def test_embedded_credentials() -> None:
    """URLs containing credentials should produce an explicit indicator."""
    analyzer = URLAnalyzer()

    result = analyzer.analyze(
        "https://user:password@example.com/login"
    )

    assert result.is_valid is True
    assert result.has_credentials is True
    assert "embedded_credentials" in result.indicators


def test_deep_subdomain_structure() -> None:
    """Three or more subdomain labels should be detected."""
    analyzer = URLAnalyzer()

    result = analyzer.analyze(
        "https://a.b.c.example.com/login"
    )

    assert result.is_valid is True
    assert result.subdomain_count == 3
    assert "deep_subdomain_structure" in result.indicators


def test_suspicious_keywords() -> None:
    """Investment and verification-related URL terms should be detected."""
    analyzer = URLAnalyzer()

    result = analyzer.analyze(
        "https://example.com/investment/verify?otp=1234"
    )

    assert result.is_valid is True
    assert "investment" in result.suspicious_keyword_hits
    assert "verify" in result.suspicious_keyword_hits
    assert "otp" in result.suspicious_keyword_hits
    assert "suspicious_keywords" in result.indicators


def test_query_parameters_and_fragment() -> None:
    """Query and fragment metadata should be extracted deterministically."""
    analyzer = URLAnalyzer()

    result = analyzer.analyze(
        "https://example.com/login?user=a&otp=1234#section"
    )

    assert result.is_valid is True
    assert result.query_parameter_count == 2
    assert result.fragment_present is True
    assert result.warnings
    assert "fragment" in result.warnings[0].lower()


def test_long_url_indicator() -> None:
    """Long URLs should produce the appropriate length indicator."""
    analyzer = URLAnalyzer()

    long_path = "a" * 85
    result = analyzer.analyze(
        f"https://example.com/{long_path}"
    )

    assert result.is_valid is True
    assert "long_url" in result.indicators
    assert "very_long_url" not in result.indicators


def test_very_long_url_indicator() -> None:
    """Very long URLs should produce the stronger length indicator."""
    analyzer = URLAnalyzer()

    very_long_path = "a" * 125
    result = analyzer.analyze(
        f"https://example.com/{very_long_path}"
    )

    assert result.is_valid is True
    assert "very_long_url" in result.indicators


def test_invalid_empty_url() -> None:
    """Empty URL input must fail honestly."""
    analyzer = URLAnalyzer()

    result = analyzer.analyze("   ")

    assert result.is_valid is False
    assert result.warnings
    assert result.warnings[0] == "URL input is empty."


def test_invalid_scheme() -> None:
    """Only HTTP and HTTPS URLs are accepted."""
    analyzer = URLAnalyzer()

    result = analyzer.analyze("ftp://example.com/file")

    assert result.is_valid is False
    assert result.warnings
    assert result.warnings[0] == "URL must use HTTP or HTTPS."


def test_missing_hostname() -> None:
    """HTTP(S) URLs without a hostname must fail validation."""
    analyzer = URLAnalyzer()

    result = analyzer.analyze("https:///login")

    assert result.is_valid is False
    assert result.warnings
    assert result.warnings[0] == "URL does not contain a hostname."


def test_invalid_port() -> None:
    """Malformed ports must fail deterministically."""
    analyzer = URLAnalyzer()

    result = analyzer.analyze("https://example.com:abc/login")

    assert result.is_valid is False
    assert result.warnings
    assert "port is invalid" in result.warnings[0]


def test_normalized_url() -> None:
    """Normalization should produce a stable HTTP(S) representation."""
    analyzer = URLAnalyzer()

    result = analyzer.analyze(
        "HTTPS://Example.COM/login?otp=1234"
    )

    assert result.is_valid is True
    assert result.normalized_url == (
        "https://example.com/login?otp=1234"
    )