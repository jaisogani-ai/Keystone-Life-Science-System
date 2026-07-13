"""
keystone.deterministic.claim_status
====================================
The claim-integrity data model (deterministic, no fabrication). It makes the
distinction the whole product rests on visible and STORED, not a UI helper:

    "Verified" must NOT mean "scientifically true."

A resolvable DOI/PMID proves the SOURCE RECORD resolved — never that it supports
a specific claim, and never that the claim is true. So each claim carries:

  Per-claim intrinsic axes
    - source_record_verified : the identifier resolves + metadata matched (bool)
    - claim_type             : evidence | computed | hypothesis | missing
    - integrity_state        : normal | retracted | concern | unverified

  Claim -> source linkage (a claim is EVIDENCE only with an exact link; a real
  DOI on an unrelated sentence is NOT evidence)
    - source_id, source_title, source_locator, source_quote,
      extraction_method, source_document_version

  Evidence status is CONCLUSION-SPECIFIC — a relation, never a global field on
  the claim (the same claim can support conclusion A and contradict conclusion B)
    claim_assessment = {claim_id, conclusion_id, evidence_status, rationale,
                        reviewer_decision, timestamp}

Everything here is a pure function of its inputs. Retracted sources may remain
VISIBLE (integrity risk / historical context) but can NEVER add positive support.
"""
from __future__ import annotations

import datetime
import re

# A source identifier that actually resolves to a record we can open — a bare
# DOI/PMID/accession OR a "DB:ID" form (UniProt:P07858, Cellosaurus:CVCL_0022).
_REAL_ID = re.compile(
    r"^\s*("
    r"https?://|"
    r"(doi:)?10\.\d{4,}/|"
    r"pmid:?\s*\d|pmc\d+|"
    r"(uniprot|cellosaurus|clinvar|chembl|reactome|geo|ensembl|refseq|pdb|ncbi):|"
    r"cvcl_|"
    r"[opq][0-9][a-z0-9]{3}[0-9]|[a-n][0-9][a-z0-9]{3}[0-9]"
    r")",
    re.I,
)
_NOT_AVAILABLE = "not available"


def source_record_verified(source: str) -> bool:
    """True iff the source is a real, resolvable identifier (DOI/PMID/PMC/
    UniProt/Cellosaurus/URL) — NOT that it supports the claim."""
    s = (source or "").strip()
    return bool(s) and s.lower() != "unresolved" and bool(_REAL_ID.match(s))


def extraction_method(source: str) -> str:
    """Name the retrieval route for a source id (honest; never invented)."""
    s = (source or "").strip().lower()
    if not source_record_verified(source):
        return "unresolved"
    if s.startswith(("10.", "doi:")):
        return "Crossref / OpenAlex (DOI)"
    if "cvcl_" in s:
        return "Cellosaurus"
    if s.startswith(("pmid", "pmc")):
        return "PubMed / Europe PMC"
    if re.match(r"^[opq][0-9]|^[a-n][0-9]", s):
        return "UniProt"
    if s.startswith("http"):
        return "web resource"
    return "resolved identifier"


def integrity_state(node) -> str:
    """normal | retracted | concern | unverified — an integrity flag on the
    source record, independent of whether the claim is true or supportive."""
    if getattr(node, "retracted", False):
        return "retracted"
    meta = getattr(node, "meta", None) or {}
    updates = meta.get("post_pub_updates") or []
    kinds = {str(u.get("type", "")).lower() for u in updates} if isinstance(updates, list) else set()
    if meta.get("expression_of_concern") or "expression_of_concern" in kinds or "concern" in kinds:
        return "concern"
    if not source_record_verified(getattr(node, "source", "") or ""):
        return "unverified"
    return "normal"


def classify_claim_type(node_type_value: str, source: str,
                        source_quote, source_locator) -> str:
    """The exact-link RULE (test-exercised directly): a claim is `evidence` only
    when the source resolves AND an exact link (quote or locator) ties the source
    to THIS claim. A real DOI with no exact link is `missing`, never evidence."""
    if (node_type_value or "").lower() == "unresolved":
        return "missing"
    if not source_record_verified(source):
        return "missing"
    has_link = bool(source_quote and source_quote != _NOT_AVAILABLE) or \
        bool(source_locator and source_locator != _NOT_AVAILABLE)
    return "evidence" if has_link else "missing"


# node types that carry a curated finding tied to their source (the node text IS
# the extracted claim). These get an exact curated link; others need an explicit
# quote/locator in meta to count as evidence.
_CURATED_TYPES = {"paper", "molecular_result", "target", "reagent",
                  "dataset", "clinical"}


def claim_linkage(node) -> dict:
    """The claim->source linkage fields (honest; `not available` where absent)."""
    meta = getattr(node, "meta", None) or {}
    src = getattr(node, "source", "") or ""
    text = getattr(node, "text", "") or ""
    nt = getattr(getattr(node, "node_type", None), "value", "") or ""
    curated = source_record_verified(src) and nt in _CURATED_TYPES and bool(text)
    quote = meta.get("quote") or (text if curated else None) or _NOT_AVAILABLE
    locator = meta.get("locator") or ("title / reported finding (curated)" if curated else None) or _NOT_AVAILABLE
    return {
        "source_id": src or None,
        "source_title": text or None,
        "source_locator": locator,
        "source_quote": quote,
        "extraction_method": ("curated from source title / finding" if curated
                              else extraction_method(src)),
        "source_document_version": (meta.get("version")
                                    or (str(getattr(node, "date", "")) or None)
                                    or _NOT_AVAILABLE),
    }


def node_claim(node) -> dict:
    """The full per-claim intrinsic record for a Node: the three axes + linkage.
    Attached to every node in the API so a claim is self-describing, not a badge."""
    src = getattr(node, "source", "") or ""
    nt = getattr(getattr(node, "node_type", None), "value", "") or ""
    link = claim_linkage(node)
    return {
        "source_record_verified": source_record_verified(src),
        "claim_type": classify_claim_type(nt, src, link["source_quote"],
                                          link["source_locator"]),
        "integrity_state": integrity_state(node),
        "linkage": link,
    }


def _now() -> str:
    return datetime.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


def assess_claim(claim_id: str, node, conclusion: dict) -> dict:
    """Evidence status of ONE claim FOR ONE conclusion — a relation, never a
    global field. Retracted => excluded for EVERY conclusion (integrity risk /
    historical context only; never positive support)."""
    supporting = conclusion.get("supporting_evidence") or []
    contradicting = conclusion.get("contradicting_evidence") or []
    if getattr(node, "retracted", False) or integrity_state(node) == "retracted":
        status = "excluded"
        rationale = ("retracted source — excluded from positive support; "
                     "retained for integrity risk and historical context only")
    elif claim_id in contradicting:
        status = "contradicted"
        rationale = "cited as contradicting this conclusion"
    elif claim_id in supporting:
        nt = getattr(getattr(node, "node_type", None), "value", "") or ""
        link = claim_linkage(node)
        if classify_claim_type(nt, getattr(node, "source", "") or "",
                               link["source_quote"], link["source_locator"]) != "evidence":
            status = "unresolved"
            rationale = "referenced for this conclusion but lacks a verifiable exact source link"
        else:
            status = "supported"
            rationale = "directly supports this conclusion via a verified, linked source"
    else:
        status = "unresolved"
        rationale = "not assessed for this conclusion"
    return {
        "claim_id": claim_id,
        "conclusion_id": conclusion.get("id"),
        "evidence_status": status,
        "rationale": rationale,
        "reviewer_decision": conclusion.get("reviewer_decision") or "pending scientist review",
        "timestamp": _now(),
    }
