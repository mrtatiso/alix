#!/usr/bin/env python3
"""alix: syvox + alias → a band80 that reads as another alias.

    $ alix check maria                                   → valid · ma·ria
    $ echo clave | vox <salt> | alix seal maria          → the band80 to store
    $ echo clave | vox <salt> | alix open <stored>       → maria
    $ alix show <stored>                                 → the alias anyone sees
    $ alix sample 20                                     → 20 aliases, to see what comes out

    >>> from alix import seal, open_, show
    >>> stored = seal(syvox, "maria")
    >>> open_(syvox, stored)
    'maria'

alix never sees a key or a salt: it receives a syvox (any 80 digits, usually
from vox) through stdin, never as an argument. Its only data is clean.tecy,
which must sit next to alix.py and is checked by sha256.

What is stored is a band80. Any band80 reads as an alias: 4 digits say how
many syllables (1 to 4) and each syllable comes from 19 more digits, looked up
in the syllables of clean.tecy. Each syllable takes a share of the numbers
proportional to its count to the power 3/4, so common syllables come out often
and rare ones seldom.

An alias is proper when it has 3 to 10 letters, at most one accent, does not
start with rr or ñ, and has at most 2 consonants in a row (y counts as a
vowel), or 3 when the last two are pr br tr dr cr gr fr pl bl cl gl fl tl ch ll
(as in alejandro, hombre, ancho). At the start, two consonants must be one of
those pairs or sh th ph wh st sp sc sk sm sn sl sw, and three must be s + pair
(stra, spri, scla). If 80 digits read as an alias that is not proper, alix reads again from
shake_256("alix1-again|" + the 80 digits), until it gets a proper one. So any
syvox, right or wrong, always opens into a proper alias.

open adds the digits of the syvox to the stored band80 (digit by digit, mod 10,
like vox) and reads the alias. seal does the opposite, choosing at random one
of the many band80s that read as the alias. So:

  - every syvox opens every stored band80 into an alias built from the table;
    a wrong one gives an alias like any other
  - the same alias sealed twice gives two different band80s
  - the stored band80 says nothing, not even how many syllables the alias has

An alias can be sealed only if it is proper and can be cut into 1 to 4
syllables of the table.

v1: digits = shake_256("alix1|" + 80 digits of the syvox), bytes 0-249 → digit.
Count, first 4 digits: 0000-0999 → 1, 1000-5499 → 2, 5500-8999 → 3,
9000-9999 → 4. Syllable i: 19 digits starting at 4 + 19·i, as a number, mod the total weight. Weight = isqrt(count³)
rounded down to an integer, then its square root: isqrt(isqrt(count³)).
Changing any of this, or the table, would be v2.
"""
import bisect
import hashlib
import math
import os
import secrets
import sys
import unicodedata

__version__ = "1.0.0"
__all__ = ["check", "proper", "seal", "open_", "show", "sample"]

HERE = os.path.dirname(os.path.abspath(__file__))
TABLE = "clean.tecy"
TABLE_SHA256 = "a2593fa55ce78bdea018fdf3b261d44b8131f35eda059bf063db3ab087ad2341"
DIGITS = 80
CHUNK = 19
MAX_PIECES = 4
HEAD = 4
COUNTS = ((1000, 1), (5500, 2), (9000, 3), (10000, 4))   # first 4 digits below → syllables

_SYL = _START = _INDEX = None
_TOTAL = 0


# ---------- the table ----------

def _load():
    global _SYL, _START, _INDEX, _TOTAL
    if _SYL is not None:
        return
    path = os.path.join(HERE, TABLE)
    if not os.path.exists(path):
        raise SystemExit(f"alix: {TABLE} is missing next to alix.py")
    with open(path, "rb") as f:
        raw = f.read()
    if hashlib.sha256(raw).hexdigest() != TABLE_SHA256:
        raise SystemExit(f"alix: {TABLE} is not the expected table (sha256 differs)")
    _SYL, _START, _INDEX = [], [], {}
    for line in raw.decode("utf-8").splitlines():
        piece, n, kind = line.split("\t")
        if kind == "s":
            _INDEX[piece] = len(_SYL)
            _SYL.append(piece)
            _START.append(_TOTAL)
            _TOTAL += math.isqrt(math.isqrt(int(n) ** 3))


def _piece(value: int) -> str:
    return _SYL[bisect.bisect(_START, value % _TOTAL) - 1]


def _split(alias: str):
    """The fewest syllables of the table that make the alias, or None."""
    _load()
    best = [None] * (len(alias) + 1)
    best[0] = []
    for j in range(1, len(alias) + 1):
        for i in range(max(0, j - 8), j):
            if best[i] is not None and alias[i:j] in _INDEX:
                cand = best[i] + [alias[i:j]]
                if best[j] is None or len(cand) < len(best[j]):
                    best[j] = cand
    return best[-1]


def _norm(alias: str) -> str:
    return unicodedata.normalize("NFC", alias).strip().lower()


# ---------- digits ----------

def _digits(band: str) -> list:
    d = [int(c) for c in band if c in "0123456789"]
    if len(d) != DIGITS:
        raise ValueError(f"must have {DIGITS} digits, not {len(d)}")
    return d


def _stream(syvox: str) -> list:
    """80 uniform digits from the syvox: bytes 0-249 → digit, 250-255 skipped."""
    seed = b"alix1|" + bytes(c + 48 for c in _digits(syvox))
    out, block = [], 0
    while len(out) < DIGITS:
        for b in hashlib.shake_256(seed + block.to_bytes(4, "big")).digest(128):
            if b < 250 and len(out) < DIGITS:
                out.append(b % 10)
        block += 1
    return out


def _band(d: list) -> str:
    s = "".join(map(str, d))
    return ".".join(s[i:i + 20] for i in range(0, DIGITS, 20))


VOWELS = set("aeiouyáéíóúü")
ACCENTS = set("áéíóú")


PAIRS = {a + b for a in "pbtdcgf" for b in "lr"} - {"dl"} | {"tl", "ch", "ll"}
FIRST = PAIRS | {"sh", "th", "ph", "wh", "st", "sp", "sc", "sk", "sm", "sn", "sl", "sw"}


def proper(alias: str) -> bool:
    """3 to 10 letters, at most one accent, no rr or ñ first, consonants in a row as in Spanish."""
    run = 0
    for i, c in enumerate(alias):
        run = 0 if c in VOWELS else run + 1
        if run > 3 or (run == 3 and alias[i - 1:i + 1] not in PAIRS):
            return False
    lead = next((i for i, c in enumerate(alias) if c in VOWELS), len(alias))
    if (lead == 2 and alias[:2] not in FIRST) or (lead == 3 and not (alias[0] == "s" and alias[1:3] in PAIRS)):
        return False
    return (3 <= len(alias) <= 10 and sum(c in ACCENTS for c in alias) <= 1
            and not alias.startswith(("rr", "ñ")))


def _again(d: list) -> list:
    seed = b"alix1-again|" + bytes(c + 48 for c in d)
    out, block = [], 0
    while len(out) < DIGITS:
        for b in hashlib.shake_256(seed + block.to_bytes(4, "big")).digest(128):
            if b < 250 and len(out) < DIGITS:
                out.append(b % 10)
        block += 1
    return out


def _read(d: list) -> str:
    """The proper alias these 80 digits read as."""
    for _ in range(256):
        alias = _read_once(d)
        if proper(alias):
            return alias
        d = _again(d)
    return alias


def _read_once(d: list) -> str:
    """The alias these 80 digits read as, proper or not."""
    _load()
    first = int("".join(map(str, d[:HEAD])))
    pieces = next(k for limit, k in COUNTS if first < limit)
    out = []
    for i in range(pieces):
        chunk = d[HEAD + CHUNK * i: HEAD + CHUNK * (i + 1)]
        out.append(_piece(int("".join(map(str, chunk)))))
    return "".join(out)


# ---------- alix ----------

def check(alias: str):
    """The syllables the alias is sealed as, or None if it cannot be sealed."""
    alias = _norm(alias)
    if not proper(alias):
        return None
    parts = _split(alias)
    return parts if parts and len(parts) <= MAX_PIECES else None


def seal(syvox: str, alias: str) -> str:
    """A band80 to store, so that open_ with this syvox gives back the alias."""
    parts = check(alias)
    if not parts:
        raise ValueError(f"'{alias}' is not proper or cannot be made of 1 to {MAX_PIECES} syllables of the table")
    rnd = secrets.randbelow
    lo = 0
    for limit, k in COUNTS:
        if k == len(parts):
            first = lo + rnd(limit - lo)
            break
        lo = limit
    d = [int(c) for c in str(first).zfill(HEAD)]
    top = 10 ** CHUNK
    for i in range(MAX_PIECES):
        if i < len(parts):
            idx = _INDEX[parts[i]]
            width = (_START[idx + 1] if idx + 1 < len(_START) else _TOTAL) - _START[idx]
            value = rnd(top // _TOTAL) * _TOTAL + _START[idx] + rnd(width)
        else:
            value = rnd(top)
        d += [int(c) for c in str(value).zfill(CHUNK)]
    return _band([(x - s) % 10 for x, s in zip(d, _stream(syvox))])


def open_(syvox: str, stored: str) -> str:
    """The alias this stored band80 hides under this syvox. Any syvox works."""
    return _read([(x + s) % 10 for x, s in zip(_digits(stored), _stream(syvox))])


def show(stored: str) -> str:
    """The alias anyone sees in the stored band80, without a syvox."""
    return _read(_digits(stored))


def sample(n: int = 100) -> list:
    """n aliases read from random band80s: what a wrong syvox shows."""
    return [_read([secrets.randbelow(10) for _ in range(DIGITS)]) for _ in range(n)]


# ---------- terminal ----------

USAGE = """usage:
  alix check <alias>     can it be sealed, and as which syllables
  alix seal <alias>      the band80 to store       (syvox through stdin)
  alix open <band80>     the alias it hides        (syvox through stdin)
  alix show <band80>     the alias anyone sees
  alix sample [n]        n aliases read from random band80s"""


def main(args=None) -> int:
    args = sys.argv[1:] if args is None else args
    try:
        if len(args) == 2 and args[0] == "check":
            parts = check(args[1])
            print(f"valid · {'·'.join(parts)}" if parts else "invalid")
            return 0 if parts else 1
        if len(args) == 2 and args[0] in ("seal", "open") and not sys.stdin.isatty():
            syvox = sys.stdin.readline().strip()
            print(seal(syvox, args[1]) if args[0] == "seal" else open_(syvox, args[1]))
            return 0
        if len(args) == 2 and args[0] == "show":
            print(show(args[1]))
            return 0
        if args and args[0] == "sample" and len(args) <= 2:
            out = sample(int(args[1]) if len(args) == 2 else 100)
            for i in range(0, len(out), 10):
                print("  ".join(f"{w:<12}" for w in out[i:i + 10]))
            return 0
    except ValueError as e:
        print(f"alix: {e}", file=sys.stderr)
        return 2
    print(USAGE, file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
