#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
import urllib.request
from pathlib import Path


BASE = "http://127.0.0.1:7070"


def get_json(path: str) -> dict:
    with urllib.request.urlopen(BASE + path, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def post_json(path: str, payload: dict) -> dict:
    req = urllib.request.Request(
        BASE + path,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", "Accept": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=180) as response:
        return json.loads(response.read().decode("utf-8"))


def main() -> int:
    health = get_json("/api/health")
    payload = {
        "text": (
            "Review this short manuscript excerpt diagnostically. Identify the most important "
            "argument and evidence weaknesses. Do not rewrite it."
        ),
        "session_token": health.get("session_token") or "",
        "dio_product_review_lane": True,
        "reasoned_integrity_lane": True,
        "document_evidence_task": "dio_sophia_academic_review",
        "document_uploads": [{
            "source_name": "phase7_manuscript.md",
            "source_path": "phase7_manuscript.md",
            "mime_type": "text/markdown",
            "modality": "academic_manuscript",
            "parser": "plain_text",
            "extracted_text": (
                "P1. This study argues that structured feedback improves learning outcomes. "
                "The argument is based on observations from one small class, but the manuscript "
                "currently generalises the conclusion to all university students.\n\n"
                "P2. No comparison group was used and the manuscript does not explain how "
                "learning improvement was measured."
            ),
            "spans": [
                {"span_id": "P1", "label": "P1", "quote": "This study argues that structured feedback improves learning outcomes."},
                {"span_id": "P2", "label": "P2", "quote": "No comparison group was used."},
            ],
        }],
        "client_context": {
            "ui_surface": "dio_sophia_review",
            "writing_action": "review",
            "response_mode": "detailed",
        },
        "disable_continuity_memory": True,
        "disable_world_events": True,
        "suppress_academic_retrieval_fastpaths": True,
    }
    result = post_json("/api/speak", payload)
    assert result.get("source") == "dio_product_review_lane", result
    assert result.get("dio_product_review_lane") is True, result
    assert result.get("document_evidence_task") == "dio_sophia_academic_review", result
    assert result.get("ui_surface") == "dio_sophia_review", result
    assert result.get("authority_created") is False, result
    assert result.get("release_authority") is False, result
    assert result.get("external_send_authority") is False, result
    assert "qwen2.5:0.5b" in str(result.get("model") or ""), result
    response = str(result.get("response") or "").strip()
    assert len(response) >= 80, result
    lower = response.lower()
    assert "rewrite" not in lower[:80], result
    out = Path(sys.argv[1] if len(sys.argv) > 1 else "/tmp/sophia-live-review.json")
    out.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(f"SOPHIA_DIO_OLLAMA_REVIEW_VERIFIED model={result.get('model')} chars={len(response)}")
    print(str(out))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
