"""Regulatory corpus loader.

Reads `agents/grant-compliance/data/regulatory_corpus/manifest.json` and
the section files it indexes. Exposes the corpus to the agent's prompts
via a typed `Corpus` object that tracks per-document verification status
(verbatim / mixed-verbatim-paraphrase / structured-paraphrase / skeleton)
and per-paragraph verbatim markers within mixed files.

The loader is deliberately strict:
  - Missing files raise at load time, not at query time
  - Missing manifest fields raise at load time
  - Verbatim markers must be paired ([VERBATIM_START ...] then [VERBATIM_END])
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Iterable

# Repo root for resolving the corpus directory. This module lives at
# src/grant_compliance/compliance_requirements_agent/corpus.py — five
# parents up is the engine repo root (agents/grant-compliance/).
_ENGINE_ROOT = Path(__file__).resolve().parents[3]
_CORPUS_DIR = _ENGINE_ROOT / "data" / "regulatory_corpus"


VERBATIM_START_RE = re.compile(r"\[VERBATIM_START[^\]]*\]")
VERBATIM_END_RE = re.compile(r"\[VERBATIM_END\]")
HEADER_FENCE_RE = re.compile(r"^={70,}\s*$", re.MULTILINE)
HEADER_FIELD_RE = re.compile(r"^([A-Z_]+):\s*(.*)$", re.MULTILINE)


@dataclass(frozen=True)
class CorpusDocument:
    """One regulation file in the corpus."""

    id: str
    citation: str
    title: str
    path: Path
    compliance_areas: tuple[str, ...]
    subpart: str | None
    verification: str  # verbatim | mixed-verbatim-paraphrase | structured-paraphrase | skeleton
    source_url: str
    verbatim_paragraphs: tuple[str, ...] = field(default_factory=tuple)
    verbatim_source: str | None = None
    verbatim_fetched_at: str | None = None

    # The body text of the file (post-header, pre-footer-fence). Loaded
    # lazily by the Corpus that owns this document.
    body: str = ""

    @property
    def is_citable(self) -> bool:
        """True when the agent may cite content from this document.

        Skeleton files are NOT citable — the agent surfaces them as
        out-of-corpus per the honesty discipline.
        """
        return self.verification != "skeleton"

    @property
    def is_quotable(self) -> bool:
        """True when the agent may QUOTE content directly. Verbatim and
        mixed (within marked paragraphs) are quotable. Paraphrase is
        describable but not quotable as the regulation's exact words.
        """
        return self.verification in ("verbatim", "mixed-verbatim-paraphrase")

    def verbatim_blocks(self) -> list[str]:
        """Return the [VERBATIM_START]...[VERBATIM_END] blocks in the body.

        For verbatim documents the entire body is returned as one block.
        For mixed documents, just the marked sub-paragraphs are returned.
        For paraphrase or skeleton documents, returns an empty list.
        """
        if not self.is_quotable:
            return []
        if self.verification == "verbatim":
            return [self.body.strip()]

        # mixed-verbatim-paraphrase — extract marked blocks
        blocks: list[str] = []
        cursor = 0
        while True:
            start_match = VERBATIM_START_RE.search(self.body, cursor)
            if not start_match:
                break
            end_match = VERBATIM_END_RE.search(self.body, start_match.end())
            if not end_match:
                # Unpaired marker — treat as a corpus integrity issue
                raise CorpusIntegrityError(
                    f"Unpaired [VERBATIM_START] marker in {self.path} "
                    f"at offset {start_match.start()}"
                )
            block = self.body[start_match.end():end_match.start()].strip()
            if block:
                blocks.append(block)
            cursor = end_match.end()
        return blocks


class CorpusIntegrityError(RuntimeError):
    """Raised when the corpus violates its own structural contract."""


@dataclass
class Corpus:
    """The full regulatory corpus — manifest + loaded documents."""

    version: str
    last_updated: str
    regulatory_basis: dict
    verification_statuses: dict
    v1_1_followups: list[dict]
    documents: list[CorpusDocument]
    compliance_area_index: dict[str, list[str]]

    def by_id(self, doc_id: str) -> CorpusDocument | None:
        for d in self.documents:
            if d.id == doc_id:
                return d
        return None

    def by_compliance_area(self, area: str) -> list[CorpusDocument]:
        ids = set(self.compliance_area_index.get(area, []))
        return [d for d in self.documents if d.id in ids]

    def citable(self) -> list[CorpusDocument]:
        return [d for d in self.documents if d.is_citable]

    def skeletons(self) -> list[CorpusDocument]:
        return [d for d in self.documents if d.verification == "skeleton"]

    def full_text_for_prompt(
        self,
        compliance_areas: Iterable[str] | None = None,
        include_skeletons: bool = True,
    ) -> str:
        """Render the corpus as a single text block for inclusion in an LLM
        prompt. Each document is preceded by its citation and verification
        status so the model knows what it can and cannot quote directly.

        Skeleton files are included with their structural template (so the
        model knows the topic exists) but explicitly marked NOT-CITABLE so
        the model refuses to ground requirements on them.
        """
        docs: Iterable[CorpusDocument]
        if compliance_areas is None:
            docs = self.documents
        else:
            wanted_ids: set[str] = set()
            for area in compliance_areas:
                wanted_ids.update(self.compliance_area_index.get(area, []))
            docs = [d for d in self.documents if d.id in wanted_ids]

        sections: list[str] = []
        for doc in docs:
            if doc.verification == "skeleton" and not include_skeletons:
                continue
            quotable = "QUOTABLE" if doc.is_quotable else "DESCRIBE-ONLY"
            if not doc.is_citable:
                quotable = "NOT-CITABLE"
            sections.append(
                f"--- {doc.citation} — {doc.title} "
                f"[verification: {doc.verification}; {quotable}] ---\n"
                f"Source: {doc.source_url}\n\n"
                f"{doc.body.strip()}\n"
            )
        return "\n\n".join(sections)


# ---------------------------------------------------------------------------
# Loader
# ---------------------------------------------------------------------------


def _parse_header(text: str) -> tuple[dict[str, str], str]:
    """Split a corpus file into (header_fields, body). Header is the block
    between the first two fence lines (rows of ====...). Body is everything
    after the second fence and before the closing fence (if present).
    """
    fences = list(HEADER_FENCE_RE.finditer(text))
    if len(fences) < 2:
        raise CorpusIntegrityError(
            "Corpus file is missing the opening + closing header fences"
        )
    header_block = text[fences[0].end():fences[1].start()]
    fields = {m.group(1): m.group(2).strip() for m in HEADER_FIELD_RE.finditer(header_block)}

    # Body — everything after the second fence (which closes the header).
    # If there's a trailing fence, strip up to it. Otherwise to EOF.
    body_start = fences[1].end()
    if len(fences) >= 3:
        body = text[body_start:fences[2].start()]
    else:
        body = text[body_start:]
    return fields, body.strip("\n")


@lru_cache(maxsize=1)
def load_corpus(corpus_dir: Path | None = None) -> Corpus:
    """Load and validate the corpus. Memoized — reuse across requests."""
    base = Path(corpus_dir) if corpus_dir else _CORPUS_DIR
    manifest_path = base / "manifest.json"
    if not manifest_path.exists():
        raise CorpusIntegrityError(f"manifest.json not found at {manifest_path}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    documents: list[CorpusDocument] = []
    for entry in manifest["documents"]:
        file_path = base / entry["path"]
        if not file_path.exists():
            raise CorpusIntegrityError(
                f"manifest references missing file: {entry['path']}"
            )
        text = file_path.read_text(encoding="utf-8")
        try:
            fields, body = _parse_header(text)
        except CorpusIntegrityError as exc:
            raise CorpusIntegrityError(f"{entry['path']}: {exc}") from exc

        # Cross-check: header CITATION must match manifest citation; header
        # VERIFICATION must match manifest verification. Loud failure beats
        # silent drift between the manifest and the file headers.
        if fields.get("CITATION", "").strip() != entry["citation"]:
            raise CorpusIntegrityError(
                f"{entry['path']}: header CITATION {fields.get('CITATION')!r} "
                f"does not match manifest citation {entry['citation']!r}"
            )
        if fields.get("VERIFICATION", "").strip() != entry["verification"]:
            raise CorpusIntegrityError(
                f"{entry['path']}: header VERIFICATION {fields.get('VERIFICATION')!r} "
                f"does not match manifest verification {entry['verification']!r}"
            )

        documents.append(
            CorpusDocument(
                id=entry["id"],
                citation=entry["citation"],
                title=entry["title"],
                path=file_path,
                compliance_areas=tuple(entry["compliance_areas"]),
                subpart=entry.get("subpart"),
                verification=entry["verification"],
                source_url=entry["source_url"],
                verbatim_paragraphs=tuple(entry.get("verbatim_paragraphs", [])),
                verbatim_source=entry.get("verbatim_source"),
                verbatim_fetched_at=entry.get("verbatim_fetched_at"),
                body=body,
            )
        )

    # Validate every mixed-verbatim-paraphrase document has paired markers.
    for d in documents:
        if d.verification == "mixed-verbatim-paraphrase":
            d.verbatim_blocks()  # raises if unpaired

    return Corpus(
        version=manifest["version"],
        last_updated=manifest["last_updated"],
        regulatory_basis=manifest["regulatory_basis"],
        verification_statuses=manifest["verification_statuses"],
        v1_1_followups=manifest.get("v1_1_followups", []),
        documents=documents,
        compliance_area_index=manifest["compliance_area_index"],
    )
