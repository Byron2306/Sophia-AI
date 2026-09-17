from __future__ import annotations

from typing import Any, Mapping


REVIEW_TASK = "dio_sophia_academic_review"
REVIEW_SURFACE = "dio_sophia_review"


def resolve_product_review_lane(body: Mapping[str, Any]) -> dict[str, Any]:
    context = body.get("client_context") if isinstance(body.get("client_context"), Mapping) else {}
    selected = (
        body.get("dio_product_review_lane") is True
        and str(body.get("document_evidence_task") or "") == REVIEW_TASK
        and str(context.get("ui_surface") or "") == REVIEW_SURFACE
        and str(context.get("writing_action") or "") == "review"
        and isinstance(body.get("document_uploads"), list)
        and bool(body.get("document_uploads"))
    )
    return {
        "selected": selected,
        "source": "dio_product_review_lane" if selected else "generic_presence",
        "task": str(body.get("document_evidence_task") or ""),
        "ui_surface": str(context.get("ui_surface") or ""),
        "writing_action": str(context.get("writing_action") or ""),
    }


def build_product_review_system_prompt(body: Mapping[str, Any]) -> str:
    lane = resolve_product_review_lane(body)
    if not lane["selected"]:
        raise ValueError("DIO product review lane is not selected")
    return "\n".join([
        "You are Sophia operating as DIO's diagnostic reviewer for an owner-authorised academic manuscript review.",
        "This is a specialist review lane, not generic tutoring or general social Presence.",
        "Act as a diagnostic reviewer. Evaluate argument clarity, method adequacy, evidence-to-claim fit, analytical coherence, limitations, and reference integrity.",
        "Do not rewrite manuscript prose and do not produce submission-ready replacement text.",
        "Preserve human authorship. Final wording, interpretation, and submission decisions remain with the author.",
        "Use only evidence supplied in the request. Do not invent publications, authors, DOIs, findings, data, or sources.",
        "Anchor major comments to supplied paragraph IDs or claim IDs when they are available.",
        "Distinguish manuscript statements from reviewer inference and from what remains unknown.",
        "Use these exact headings when a full review is requested: Overall assessment; Major revisions; Minor revisions; Evidence limits; Author-owned next steps.",
    ])


def build_product_review_prompt(body: Mapping[str, Any], user_text: str) -> str:
    uploads = body.get("document_uploads") or []
    evidence_blocks: list[str] = []
    for upload in uploads:
        if not isinstance(upload, Mapping):
            continue
        name = str(upload.get("source_name") or upload.get("source_path") or "document")
        extracted = str(upload.get("extracted_text") or "")
        spans = upload.get("spans") if isinstance(upload.get("spans"), list) else []
        evidence_blocks.append(f"SOURCE: {name}\nTEXT:\n{extracted}\nSPANS:\n{spans}")
    return "\n\n".join([
        user_text.strip(),
        "CLOSED-WORLD DOCUMENT EVIDENCE:",
        *evidence_blocks,
    ])
