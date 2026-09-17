from __future__ import annotations

import unittest

from arda_os.backend.services.dio_product_review import (
    build_product_review_system_prompt,
    resolve_product_review_lane,
)


class DioProductReviewRoutingTests(unittest.TestCase):
    def test_exact_dio_review_payload_selects_specialist_lane(self) -> None:
        body = {
            "dio_product_review_lane": True,
            "reasoned_integrity_lane": True,
            "document_evidence_task": "dio_sophia_academic_review",
            "document_uploads": [{
                "source_name": "manuscript.md",
                "modality": "academic_manuscript",
                "extracted_text": "A bounded manuscript excerpt.",
                "spans": [{"span_id": "P1", "quote": "A bounded manuscript excerpt."}],
            }],
            "client_context": {
                "ui_surface": "dio_sophia_review",
                "writing_action": "review",
            },
        }
        lane = resolve_product_review_lane(body)
        self.assertTrue(lane["selected"])
        self.assertEqual(lane["source"], "dio_product_review_lane")
        self.assertEqual(lane["task"], "dio_sophia_academic_review")
        self.assertEqual(lane["ui_surface"], "dio_sophia_review")

    def test_generic_presence_request_does_not_enter_product_review_lane(self) -> None:
        self.assertFalse(resolve_product_review_lane({"text": "Hello Sophia"})["selected"])

    def test_specialist_prompt_is_reviewer_not_generic_pedagogy(self) -> None:
        body = {
            "dio_product_review_lane": True,
            "document_evidence_task": "dio_sophia_academic_review",
            "document_uploads": [{
                "source_name": "paper.md",
                "modality": "academic_manuscript",
                "extracted_text": "Claim text.",
                "spans": [{"span_id": "P1", "quote": "Claim text."}],
            }],
            "client_context": {"ui_surface": "dio_sophia_review", "writing_action": "review"},
        }
        prompt = build_product_review_system_prompt(body)
        self.assertIn("diagnostic reviewer", prompt.lower())
        self.assertIn("do not rewrite", prompt.lower())
        self.assertIn("paragraph", prompt.lower())
        self.assertNotIn("zone of proximal development", prompt.lower())


if __name__ == "__main__":
    unittest.main()
