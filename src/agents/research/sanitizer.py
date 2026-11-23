"""
Input sanitizer for external/social/market text before it enters any model or
risk path. Treats prompt injection as a financial attack: any matched pattern
causes the input to be rejected (dropped/flagged), never passed through.

Patterns are intentionally conservative: false positives are safe (we lose a
signal), false negatives are dangerous (an injection could reach execution).
"""

from __future__ import annotations

import re
from typing import List, Tuple

# Prompt-injection / jailbreak patterns commonly used to hijack LLM output that
# later flows into trading decisions. Each is matched case-insensitively.
_INJECTION_PATTERNS: List[re.Pattern[str]] = [
    re.compile(r"ignore\s+(previous|all)\s+(instructions|directives)", re.I),
    re.compile(r"disregard\s+(previous|all)\s+(instructions|directives)", re.I),
    re.compile(r"new\s+(task|directive|instruction|system)", re.I),
    re.compile(r"system\s*(prompt|message|role|instruction)", re.I),
    re.compile(r"you\s+are\s+now\s+(a|an)\s+\w+", re.I),
    re.compile(r"jailbreak|DAN|do\s+anything\s+now", re.I),
    re.compile(r"override\s+(safety|risk|kill\s*switch|limit)", re.I),
    re.compile(r"send\s+.{0,60}\s+to\s+0x[0-9a-fA-F]{40}", re.I),
    re.compile(r"transfer\s+.{0,60}\s+to\s+0x[0-9a-fA-F]{40}", re.I),
    re.compile(r"approve\s+.{0,60}\s+for\s+0x[0-9a-fA-F]{40}", re.I),
    re.compile(r"(api|secret|private)\s*key\s*[:=]", re.I),
    re.compile(r"sk-[A-Za-z0-9]{20,}", re.I),
    re.compile(r"-----BEGIN\s+[A-Z ]+-----", re.I),
]

# Credential-like tokens that must never be echoed into logs or LLM context.
_CREDENTIAL_PATTERNS: List[re.Pattern[str]] = [
    re.compile(r"sk-[A-Za-z0-9]{20,}"),
    re.compile(r"0x[0-9a-fA-F]{64}"),
    re.compile(r"api[_-]?key[\"']?\s*[:=]\s*[^\s\"']+", re.I),
    re.compile(r"secret[\"']?\s*[:=]\s*[^\s\"']+", re.I),
    re.compile(r"password[\"']?\s*[:=]\s*[^\s\"']+", re.I),
    re.compile(r"private[_-]?key[\"']?\s*[:=]\s*[^\s\"']+", re.I),
]

# Maximum length of any single external text fed into the research path.
MAX_INPUT_LEN = 4000


class SanitizedResult:
    """Outcome of sanitizing a piece of external text."""

    def __init__(self, text: str, safe: bool, reasons: List[str]) -> None:
        self.text = text
        self.safe = safe
        self.reasons = reasons

    def __bool__(self) -> bool:
        return self.safe

    def __repr__(self) -> str:
        return f"SanitizedResult(safe={self.safe}, reasons={self.reasons})"


class TextSanitizer:
    """Sanitizes untrusted external text before it reaches the model/risk path."""

    def __init__(self, max_input_len: int = MAX_INPUT_LEN) -> None:
        self.max_input_len = max_input_len
        self._redactions = 0

    @property
    def redactions(self) -> int:
        return self._redactions

    def _redact_credentials(self, text: str) -> str:
        """Replace credential-like substrings with placeholders."""
        result = text
        for pat in _CREDENTIAL_PATTERNS:
            result, n = pat.subn("[REDACTED]", result)
            self._redactions += n
        return result

    def sanitize(self, text: str) -> SanitizedResult:
        """Return a SanitizedResult; safe=False means the caller must drop it."""
        if not isinstance(text, str):
            return SanitizedResult("", False, ["non-string input"])

        if len(text) > self.max_input_len:
            return SanitizedResult(
                "", False, [f"input too long ({len(text)} > {self.max_input_len})"]
            )

        # Strip credentials first so they never appear in reasons or logs.
        clean = self._redact_credentials(text)

        reasons: List[str] = []
        for pat in _INJECTION_PATTERNS:
            if pat.search(clean):
                reasons.append(f"matched injection pattern: {pat.pattern[:40]}")

        if reasons:
            # Reject whole input rather than attempting surgical removal.
            return SanitizedResult("", False, reasons)

        return SanitizedResult(clean, True, [])
