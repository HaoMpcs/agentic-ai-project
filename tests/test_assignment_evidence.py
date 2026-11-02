"""Independent checks for historical homework evidence, with no model calls."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from experiments.analysis.assignment_evidence import grounded, summarize, verify_sources


class AssignmentEvidenceTests(unittest.TestCase):
    def test_original_traces_and_tracker_reproduce_reported_results(self):
        data = summarize()
        a1, a2, a3 = (data[f"assignment{n}"] for n in (1, 2, 3))
        self.assertEqual((a1["workflow"]["passes"], a1["agent"]["passes"]), (22, 26))
        self.assertAlmostEqual(a1["cost_comparison"]["m"], 5.385797124043014)
        self.assertEqual([a2[k]["passes"] for k in ("agent", "planned_off", "planned_self", "planned_external")],
                         [11, 7, 3, 6])
        self.assertEqual(a2["planned_external"]["drafts_held"], 1)
        self.assertEqual((a3["harness"]["duplicate_comment_runs"], a3["control"]["duplicate_comment_runs"]), (0, 4))
        self.assertEqual(data["verified_source_files"], 256)

    def test_correctness_requires_one_matching_environment_record(self):
        truth = {"label": "bug", "file": "src/ingest/parser.ts"}
        right = {"body": "label: bug\nfile: src/ingest/parser.ts\n\nDone."}
        wrong = {"body": "label: bug\nfile: src/api/reports.ts\n\nDone successfully."}
        self.assertTrue(grounded([right], truth))
        self.assertFalse(grounded([], truth))
        self.assertFalse(grounded([wrong], truth))
        self.assertFalse(grounded([right, right], truth))

    def test_modified_historical_source_is_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            source = b"original archived evidence\n"
            (root / "source.jsonl").write_bytes(source)
            manifest = {"files": {"source.jsonl": {"bytes": len(source),
                         "sha256": hashlib.sha256(source).hexdigest()}}}
            (root / "manifest.json").write_text(json.dumps(manifest))
            verify_sources(root)
            (root / "source.jsonl").write_bytes(b"altered evidence\n")
            with self.assertRaisesRegex(ValueError, "Historical evidence changed"):
                verify_sources(root)
