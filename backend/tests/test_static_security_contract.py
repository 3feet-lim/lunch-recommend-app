"""Static security and scope checks for the Slack lunch bot MVP.

These checks are intentionally lightweight and run without importing app code.
They catch common regressions from the PRD/test spec: committed credentials,
out-of-scope product paths, unsafe logging, and accidental real-network tests.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest


BACKEND_ROOT = Path(__file__).resolve().parents[1]
APP_ROOT = BACKEND_ROOT / "app"
TEST_ROOT = BACKEND_ROOT / "tests"


SECRET_PATTERNS = [
    re.compile(r"xox[baprs]-[A-Za-z0-9-]+"),
    re.compile(r"hooks\.slack\.com/services/[A-Za-z0-9/_-]+"),
    re.compile(r"(?i)(slack|kakao|naver|openweather)[_a-z]*secret\s*=\s*['\"][^'\"]{8,}"),
    re.compile(r"(?i)(api[_-]?key|bot[_-]?token)\s*=\s*['\"][^'\"]{8,}"),
]
FORBIDDEN_SCOPE_TERMS = {
    "voting",
    "vote",
    "reservation",
    "reserve",
    "ordering",
    "payment",
    "personal_learning",
    "personalization",
    "ios",
    "swiftui",
}


def _python_files(root: Path) -> list[Path]:
    if not root.exists():
        return []
    return [p for p in root.rglob("*.py") if "__pycache__" not in p.parts]


@pytest.mark.security
def test_no_committed_real_secrets_in_backend_sources() -> None:
    sources = _python_files(APP_ROOT) + [p for p in BACKEND_ROOT.glob("*.py")]
    if not sources:
        pytest.skip("backend app sources are not present yet")

    offenders: list[str] = []
    for path in sources:
        text = path.read_text(encoding="utf-8")
        for pattern in SECRET_PATTERNS:
            if pattern.search(text):
                offenders.append(str(path.relative_to(BACKEND_ROOT)))
                break

    assert offenders == []


@pytest.mark.contract
def test_mvp_backend_does_not_add_out_of_scope_product_paths() -> None:
    sources = _python_files(APP_ROOT)
    if not sources:
        pytest.skip("backend app sources are not present yet")

    offenders: list[str] = []
    for path in sources:
        lowered = path.read_text(encoding="utf-8").lower()
        # Allow env/test guard words only in explicit security denylist comments.
        for term in FORBIDDEN_SCOPE_TERMS:
            if re.search(rf"\b{re.escape(term)}\b", lowered):
                offenders.append(f"{path.relative_to(BACKEND_ROOT)}:{term}")

    assert offenders == []


@pytest.mark.security
def test_tests_keep_real_network_blocking_fixture() -> None:
    conftest = TEST_ROOT / "conftest.py"
    text = conftest.read_text(encoding="utf-8")

    assert "no_real_network" in text
    assert "socket" in text
    assert "real network access blocked" in text


@pytest.mark.security
def test_logging_sources_include_secret_redaction_when_logging_exists() -> None:
    logging_candidates = list(APP_ROOT.rglob("*log*.py")) if APP_ROOT.exists() else []
    if not logging_candidates:
        pytest.skip("logging implementation is not present yet")

    combined = "\n".join(path.read_text(encoding="utf-8").lower() for path in logging_candidates)
    assert any(word in combined for word in ("redact", "mask", "sanitize"))
    assert "response_url" in combined
    assert "slack_signing_secret" in combined or "api_key" in combined or "secret" in combined
