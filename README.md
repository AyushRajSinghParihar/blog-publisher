# Blog publisher

A reusable agent skill for taking an approved blog article through the site's actual publishing workflow and checking the resulting live page. It keeps the reviewed revision fixed, preserves article identity across retries and updates, and requires uncertain outcomes to be reconciled before another write.

The package has two parts:

| Part | What it supplies |
| --- | --- |
| [Agent instructions](SKILL.md) | A workflow for discovering the site's CMS or Git deployment path, checking readiness, recording publication stages, and verifying the exact approved revision |
| [Offline Python helper](scripts/rendered_manifest.py) | A repeatable comparison of supplied HTML, including citation destinations, image attributes, headings, metadata, and parsed JSON-LD |

**This is not a CMS integration or deployment service.** It installs no provider adapter, scheduler, server, credentials, or production configuration. The agent must use or implement a capable adapter for the target site. Reading these instructions does not add missing enforcement to an existing runner. Unsupported capabilities remain explicit blockers.

The helper performs no network requests, Git pushes, CMS writes, or deployments. A matching receipt establishes agreement between the supplied artifacts; it does not establish that they came from a live deployment. Source accuracy, image rights, browser rendering, robots.txt, sitemap behavior, and provider completion require separate actual checks.

## Prerequisites

For the **offline helper**, use Python 3 with its standard library; no `pip` packages or account access are needed. Run `python3 --version` to check the interpreter. The helper's executable checks and their scope are described in [VALIDATION.md](VALIDATION.md).

For **actual publishing**, the host agent needs the reviewed article and evidence, the site's authoring rules/configuration, a working preview process, and authenticated access to the real CMS or Git/CI system. Its adapter must support stable identity lookup, conflict detection, outcome reconciliation, and identification of the completed production revision. The [publishing contract](references/publishing-contract.md) explains what must be discovered and which gaps block unattended publication. An adapter is the site's working integration, not an extra component bundled here.

## Install

From the target project's root, clone the complete package into a skill directory supported by your agent:

```sh
git clone https://github.com/AyushRajSinghParihar/blog-publisher.git .agents/skills/blog-publisher
```

Alternatively, place a downloaded copy at `.agents/skills/blog-publisher`. Keep `SKILL.md`, `references/`, and `scripts/` together. Skill discovery locations depend on the host agent; this path is a project-local example. Reload the agent session if it discovers skills only at startup.

Invoke it in the target project, for example:

> Use $blog-publisher to inspect this project's publishing workflow and prepare a draft preview of the reviewed article. Identify the exact reviewed revision, save the publication record, and report missing checks or adapter capabilities. Keep mode draft; do not publish.

For a permitted publication or retry, name the saved article/run record and the existing authorized mode. The agent must inspect that record and the real external state before acting; changing a slug is not a retry strategy.

## Try the offline helper

The following example uses only the bundled fictional fixture. Run the entire block **from this package's root**: if installed as above, first `cd .agents/skills/blog-publisher`. It copies the fixture into a disposable private directory, creates an expected manifest, and compares another copy with synthetic HTTP observations. It makes no network requests, including to the intentionally unusable `example.invalid` URL.

```sh
(
set -eu
publisher_skill_dir="$(pwd -P)"
umask 077
publisher_demo_dir="$(mktemp -d "${TMPDIR:-/tmp}/blog-publisher-demo.XXXXXX")"
cd "$publisher_demo_dir"

cp "$publisher_skill_dir/tests/fixtures/article.html" reviewed.html
python3 "$publisher_skill_dir/scripts/rendered_manifest.py" snapshot reviewed.html \
  --url https://example.invalid/guides/example/ \
  --indexing index --article-id article-body --out expected.json

cp reviewed.html observed.html
cat > response-headers.json <<'JSON'
{"content-type":"text/html; charset=utf-8","x-robots-tag":[]}
JSON

python3 "$publisher_skill_dir/scripts/rendered_manifest.py" verify expected.json observed.html \
  --url https://example.invalid/guides/example/ \
  --status 200 --headers response-headers.json --out verification.json

python3 -m json.tool verification.json
printf 'Demo files: %s\n' "$publisher_demo_dir"
cd "$publisher_skill_dir"
)
```

`snapshot` prints `status: snapshot-created` and the expected manifest's SHA256. `verify` exits successfully and writes a receipt containing these fields, among others:

```json
{
  "status": "matched",
  "scope": "supplied-artifacts-only",
  "errors": [],
  "differences": [],
  "deploymentCheck": "not-performed",
  "browserCheck": "not-performed",
  "robotsAndSitemapCheck": "not-performed"
}
```

This is a plumbing exercise, not live verification: the observation is a copied fixture and the headers/status are synthetic. For a real run, the site's adapter must capture the actual response after the recorded deployment completes. Do not substitute example observations for those captures. Keep the printed directory to inspect the files, then remove that disposable directory when finished.

| Exit code | Meaning |
| --- | --- |
| `0` | A snapshot was created, or supplied observations matched the expected manifest |
| `1` | Verification ran and found a content, URL, HTTP, or indexing mismatch; receipt status is `blocked` |
| `2` | Input or execution error prevented a valid comparison; a receipt may be `not-performed` or unavailable |

Always check the current process's exit code and fresh receipt. A previous JSON file is not evidence that a new invocation succeeded. See the [HTML comparison guide](references/rendered-manifest.md) for selector choices, exact hash semantics, comparison scope, and limitations.

## Connect it to a real site

Use one deployment authority per run. Discover what actually changes production before issuing any write: a Git push may already trigger a release.

| Site workflow | Integration responsibility |
| --- | --- |
| CMS API | Freeze the reviewed request payload and any approved CMS transformation. Query the stable article key, use provider idempotency/conditional revisions where available, and retain the returned content and publication IDs. |
| Git with deployment CI | Freeze the approved commit or artifact, honor branch protection, push through the configured path, and await the deployment for that exact commit and environment. Do not also run a local deployment. |
| Authorized direct deployment | Build/deploy the frozen approved input through the existing command, retain its revision/deployment receipt, and coordinate with any other release mechanism. |

The adapter must enforce the required reviews and preview checks before mutation. A draft run stops before anything capable of changing production. After the selected authority completes the expected revision, capture the live page and compare it with the reviewed output; separately complete the site's required browser, crawler, sitemap, and other checks. Save `verified` only when all required checks actually pass. The helper's `matched` receipt alone cannot set that state.

Publication records track progress through `prepared`, `write-requested`, `written`, `deployment-requested`, `deployed-unverified`, and `verified`. A blocker can occur at any stage. If deployment happened but a check failed, preserve `deployed-unverified`; do not relabel it an unpublished draft. These are the adapter contract's states, not a persistence engine provided by this package.

Retries keep the same `articleId`, `runId`, payload hash, and operation key. After a timeout, inspect the CMS/Git/CI state and adopt the matching existing operation before retrying. If the outcome cannot be determined, stop with the precise unknown outcome. A substantive update uses a new `runId` while preserving article/CMS identity and canonical URL, names the prior revision as a precondition, and retains old reviews and receipts. Each legitimate run allows at most two review cycles; a new run cannot be created just to evade failed reviews.

Use the detailed [adapter and recovery contract](references/publishing-contract.md) when implementing these behaviors. The [evaluation cards](references/evaluations.md) provide synthetic interruption and concurrency cases to exercise; they are not evidence of a tested live provider integration.

## Resources and checks

| Resource | Read or run it for |
| --- | --- |
| [SKILL.md](SKILL.md) | Agent entrypoint and workflow requirements |
| [Publishing contract](references/publishing-contract.md) | Adapter capabilities, identity, durable records, conditional updates, and recovery |
| [HTML comparison guide](references/rendered-manifest.md) | CLI options, hashes, supplied HTTP observations, and comparison limits |
| [Evaluation cards](references/evaluations.md) | Behavioral cases for a real adapter or isolated agent evaluation |
| [Helper script](scripts/rendered_manifest.py) | Creating and comparing offline semantic manifests |
| [CLI tests](tests/test_rendered_manifest.py) | Executable local contract checks using the bundled [fixture](tests/fixtures/article.html) |
| [Validation scope](VALIDATION.md) | What was checked and what remains outside the package's evidence |

Run these commands from this package's root:

```sh
python3 scripts/rendered_manifest.py --help
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -p 'test_*.py'
```

## Troubleshooting

| Result | Action |
| --- | --- |
| Agent cannot find the skill | Confirm the host's skill directory and reload its session. Keep the whole package together. |
| Script or fixture not found | Start the quickstart in the package root. In project automation, use the script's absolute path; input/output paths are relative to the caller's current directory. |
| No capable CMS/CI adapter | Report the missing capability and prepare only permitted draft artifacts. Installing this package does not configure a provider. |
| Article selector finds zero or multiple elements | Use a unique `--article-id`, or the correct `--article-tag`; include the full reviewed content and citations. |
| Indexing mismatch | Check actual HTML and X-Robots-Tag observations against the intended policy. A `noindex` preview manifest is not an approved indexable production manifest. |
| Content differs despite identical visible text | Inspect `differences`: link destinations, image attributes, metadata, and JSON-LD can change without changing displayed prose. Do not weaken the comparison to obtain a pass. |
| JavaScript or dynamic markup makes captures differ | Capture the actual serialized browser DOM and use a deterministic reviewed scope. The helper does not execute JavaScript or offer a broad ignore switch. |
| An interrupted write/deploy has no acknowledgement | Reconcile by saved operation key, stable article identity, exact commit/revision, and deployment target before sending another write. |

## Keep site data private

This repository contains neutral fixtures. Store actual payloads, manifests, response captures, journals, unpublished drafts, account/CMS identifiers, preview URLs/tokens, browser state, and credentials in the consuming project's appropriate private storage. They can expose unpublished content or account relationships even when no secret token is present.

Do not commit those artifacts to this package or include real site data in public examples/issues. Treat `.gitignore` as a convenience, not a privacy guarantee: inspect every staged change before publishing. Use sanitized synthetic reproductions for public bug reports.

## License

[MIT](LICENSE).
