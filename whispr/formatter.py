"""Text post-processing applied to raw Whisper output before injection.

Pipeline: filler removal -> spoken commands -> user replacements ->
dictionary casing -> punctuation/whitespace tidy -> sentence
capitalization -> optional trailing space (so consecutive dictations
chain naturally, like Wispr Flow).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field


@dataclass
class FormatOptions:
    remove_fillers: bool = True
    capitalize_sentences: bool = True
    trailing_space: bool = True
    spoken_commands: bool = False
    ensure_ending_punctuation: bool = False
    dictionary: tuple[str, ...] = ()
    replacements: dict[str, str] = field(default_factory=dict)


# Standalone hesitation sounds. Boundaries forbid word characters or
# apostrophes on either side so "umbrella", "summer", "hummed" survive.
_FILLER_RE = re.compile(
    r"(?i)(?<![\w'])(?:u+m+|u+h+|erm+|er|a+h+|h+m+|mhm+)(?![\w'])"
)

_NEW_PARAGRAPH_RE = re.compile(r"(?i)[ \t]*[,.!?]?[ \t]*\bnew\s+paragraph\b[,.!?]?[ \t]*")
_NEW_LINE_RE = re.compile(r"(?i)[ \t]*[,.!?]?[ \t]*\bnew\s+line\b[,.!?]?[ \t]*")


def _word_re(term: str) -> re.Pattern:
    return re.compile(rf"(?i)(?<![\w']){re.escape(term)}(?![\w'])")


def _tidy(s: str) -> str:
    s = s.replace("\r\n", "\n")
    s = re.sub(r"[ \t]+", " ", s)
    s = re.sub(r" *\n *", "\n", s)
    s = re.sub(r",(\s*,)+", ",", s)          # duplicate commas left by removals
    s = re.sub(r" +([,.;:!?])", r"\1", s)    # no space before punctuation
    s = re.sub(r",+\s*([.!?])", r"\1", s)    # ", ." -> "."
    s = re.sub(r",(?=[A-Za-z])", ", ", s)    # missing space after comma (keeps 1,000)
    s = re.sub(r"^[\s,.;:!?]+", "", s)       # orphan punctuation after leading-filler removal
    return s.strip()


def _capitalize(s: str) -> str:
    def upper(m: re.Match) -> str:
        return m.group(1) + m.group(2).upper()

    s = re.sub(r"^(\W*)([a-z])", upper, s, count=1)
    s = re.sub(r"([.!?][\"')\]]*\s+)([a-z])", upper, s)
    s = re.sub(r"(\n\s*)([a-z])", upper, s)
    return s


def format_text(text: str, opts: FormatOptions | None = None) -> str:
    opts = opts or FormatOptions()
    s = text or ""

    if opts.remove_fillers:
        s = _FILLER_RE.sub("", s)

    if opts.spoken_commands:
        s = _NEW_PARAGRAPH_RE.sub("\n\n", s)
        s = _NEW_LINE_RE.sub("\n", s)

    for src, dst in (opts.replacements or {}).items():
        if src.strip():
            s = _word_re(src).sub(lambda _m, d=dst: d, s)

    for term in opts.dictionary or ():
        if term.strip():
            s = _word_re(term).sub(lambda _m, t=term: t, s)

    s = _tidy(s)

    if opts.capitalize_sentences:
        s = _capitalize(s)

    if opts.ensure_ending_punctuation and s and s[-1].isalnum():
        s += "."

    if opts.trailing_space and s:
        s += " "
    return s
