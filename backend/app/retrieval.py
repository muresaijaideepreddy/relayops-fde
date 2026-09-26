"""Transparent lexical baseline; no embedding or semantic-search claim."""

from dataclasses import dataclass
import re

from .schemas import Citation


STOP_WORDS = frozenset(
    "a an and are as at be been but by can cannot could do does for from had has have how i in is it its me my no not of on or our please should that the their them there these they this to update us was we were what when which will with would you your".split()
)
INJECTION_PATTERN = re.compile(
    r"ignore\s+(?:all\s+)?(?:previous|prior|your|the)\s+instructions|"
    r"reveal.{0,80}(?:secret|api.?key|system.?prompt)|"
    r"bypass.{0,40}(?:approval|policy|rules)|system\s+prompt",
    re.IGNORECASE | re.DOTALL,
)


@dataclass(frozen=True)
class EvidenceDocument:
    id: str
    tenant_id: str
    title: str
    content: str


def tokens(text: str) -> set[str]:
    result = set()
    for token in re.findall(r"[a-z0-9]+", text.lower()):
        if len(token) < 3 or token in STOP_WORDS:
            continue
        # Only simple plural normalization; this does not infer semantic similarity.
        if token.endswith("s") and not token.endswith(("ss", "us")) and len(token) > 4:
            token = token[:-1]
        result.add(token)
    return result


def suspicious_instructions(text: str) -> bool:
    return bool(INJECTION_PATTERN.search(text))


def retrieve(
    query: str, documents: list[EvidenceDocument], tenant_id: str, limit: int = 3
) -> list[Citation]:
    query_terms = tokens(query)
    if not query_terms or suspicious_instructions(query):
        return []
    ranked = []
    for doc in documents:
        # Defense in depth: callers also scope the database query.
        if doc.tenant_id != tenant_id or suspicious_instructions(doc.content):
            continue
        title_terms = tokens(doc.title)
        best = None
        # Windows retain exact source text and include the tail of long documents.
        for start in range(0, len(doc.content), 600):
            excerpt = doc.content[start : start + 900]
            matched = query_terms & tokens(excerpt)
            if len(matched) < 2:
                continue
            score = min(
                1.0, (len(matched) + 0.5 * len(query_terms & title_terms)) / len(query_terms)
            )
            candidate = Citation(
                document_id=doc.id, title=doc.title, excerpt=excerpt, score=round(score, 4)
            )
            if best is None or candidate.score > best.score:
                best = candidate
        if best is not None:
            ranked.append(best)
    return sorted(ranked, key=lambda c: (-c.score, c.document_id))[:limit]
