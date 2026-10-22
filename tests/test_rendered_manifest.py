"""Public CLI contract tests, with local artifacts; no provider or deployment proof.

Owner-boundary justification: production's CLI must reject identical visible text
with changed citation/image destinations, stale/malformed inputs, or blocked runtime
indexing. Each case exercises a distinct false-positive risk; no fake publisher or
test-only production seam is used.
"""

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "scripts" / "rendered_manifest.py"
FIXTURE = (ROOT / "tests" / "fixtures" / "article.html").read_text(encoding="utf-8")
URL = "https://example.invalid/guides/example/"


class ManifestCliTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.work = Path(self.temp.name)
        self.expected_html = self.work / "expected.html"
        self.expected_html.write_text(FIXTURE, encoding="utf-8")
        self.expected = self.work / "expected.json"
        self.headers = self.work / "headers.json"
        self.headers.write_text(json.dumps({"Content-Type": "text/html; charset=utf-8", "X-Robots-Tag": []}))
        built = self.run_cli("snapshot", self.expected_html, "--url", URL, "--indexing", "index", "--out", self.expected)
        self.assertEqual(built.returncode, 0, built.stderr)

    def run_cli(self, *args):
        return subprocess.run([sys.executable, str(CLI), *map(str, args)], text=True, capture_output=True, check=False)

    def verify(self, html=FIXTURE, status=200, url=URL):
        observed = self.work / "observed.html"
        observed.write_text(html, encoding="utf-8")
        self.receipt = self.work / "receipt.json"
        return self.run_cli("verify", self.expected, observed, "--url", url, "--status", status, "--headers", self.headers, "--out", self.receipt)

    def test_matching_artifacts_and_benign_serialization_changes(self):
        changed = FIXTURE.replace('<article id="article-body">', '<article class="new-css-name" id="article-body" data-render="fresh">')
        changed = changed.replace('"@type":"Article","headline":"Example shortcut checklist"', '"headline":"Example shortcut checklist","@type":"Article"')
        result = self.verify(changed)
        self.assertEqual(result.returncode, 0, result.stderr)
        receipt = json.loads(self.receipt.read_text())
        self.assertEqual(receipt["status"], "matched")
        self.assertEqual(receipt["deploymentCheck"], "not-performed")
        self.assertEqual(receipt["browserCheck"], "not-performed")

    def test_meaningful_changes_block_even_when_page_title_is_unchanged(self):
        cases = {
            "citation-destination": ('https://example.invalid/source-a/', 'https://example.invalid/source-b/'),
            "image-source": ('/images/diagram-a.svg', '/images/diagram-b.svg'),
            "image-alt": ('Two sample windows side by side', 'One sample window'),
            "heading-level": ('<h2 id="start">Start with one shortcut</h2>', '<h3 id="start">Start with one shortcut</h3>'),
            "description": ('A neutral synthetic publishing fixture.', 'An unreviewed description.'),
            "jsonld-date": ('"2026-01-01"', '"2026-02-01"'),
            "code-whitespace": ('left = 1', 'left  = 1'),
            "word-boundary": ('Read the <a', 'Read the<a'),
        }
        for name, (before, after) in cases.items():
            with self.subTest(name=name):
                result = self.verify(FIXTURE.replace(before, after))
                self.assertEqual(result.returncode, 1, result.stderr)
                receipt = json.loads(self.receipt.read_text())
                self.assertEqual(receipt["status"], "blocked")
                self.assertTrue(receipt["differences"])

    def test_http_identity_and_indexing_are_required_observations(self):
        for status, url, headers in [
            (404, URL, {"content-type": "text/html"}),
            (200, "https://example.invalid/wrong/", {"content-type": "text/html"}),
            (200, URL, {"content-type": "text/plain"}),
            (200, URL, {"content-type": "text/html", "x-robots-tag": ["all", "googlebot: NOINDEX"]}),
            (200, URL, {"content-type": "text/html", "x-robots-tag": "none"}),
        ]:
            with self.subTest(status=status, url=url, headers=headers):
                self.headers.write_text(json.dumps(headers))
                result = self.verify(status=status, url=url)
                self.assertEqual(result.returncode, 1, result.stderr)
                self.assertTrue(json.loads(self.receipt.read_text())["errors"])

    def test_missing_artifact_overwrites_an_old_success_receipt(self):
        self.assertEqual(self.verify().returncode, 0)
        self.headers.unlink()
        result = self.verify()
        self.assertEqual(result.returncode, 2)
        self.assertEqual(json.loads(self.receipt.read_text())["status"], "not-performed")

        self.expected_html.unlink()
        failed_snapshot = self.run_cli("snapshot", self.expected_html, "--url", URL, "--indexing", "index", "--out", self.expected)
        self.assertEqual(failed_snapshot.returncode, 2)
        self.assertEqual(json.loads(self.expected.read_text())["status"], "not-performed")

    def test_ambiguous_article_and_invalid_structured_data_cannot_pass(self):
        for html in [FIXTURE.replace('</main>', '<article>Another article</article></main>'), FIXTURE.replace('"@type":"Article"', '"@type":undefined')]:
            with self.subTest(html=html):
                result = self.verify(html)
                self.assertEqual(result.returncode, 2)
                self.assertEqual(json.loads(self.receipt.read_text())["status"], "not-performed")

    def test_noindex_preview_policy_is_supported_explicitly(self):
        preview = FIXTURE.replace('content="index, follow"', 'content="noindex, follow"')
        self.expected_html.write_text(preview)
        built = self.run_cli("snapshot", self.expected_html, "--url", URL, "--indexing", "noindex", "--article-id", "article-body", "--out", self.expected)
        self.assertEqual(built.returncode, 0, built.stderr)
        self.assertEqual(self.verify(preview).returncode, 0)


if __name__ == "__main__":
    unittest.main()
