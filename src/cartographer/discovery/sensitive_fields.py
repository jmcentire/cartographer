"""Sensitive field scanner — detects PII/financial/auth field patterns."""

from __future__ import annotations

from pathlib import Path

import yaml

from cartographer.models import Confidence, DiscoveredSensitiveField

# Default patterns shipped with Cartographer
# Teams can extend by providing a custom classification_patterns.yaml
DEFAULT_PATTERNS: dict[str, list[str]] = {
    "PII": [
        "email",
        "phone",
        "phone_number",
        "first_name",
        "last_name",
        "full_name",
        "address",
        "street",
        "city",
        "zip_code",
        "postal_code",
        "date_of_birth",
        "dob",
        "birth_date",
        "ssn",
        "social_security",
        "social_security_number",
        "tax_id",
        "national_id",
        "passport",
        "passport_number",
        "driver_license",
        "drivers_license",
        "ip_address",
        "user_agent",
        "geolocation",
        "latitude",
        "longitude",
    ],
    "FINANCIAL": [
        "credit_card",
        "card_number",
        "cvv",
        "expiry",
        "expiration",
        "account_number",
        "routing_number",
        "bank_account",
        "iban",
        "swift",
        "balance",
        "payment",
        "billing",
        "invoice",
        "transaction",
    ],
    "AUTH": [
        "password",
        "password_hash",
        "hashed_password",
        "secret",
        "api_key",
        "api_secret",
        "token",
        "access_token",
        "refresh_token",
        "session_token",
        "jwt",
        "private_key",
        "credential",
        "credentials",
        "auth_token",
        "oauth_token",
        "mfa_secret",
        "totp_secret",
    ],
    "COMPLIANCE": [
        "audit_log",
        "consent",
        "gdpr",
        "hipaa",
        "pci",
        "compliance",
        "regulatory",
        "retention",
        "data_subject",
    ],
}


def load_patterns(custom_path: Path | None = None) -> dict[str, list[str]]:
    """Load classification patterns, merging custom patterns if provided."""
    patterns = dict(DEFAULT_PATTERNS)
    if custom_path and custom_path.exists():
        with open(custom_path) as f:
            custom: dict[str, list[str]] = yaml.safe_load(f) or {}
        for tier, fields in custom.items():
            if tier in patterns:
                existing = set(patterns[tier])
                patterns[tier].extend(f for f in fields if f not in existing)
            else:
                patterns[tier] = fields
    return patterns


class SensitiveFieldScanner:
    def __init__(self, custom_patterns_path: Path | None = None):
        self._patterns = load_patterns(custom_patterns_path)
        # Build a lookup: field_name -> (tier, pattern)
        self._lookup: dict[str, tuple[str, str]] = {}
        for tier, field_names in self._patterns.items():
            for name in field_names:
                self._lookup[name.lower()] = (tier, name)

    def scan(self, file_path: Path, content: str) -> list[DiscoveredSensitiveField]:
        results: list[DiscoveredSensitiveField] = []
        seen: set[tuple[str, int]] = set()

        for i, line in enumerate(content.split("\n"), 1):
            # Tokenize the line to find field-like identifiers
            tokens = _extract_identifiers(line)
            for token in tokens:
                normalized = token.lower()
                if normalized in self._lookup:
                    key = (normalized, i)
                    if key in seen:
                        continue
                    seen.add(key)
                    tier, pattern = self._lookup[normalized]
                    results.append(
                        DiscoveredSensitiveField(
                            field_name=token,
                            source_file=str(file_path),
                            line=i,
                            pattern_matched=pattern,
                            classification_hint=tier,
                            confidence=Confidence.LOW,
                        )
                    )

        return results


def _extract_identifiers(line: str) -> list[str]:
    """Extract identifier-like tokens from a line of code."""
    import re

    # Match word characters, including underscores (common in field names)
    return re.findall(r"\b[a-zA-Z_][a-zA-Z0-9_]*\b", line)
