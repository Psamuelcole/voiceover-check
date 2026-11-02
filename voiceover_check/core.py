"""Compare what a script says with what a voiceover actually said.

The heard words come from a transcript with timings, so every flag says where to look.
A flag means "listen here". Speech recognition makes mistakes too, especially on names.
"""
import glob, json, os, re
from collections import namedtuple

Flag = namedtuple("Flag", "kind seconds wrote heard")
WORD = re.compile(r"[^\W_]+(?:'[^\W_]+)*")
MARKUP = re.compile(r"\[([^\]]+)\]\(/[^)]*/\)")  # [Lagos](/lˈAɡɔs/) -> Lagos


UNITS = {w: i for i, w in enumerate("zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen sixteen seventeen eighteen nineteen".split())}
TENS = {w: (i + 2) * 10 for i, w in enumerate("twenty thirty forty fifty sixty seventy eighty ninety".split())}
ORDINALS = {"first": 1, "second": 2, "third": 3, "fourth": 4, "fifth": 5, "sixth": 6, "seventh": 7, "eighth": 8, "ninth": 9, "tenth": 10,
            "eleventh": 11, "twelfth": 12, "thirteenth": 13, "fourteenth": 14, "fifteenth": 15, "sixteenth": 16, "seventeenth": 17, "eighteenth": 18,
            "nineteenth": 19, "twentieth": 20, "thirtieth": 30, "fortieth": 40, "fiftieth": 50, "sixtieth": 60, "seventieth": 70, "eightieth": 80, "ninetieth": 90}
ORDINAL_END = {1: "st", 2: "nd", 3: "rd", 21: "st", 22: "nd", 23: "rd", 31: "st"}
CURRENCY = {"$": "dollars", "₦": "naira", "£": "pounds", "€": "euros"}
BIG = ("thousand", "million", "billion", "trillion")


def _ordinal(n):
    return f"{n}{ORDINAL_END.get(n, 'th')}"


def _small(t, i):
    """Read a spoken number under 100 at position i. Returns (value, next position, ordinal?)."""
    if t[i] in UNITS:
        return UNITS[t[i]], i + 1, False
    if t[i] in ORDINALS:
        return ORDINALS[t[i]], i + 1, True
    if t[i] in TENS:
        n = TENS[t[i]]
        if i + 1 < len(t):
            if t[i + 1] in UNITS and 0 < UNITS[t[i + 1]] < 10:
                return n + UNITS[t[i + 1]], i + 2, False
            if t[i + 1] in ORDINALS and ORDINALS[t[i + 1]] < 10:
                return n + ORDINALS[t[i + 1]], i + 2, True
        return n, i + 1, False
    return None


def _spoken_number(t, i):
    """Read a spoken number at position i: thirty nine, two hundred and fifty, two thousand and seven, twenty twenty six."""
    first = _small(t, i)
    if not first:
        return None
    n, j, ordinal = first
    if ordinal:
        return _ordinal(n), j
    # years said in two parts: nineteen ninety, twenty twenty six
    if 10 <= n <= 20 and j < len(t) and t[j] in TENS:
        low, k, is_ord = _small(t, j)
        if not is_ord:
            return str(n * 100 + low), k
    if n < 10 and j < len(t) and t[j] == "hundred":
        n, j = n * 100, j + 1
        k = j + 1 if j < len(t) and t[j] == "and" else j
        if k < len(t) and _small(t, k) and not _small(t, k)[2]:
            low, j, _ = _small(t, k)
            n += low
    if j < len(t) and t[j] == "thousand" and n < 1000:
        n, j = n * 1000, j + 1
        k = j + 1 if j < len(t) and t[j] == "and" else j
        if k < len(t) and _small(t, k) and not _small(t, k)[2]:
            low, j, _ = _small(t, k)
            n += low
    return str(n), j


def _normalise(raw):
    """Say numbers one way, so 'two thousand and sixteen' matches '2016'. Returns tokens and where each started."""
    out, starts, i = [], [], 0
    while i < len(raw):
        found = _spoken_number(raw, i)
        word, j = found if found else (raw[i], i + 1)
        out.append(word); starts.append(i); i = j
    # "2 point 1" stays three words on both sides; "39 dollars million" becomes "39 million dollars"
    for k in range(len(out) - 1):
        if out[k] in CURRENCY.values() and out[k + 1] in BIG:
            out[k], out[k + 1] = out[k + 1], out[k]
    return out, starts


def _raw_tokens(text):
    text = MARKUP.sub(r"\1", text).lower().replace("’", "'")
    text = re.sub(r"(?<=\d),(?=\d)", "", text)
    text = re.sub(r"([$₦£€])\s?(\d+(?:\.\d+)?)(\s?(?:thousand|million|billion|trillion))?", lambda m: f"{m.group(2)}{m.group(3) or ''} {CURRENCY[m.group(1)]}", text)
    text = re.sub(r"(?<=\d)\.(?=\d)", " point ", text).replace("%", " percent")
    return [w.replace("'", "") for w in WORD.findall(text.replace("-", " "))]


def tokens(text):
    return _normalise(_raw_tokens(text))[0]


def _same_sounds(a, b):
    """startup / start up, founderscable dot com / founderscable.com: same words, spaced differently."""
    return a.replace(" ", "").replace("dot", "") == b.replace(" ", "").replace("dot", "")


def load_script(path):
    """One text file, or every .txt in a folder in name order."""
    if os.path.isdir(path):
        paths = sorted(glob.glob(os.path.join(path, "*.txt")))
        if not paths:
            raise ValueError(f"no .txt files in {path}")
    else:
        paths = [path]
    parts = []
    for p in paths:
        with open(p, encoding="utf-8") as f:
            parts.append(f.read())
    return "\n".join(parts)


def load_words(path):
    """Timed words from JSON: a list, or {"words": [...]}. Items use w/s or word/start."""
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    items = data["words"] if isinstance(data, dict) else data
    return [(i.get("w", i.get("word", "")), float(i.get("s", i.get("start", 0)))) for i in items]


def compare(script_text, timed_words):
    """Return (match score from 0 to 1, list of Flags)."""
    import difflib
    wrote = tokens(script_text)
    joined = []
    for word, start in timed_words:  # speech models can split 2,000 into "2," + "000" and 2.1 into "2" + ".1"
        w = word.strip()
        if joined and (re.fullmatch(r"[,.]\d+.*", w) or (re.search(r"(?<!\d\d\d)\d,$", joined[-1][0]) and re.fullmatch(r"\d{3}\W*", w))):
            joined[-1] = (joined[-1][0] + w, joined[-1][1])
        else:
            joined.append((w, start))
    raw, raw_times = [], []
    for word, start in joined:
        for t in _raw_tokens(word):
            raw.append(t); raw_times.append(start)
    heard, starts = _normalise(raw)
    times = [raw_times[i] for i in starts]
    sm = difflib.SequenceMatcher(None, wrote, heard, autojunk=False)
    flags = []
    for op, a1, a2, b1, b2 in sm.get_opcodes():
        if op == "equal":
            continue
        at = times[min(b1, len(times) - 1)] if times else 0.0
        kind = {"insert": "EXTRA", "delete": "MISSING", "replace": "CHANGED"}[op]
        said, spoke = " ".join(wrote[a1:a2]), " ".join(heard[b1:b2])
        if not _same_sounds(said, spoke):
            flags.append(Flag(kind, at, said, spoke))
    return sm.ratio(), flags
