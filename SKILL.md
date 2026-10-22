---
name: blog-publisher
description: Prepare, preview, publish, or resume a reviewed blog article through the site's actual CMS API or Git deployment workflow, preserving the approved revision and preventing duplicate publication. Use for publication and substantive updates; this skill does not supply a CMS integration or deployment credentials.
license: MIT
---

Publish one reviewed revision to one stable article identity, and verify the resulting live page. Default to a draft when mode or publication authorization is unspecified. Honor an existing explicit publishing configuration; do not ask again for authorization it already provides.

## Discover the real publishing path

Read the site's authoring rules, content schemas, package scripts, deployment workflows, current publication records, and relevant configuration. Identify whether a CMS write, Git push, CI job, or local command actually changes production. A push can itself publish. Never push a draft to a deployment branch merely to test connectivity.

Use [the adapter and recovery contract](references/publishing-contract.md) before implementing an adapter, publishing, updating, or resuming. Record the discovered capabilities and exact missing tools/access. Use the existing integration if sufficient; do not claim that this skill provides a working site adapter. Consult current official API documentation when adapter behavior is uncertain.

Check that the host runner actually enforces the required gates. Reading this skill does not repair its code: if it cannot freeze inputs, reconcile unknown outcomes, or identify the completed deployment, report the implementation gap and block unattended publication until an authorized adapter change supplies it.

Select **one deployment authority** per run. If Git CI deploys pushes, push the approved commit once and await that exact commit's deployment; do not also deploy locally. Local locking cannot coordinate a CI provider. Journal-only updates must not trigger an unobserved production deployment.

## Freeze the reviewed publication

- Keep a stable `articleId` and a new `runId` for each creation or substantive update. A retry retains both. Preserve old runs. Review cycles belong to the run; at most two cycles are allowed per run. An unresolved major issue blocks that run, and creating another run solely to evade failed reviews is not permitted.
- Require final factual and reader-usefulness review for the **exact** payload, plus required source, link, metadata, image rights/alt, indexing, and desktop/mobile preview checks. An absent check is `not-performed`, never passed. This skill verifies publication, not the truth of source claims or image permissions.
- Bind a manifest to the reviewed revision, payload/assets hashes, relevant configuration, expected canonical URL, preview evidence, reviewer reports, and intended visibility. If the CMS transforms payloads, preview and approve that transformation too.
- Freeze the Git commit or immutable build artifact for Git publishing. For a CMS, freeze the request payload plus expected existing CMS revision. Build or submit from that frozen input; do not rebuild from a changing working directory. Changes invalidate the applicable review/checks.
- Updating preserves the article/CMS identity and URL. Record the previous revision as a write precondition; use the CMS's revision/ETag condition or a guarded Git ancestry check. Explain material corrections and use the actual update date according to site rules.

## Publish and recover

Preflight adapter tools, access, branch/CMS permissions, deployment target, unique identity, frozen inputs, and checks before the first external mutation. Never print credentials. In draft mode finish the preview and saved record; stop before any action capable of changing production.

Before each external write, durably save the intended operation, stable idempotency key, expected base revision, and current stage. Save acknowledgements, external IDs and revision/deployment IDs as they become known. On timeout or interruption, reconcile with the actual CMS/Git/CI state before retrying; an unknown outcome is not permission to create again. Stop on conflicting edits, ambiguous identity, or a newer production revision. Details and stage-specific next actions are in the contract.

Wait for the selected authority's successful deployment of the recorded commit/revision. Verify the live URL afterwards against the frozen expected output, including meaningful link/image attributes and metadata, then save the verified revision and time. Text equality alone is insufficient. A failed verification records `deployed-unverified`, not an unpublished draft or a successful publication. Report the exact stage and blocker.

## Optional deterministic HTML check

The bundled **offline** helper compares serialized HTML without networking or publishing:

```sh
python3 scripts/rendered_manifest.py snapshot preview.html --url https://example.invalid/guides/example/ --indexing index --article-tag article --out expected.json
python3 scripts/rendered_manifest.py verify expected.json live.html --url https://example.invalid/guides/example/ --status 200 --headers response-headers.json --out verification.json
```

Paths above are illustrative and resolve relative to this skill when invoking its script. Read [helper usage and limits](references/rendered-manifest.md) before using its result as evidence. It cannot observe deployment completion, browser layout, JavaScript rendering, robots.txt, sitemap content, or source accuracy. Those require the actual adapter and checks. Save the helper's expected manifest hash in the reviewed publication record.

Use [behavioral evaluation scenarios](references/evaluations.md) when implementing or changing publication behavior. Synthetic scenarios establish only the behavior actually exercised; they never establish live CMS or deployment success.
