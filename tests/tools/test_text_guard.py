"""Tests for tools.text_guard -- hidden-character detection & sanitization.

Hidden codepoints are built with chr() rather than embedded as invisible
literals, so the test source stays readable and copy-paste safe.
"""

import unicodedata

from tools.text_guard import (
    Category,
    SanitizePolicy,
    classify_codepoint,
    decode_tag_chars,
    decode_variation_selectors,
    invisible_ratio,
    sanitize,
    scan,
)

ZWSP = chr(0x200B)
ZWNJ = chr(0x200C)
NEL = chr(0x0085)
RLO = chr(0x202E)   # right-to-left override (Trojan Source)
PUA = chr(0xE000)


def _tag(s: str) -> str:
    """Encode ASCII as Unicode tag characters (the hidden channel)."""
    return "".join(chr(0xE0000 + ord(c)) for c in s)


# ---------------------------------------------------------------------------
# Classification
# ---------------------------------------------------------------------------

class TestClassify:
    def test_plain_text_is_benign(self):
        for ch in "Hello, world! 123 cafe naive":
            assert classify_codepoint(ord(ch)) is None

    def test_pua(self):
        assert classify_codepoint(0xE000) == Category.PUA
        assert classify_codepoint(0xF8FF) == Category.PUA
        assert classify_codepoint(0xF0000) == Category.PUA      # supplementary PUA-A
        assert classify_codepoint(0x100000) == Category.PUA     # PUA-B

    def test_c1_controls_including_nel(self):
        assert classify_codepoint(0x0085) == Category.C1_CONTROL  # NEL
        assert classify_codepoint(0x0080) == Category.C1_CONTROL
        assert classify_codepoint(0x009F) == Category.C1_CONTROL

    def test_zero_width_family(self):
        for cp in (0x200B, 0x200C, 0x200D, 0x2060, 0xFEFF, 0x180E):
            assert classify_codepoint(cp) == Category.ZERO_WIDTH

    def test_bidi_controls(self):
        for cp in (0x202A, 0x202E, 0x2066, 0x2069, 0x200E):
            assert classify_codepoint(cp) == Category.BIDI_CONTROL

    def test_tag_characters(self):
        assert classify_codepoint(0xE0041) == Category.TAG_CHAR   # tag 'A'
        assert classify_codepoint(0xE007F) == Category.TAG_CHAR   # cancel tag

    def test_variation_selectors(self):
        assert classify_codepoint(0xFE00) == Category.VARIATION_SELECTOR
        assert classify_codepoint(0xE0100) == Category.VARIATION_SELECTOR


# ---------------------------------------------------------------------------
# Scanning
# ---------------------------------------------------------------------------

class TestScan:
    def test_clean_text(self):
        report = scan("a perfectly ordinary sentence")
        assert not report.is_suspicious
        assert report.risk_score == 0

    def test_detects_zero_width_in_words(self):
        text = f"hel{ZWSP}lo wor{ZWNJ}ld"
        report = scan(text)
        assert report.is_suspicious
        assert report.counts_by_category()["zero_width"] == 2

    def test_detects_nel_pulses(self):
        text = f"li{NEL}ne"
        report = scan(text)
        assert any(f.category == Category.C1_CONTROL for f in report.findings)

    def test_bidi_scores_highest(self):
        report = scan(f"safe{RLO}txet_esrever")
        assert report.risk_score >= 80  # Trojan Source is top severity

    def test_normalization_change_flagged(self):
        decomposed = "cafe" + chr(0x0301)  # e + COMBINING ACUTE ACCENT
        report = scan(decomposed)
        assert report.normalization_changes is True
        assert report.risk_score > 0

    def test_indices_are_accurate(self):
        text = f"ab{ZWSP}cd"
        report = scan(text)
        assert report.findings[0].index == 2


# ---------------------------------------------------------------------------
# Decoding (forensics)
# ---------------------------------------------------------------------------

class TestDecode:
    def test_decode_tag_chars(self):
        carrier = "\U0001F44D" + _tag("hi")   # thumbs-up + hidden "hi"
        assert decode_tag_chars(carrier) == "hi"

    def test_scan_surfaces_tag_payload(self):
        report = scan("ok" + _tag("ignore prev"))
        assert report.decoded_payloads["tag_chars"] == "ignore prev"

    def test_decode_variation_selectors_roundtrip(self):
        data = b"Hi"
        enc = []
        for b in data:
            enc.append(chr(0xFE00 + b) if b < 16 else chr(0xE0100 + b - 16))
        assert decode_variation_selectors("".join(enc)) == "Hi"


# ---------------------------------------------------------------------------
# Sanitizing
# ---------------------------------------------------------------------------

class TestSanitize:
    def test_strips_zero_width_and_pua(self):
        text = f"he{ZWSP}llo{PUA} world"
        clean, report = sanitize(text)
        assert clean == "hello world"
        assert report.is_suspicious

    def test_strips_bidi_and_tag_chars(self):
        text = f"a{RLO}b" + _tag("x")
        clean, _ = sanitize(text)
        assert RLO not in clean
        assert all(not (0xE0000 <= ord(c) <= 0xE007F) for c in clean)

    def test_normalizes_to_nfc(self):
        decomposed = "cafe" + chr(0x0301)
        clean, _ = sanitize(decomposed)
        assert clean == unicodedata.normalize("NFC", decomposed)
        assert chr(0x0301) not in clean

    def test_preserves_legitimate_text(self):
        text = "Naive cafe resume costs 5 euro. Ogham: " + chr(0x1681) + chr(0x1682)
        clean, _ = sanitize(text)
        assert "Naive cafe resume" in clean
        # Ogham letters are assigned, visible script -- not stripped.
        assert chr(0x1681) in clean

    def test_variation_selectors_kept_by_default(self):
        text = "❤" + chr(0xFE0F)   # heart + emoji presentation selector
        clean, _ = sanitize(text)
        assert chr(0xFE0F) in clean

    def test_variation_selectors_strippable_on_demand(self):
        text = "❤" + chr(0xFE0F)
        policy = SanitizePolicy(strip_variation_selectors=True)
        clean, _ = sanitize(text, policy)
        assert chr(0xFE0F) not in clean


# ---------------------------------------------------------------------------
# Heuristics
# ---------------------------------------------------------------------------

class TestInvisibleRatio:
    def test_clean_is_zero(self):
        assert invisible_ratio("ordinary text") == 0.0

    def test_laced_text_is_high(self):
        text = ("a" + ZWSP) * 10  # half the characters are zero-width
        assert invisible_ratio(text) == 0.5

    def test_empty(self):
        assert invisible_ratio("") == 0.0
