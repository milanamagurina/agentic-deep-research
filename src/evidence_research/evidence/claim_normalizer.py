"""Claim normalization: one fact, one claim node, many aliases (section 16).

1. deterministic canonical key (subject | predicate | object | period, with number/unit/currency
   normalization) -> exact match merges immediately;
2. otherwise candidate retrieval by token similarity on the same subject;
3. the model is asked SAME / DIFFERENT / UNCERTAIN for close candidates; only SAME merges.
"""

from __future__ import annotations

import re

from ..models import Claim, TemporalScope

_CURRENCY = {"€": "eur ", "eur": "eur ", "euro": "eur ", "euros": "eur ", "$": "usd ", "usd": "usd ", "us$": "usd ", "£": "gbp ", "gbp": "gbp "}
_MAGNITUDE = {"m": 1e6, "mn": 1e6, "million": 1e6, "mio": 1e6, "bn": 1e9, "b": 1e9, "billion": 1e9, "k": 1e3, "thousand": 1e3}
_FISCAL = re.compile(r"\bfy\s?'?(\d{2,4})\b")
_NUM = re.compile(r"(\d{1,3}(?:,\d{3})+(?:\.\d+)?|\d+(?:[.,]\d+)?)\s*(million|billion|thousand|mio|mn|bn|m|b|k)?\b")
_STOP = {"the", "a", "an", "of", "in", "for", "on", "at", "to", "and", "was", "were", "is", "are", "its", "by", "with", "as"}
SIMILARITY_CANDIDATE = 0.45


def _parse_number(raw: str) -> float:
    """'47.5' -> 47.5, '1,200' -> 1200 (thousands separator), '47,5' -> 47.5 (decimal comma)."""
    if "," in raw and "." not in raw:
        head, tail = raw.rsplit(",", 1)
        return float(raw.replace(",", "")) if len(tail) == 3 else float(f"{head}.{tail}")
    return float(raw.replace(",", ""))


def normalize_text(s: str) -> str:
    s = " " + s.lower().replace("’", "'") + " "
    s = s.replace("us$", " usd ").replace("€", " eur ").replace("$", " usd ").replace("£", " gbp ")
    for word, code in _CURRENCY.items():
        if word.isalpha():
            s = re.sub(rf"\b{word}\b", code, s)
    s = _FISCAL.sub(lambda m: "fy" + (m.group(1) if len(m.group(1)) == 4 else "20" + m.group(1)), s)

    def num(m: re.Match) -> str:
        value = _parse_number(m.group(1)) * _MAGNITUDE.get((m.group(2) or "").lower(), 1)
        text = f"{value:.4f}".rstrip("0").rstrip(".")
        return f" {text} "

    s = _NUM.sub(num, s)
    s = re.sub(r"[^a-z0-9.% ]+", " ", s)
    return " ".join(w for w in s.split() if w not in _STOP and w.strip(".") )


def _period(scope: TemporalScope | None) -> str:
    if not scope:
        return ""
    return f"{scope.valid_from or ''}..{scope.valid_to or ''}"


def canonical_key(subject: str, predicate: str, obj: str, scope: TemporalScope | None, kind: str = "fact", attributed_to: str | None = None) -> str:
    who = normalize_text(attributed_to) if attributed_to else ""
    return "|".join([kind, who, normalize_text(subject), normalize_text(predicate), normalize_text(obj), _period(scope)])


def similarity(a: str, b: str) -> float:
    ta, tb = set(normalize_text(a).split()), set(normalize_text(b).split())
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / len(ta | tb)


def subject_matches(a: Claim, b: Claim) -> bool:
    sa, sb = set(normalize_text(a.subject).split()), set(normalize_text(b.subject).split())
    return bool(sa & sb)


def candidates(new: Claim, existing: list[Claim], limit: int = 3) -> list[tuple[float, Claim]]:
    scored = [
        (similarity(new.natural_language, c.natural_language), c)
        for c in existing
        if c.kind == new.kind and subject_matches(new, c) and c.id != new.id
    ]
    return sorted([t for t in scored if t[0] >= SIMILARITY_CANDIDATE], key=lambda t: -t[0])[:limit]


def same_slot(a: Claim, b: Claim) -> bool:
    """Same subject and predicate (normalized): candidates for contradiction or temporal versioning.

    Attribution claims are excluded: two different things someone SAID never contradict each other.
    """
    if a.kind != "fact" or b.kind != "fact":
        return False
    return normalize_text(a.subject) == normalize_text(b.subject) and normalize_text(a.predicate) == normalize_text(b.predicate)


def numbers(text: str) -> list[float]:
    out = []
    for tok in normalize_text(text).split():
        try:
            out.append(float(tok))
        except ValueError:
            pass
    return out


def values_consistent(a: str, b: str, tolerance: float = 0.02) -> bool:
    """'EUR 47.5 million' vs 'EUR 47,512,000': equal up to rounding, so not a contradiction."""
    if normalize_text(a) == normalize_text(b):
        return True
    na, nb = numbers(a), numbers(b)
    if not na or len(na) != len(nb):
        return False
    return all(abs(x - y) <= tolerance * max(abs(x), abs(y), 1e-9) for x, y in zip(na, nb))
