"""Keyword lexicon and text cleaning used by the keyword baseline router.

The word lists are generic telco and lab vocabulary, and many patterns match no challenge item.
The same author wrote the lists and the challenge set, and the items the baseline gets wrong
were mostly written against these lists; each one is recorded in the set with the reason.
"""

import re
from collections.abc import Mapping

from faultline_noc.router.models import Agent

FLAGS = re.IGNORECASE | re.MULTILINE

AGENT_PATTERNS: Mapping[Agent, tuple[re.Pattern[str], ...]] = {
    Agent.KNOWLEDGE: tuple(
        re.compile(pattern, FLAGS)
        for pattern in (
            r"\bexplain\w*",
            r"\bwhat (?:is|are|does|do)\b",
            r"\bhow (?:does|do|is|are)\b",
            r"\bdescrib\w*",
            r"\bdocs?\b",
            r"\bdocumentation\b",
            r"\bguide\b",
            r"\bwalk me through\b",
            r"\bteach\b",
            r"\btutorial\b",
            r"\bdifference between\b",
            r"\bsummari[sz]e\b",
            r"\boverview\b",
            r"\blesson\b",
            r"\bconcepts?\b",
            r"\bdefin\w*",
        )
    ),
    Agent.TESTING: tuple(
        re.compile(pattern, FLAGS)
        for pattern in (
            r"\bre-?run\b",
            r"\brun\b",
            r"\btests?\b",
            r"\bexecut\w*",
            r"\bsmoke\b",
            r"\bregression\b",
            r"\bbenchmark\w*",
            r"\bvalidat\w*",
            r"\bverif\w*",
            r"\biperf\b",
            r"\bsuite\b",
        )
    ),
    Agent.INCIDENT: tuple(
        re.compile(pattern, FLAGS)
        for pattern in (
            r"\bwhy\b",
            r"\broot cause\b",
            r"\brca\b",
            r"\balarms?\b",
            r"\boutages?\b",
            r"\bspik\w*",
            r"\blatency\b",
            r"\bdown\b",
            r"\bfail\w*",
            r"\bcrash\w*",
            r"\bdegrad\w*",
            r"\bincidents?\b",
            r"\btroubleshoot\w*",
            r"\bdiagnos\w*",
            r"\binvestigat\w*",
            r"\bpacket loss\b",
            r"\bdrop\w*",
            r"\berrors?\b",
            r"\btime-?outs?\b",
            r"\bbroken\b",
            r"\bunreachable\b",
            r"\bflap\w*",
            r"\bwrong\b",
            r"\bstuck\b",
        )
    ),
}

WRITE_IMPERATIVE = re.compile(
    r"^\s*(?:(?:please|kindly|now|also|then|and|go ahead and|can you|could you|would you"
    r"|i need you to|i want you to|we need to|let's)\s+)*"
    r"(?:restart|reboot|roll ?back|scale|redeploy|drain|cordon|fail ?over|delete|kill"
    r"|shut ?down)\b",
    FLAGS,
)
WRITE_TARGET = re.compile(
    r"\b(?:amf|smf|upf|nrf|gnb|ausf|udm|pcf|nssf)(?:-\d+)?\b"
    r"|\b(?:pods?|cnfs?|deployments?|nodes?|replicas?|release|cluster|statefulset)\b",
    FLAGS,
)
LEFT_CURLY_QUOTE = chr(0x201C)
RIGHT_CURLY_QUOTE = chr(0x201D)
QUOTED_SPAN = re.compile(
    rf'"[^"]*"|{LEFT_CURLY_QUOTE}[^{RIGHT_CURLY_QUOTE}]*{RIGHT_CURLY_QUOTE}|`[^`]*`'
)
LOG_LINE = re.compile(
    r"^\s*(?:>|\d{4}-\d{2}-\d{2}|\[[\w:.-]+\]|(?:INFO|WARN|WARNING|ERROR|DEBUG|CRITICAL)\b).*$",
    re.MULTILINE,
)
REPORTED_SPEECH = re.compile(
    r"\b(?:says|said|reads|wrote|writes|contains)\s*:[ \t]*\n?[^.?!\n]*", FLAGS
)
INJECTION_MARKERS: tuple[re.Pattern[str], ...] = tuple(
    re.compile(pattern, FLAGS)
    for pattern in (
        r"\bignore (?:all |any |the |your )?(?:previous |prior |above )?instructions\b",
        r"\bdisregard\b",
        r"^\s*system\s*:",
        r"\bsystem override\b",
        r"\byou are now\b",
        r"\bnew instructions\b",
        r"\bdeveloper mode\b",
    )
)
SENTENCE_BREAK = re.compile(r"(?<=[.!?])\s+|\n+")
CLAUSE_BREAK = re.compile(
    r",?\s+(?:and\s+)?then\s+|,?\s+after that,?\s+|,?\s+afterwards,?\s+|;\s*|,?\s+and\s+"
    r"|,\s+also\s+",
    FLAGS,
)


def strip_quoted_material(request: str) -> str:
    """Remove quoted spans, pasted log lines and reported speech, which carry no user intent."""
    without_quotes = QUOTED_SPAN.sub(" ", request)
    without_logs = LOG_LINE.sub(" ", without_quotes)
    return REPORTED_SPEECH.sub(" ", without_logs)


def is_injected(sentence: str) -> bool:
    """Return True when a sentence carries a known instruction-override phrase."""
    return any(marker.search(sentence) for marker in INJECTION_MARKERS)


def user_clauses(request: str) -> tuple[str, ...]:
    """Return the clauses of the request that carry the user's own intent, in order."""
    cleaned = strip_quoted_material(request)
    sentences = [part for part in SENTENCE_BREAK.split(cleaned) if part.strip()]
    kept = [sentence for sentence in sentences if not is_injected(sentence)]
    clauses = [clause.strip(" ,.") for sentence in kept for clause in CLAUSE_BREAK.split(sentence)]
    return tuple(clause for clause in clauses if clause)


def agent_scores(clause: str) -> dict[Agent, int]:
    """Return how many of each agent's patterns match the clause."""
    return {
        agent: sum(1 for pattern in patterns if pattern.search(clause))
        for agent, patterns in AGENT_PATTERNS.items()
    }


def is_write_command(clause: str) -> bool:
    """Return True when the clause opens with an imperative that changes network state."""
    return WRITE_IMPERATIVE.search(clause) is not None


def names_write_target(clause: str) -> bool:
    """Return True when a write clause names what it would change."""
    return WRITE_TARGET.search(clause) is not None
