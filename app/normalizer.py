import base64
import re
import unicodedata


ZERO_WIDTH_CHARS = {
    "\u200b",  # Zero Width Space
    "\u200c",  # Zero Width Non-Joiner
    "\u200d",  # Zero Width Joiner
    "\u2060",  # Word Joiner
    "\ufeff",  # Zero Width No-Break Space
}


LEET_MAP = str.maketrans({
    "0": "o",
    "1": "i",
    "3": "e",
    "4": "a",
    "5": "s",
    "7": "t",
    "8": "b",
    "9": "g",
})


def remove_zero_width(text: str) -> str:
    """Remove invisible Unicode characters commonly used for obfuscation."""

    return "".join(
        char for char in text
        if char not in ZERO_WIDTH_CHARS
    )


def normalize_unicode(text: str) -> str:
    """Apply Unicode compatibility normalization."""

    return unicodedata.normalize("NFKC", text)


def normalize_leetspeak(text: str) -> str:
    """
    Convert common numeric leetspeak substitutions.

    Example:
        1gn0re prev1ous 1nstruct10ns
        ->
        ignore previous instructions
    """

    return text.translate(LEET_MAP)


def try_decode_base64(value: str):
    """
    Try to decode a Base64 candidate.

    Returns decoded text if it appears to be readable,
    otherwise returns None.
    """

    candidate = value.strip()

    if len(candidate) < 16:
        return None

    # Base64 strings normally contain only these characters.
    if not re.fullmatch(r"[A-Za-z0-9+/=_-]+", candidate):
        return None

    # Remove padding and restore valid Base64 padding.
    candidate = candidate.rstrip("=")

    padding = "=" * (-len(candidate) % 4)

    try:
        decoded_bytes = base64.b64decode(
            candidate + padding,
            validate=False,
        )

        decoded = decoded_bytes.decode(
            "utf-8",
            errors="ignore",
        ).strip()

    except Exception:
        return None

    if not decoded:
        return None

    # Avoid treating random binary data as meaningful text.
    printable_ratio = sum(
        char.isprintable() or char.isspace()
        for char in decoded
    ) / len(decoded)

    if printable_ratio < 0.85:
        return None

    return decoded



def decode_base64_candidates(text: str):
    """Decode Base64 candidates without modifying their characters."""

    decoded_parts = []

    candidates = re.findall(
        r"(?<![A-Za-z0-9+/=_-])"
        r"[A-Za-z0-9+/=_-]{16,}"
        r"(?![A-Za-z0-9+/=_-])",
        text,
    )

    for candidate in candidates:
        decoded = try_decode_base64(candidate)

        if decoded is not None:
            decoded_parts.append(decoded)

    return decoded_parts




def normalize_text(text: str) -> dict:
    if not isinstance(text, str):
        text = str(text)

    original = text
    transformations = []

    normalized = normalize_unicode(text)

    if normalized != text:
        transformations.append("unicode_normalization")

    without_zero_width = remove_zero_width(normalized)

    if without_zero_width != normalized:
        transformations.append("zero_width_removal")

    normalized = without_zero_width

    # Decode the untouched encoded text first.
    decoded_parts = decode_base64_candidates(normalized)

    if decoded_parts:
        transformations.append("base64_decoding")

    # Apply leetspeak only after Base64 decoding.
    leet_normalized = normalize_leetspeak(normalized)

    if leet_normalized != normalized:
        transformations.append("leetspeak_normalization")

    normalized = leet_normalized

    if decoded_parts:
        normalized += "\n" + "\n".join(decoded_parts)

    return {
        "original_text": original,
        "normalized_text": normalized,
        "transformations": transformations,
        "decoded_base64": decoded_parts,
    }
