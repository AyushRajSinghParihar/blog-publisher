# Offline rendered article comparison

`scripts/rendered_manifest.py` uses only Python's standard library and performs no network, Git, CMS, or deployment operations. It reads supplied HTML and headers. Its result means those supplied artifacts match; the adapter must establish their provenance and deployment association.

## Commands

Create the expected manifest from the exact approved production/preview output with the **production canonical URL** and intended indexing policy:

```sh
python3 scripts/rendered_manifest.py snapshot expected.html --url https://example.invalid/guides/example/ --indexing index --article-id article-body --out expected.json
```

Use `--article-tag article` (the default) or `--article-tag main` when there is no stable content ID. Selection must identify exactly one element. Choose the element enclosing the reviewed article; do not scope it so narrowly that citations, illustrations, or a substantive section are missed. A scope choice belongs to the reviewed manifest.

For live verification, the adapter captures the actual final URL, HTTP status, response headers, and serialized live HTML. Supply the headers as a JSON object whose values are strings or arrays of strings:

```json
{"content-type": "text/html; charset=utf-8", "x-robots-tag": []}
```

```sh
python3 scripts/rendered_manifest.py verify expected.json observed.html --url https://example.invalid/guides/example/ --status 200 --headers response-headers.json --out verification.json
```

Exit 0 means the supplied document matches and supplied HTTP/indexing observations pass; exit 1 means a verification mismatch; exit 2 means invalid input or inability to perform comparison. The JSON receipt records hashes and differences. Invalid input cannot produce a passed receipt. `snapshot` itself is not a live check.

Always require the current process's exit code and fresh receipt. Input-data failures overwrite a requested output with `not-performed`; argument parsing or unwritable paths can prevent any receipt from being saved. `comparedAt` dates this offline comparison, not the live capture or deployment.

`manifestSha256` and `expectedManifestSha256` hash the exact expected JSON file bytes; save and compare this value with the reviewed publication record. HTML hashes also cover the supplied file bytes. `semanticSha256` uses canonical JSON so object key ordering does not affect semantic comparison.

## What is compared

- Final URL and exactly one canonical URL, the document title/language/base URL, relevant named/property metadata (description, crawler directives, Open Graph, Twitter).
- The selected element's ordered HTML content, headings, text, meaningful attributes, link destinations, image source/alt/srcset, accessible labels and table semantics. Relative `href`, `src`, `poster`, and `cite` resolve against the document URL/base.
- Parsed JSON-LD values from the whole document. Object key order and order of separate JSON-LD script blocks do not create mismatches; array order remains meaningful.
- HTTP 200, HTML content type, and indexing policy across supplied HTML crawler metadata and all supplied X-Robots-Tag values. `none` implies `noindex`. An unrecognized crawler-qualified header is not silently treated as an affirmative index permission.

Whitespace outside `pre`/`code` is normalized; class names, inline CSS, comments, and data attributes are excluded. These exclusions are for semantic content comparison, not a claim of pixel equality. Source hashes retain the original input identity even when semantic output matches.

## Limits requiring other checks

This is an HTML parser, not a browser or full HTML5 tree builder. Use serialized browser DOM for documents relying on optional-tag repair or JavaScript-generated content. It does not evaluate computed visibility, CSS layout, image loading/rights, link availability, accessibility quality, schema validity, robots.txt rules, sitemap membership, source accuracy, provider revisions, or deployment completion. `alt` equality does not prove the description is accurate.

Use real preview/browser checks and actual provider receipts for those tasks. The helper does not authenticate artifacts: approve/store the expected manifest hash and capture observed artifacts through the actual adapter. Never fabricate header/status files for a live run. Dynamic article content needs an explicit narrow reviewed comparison policy or a deterministic capture; the helper has no broad ignore switch.
