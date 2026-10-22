# Adapter, identity, and recovery contract

Use this when selecting or implementing the actual site's publication path. It is an interface contract, not an installed backend. Reuse the repository's record format if it preserves these invariants.

## Capability discovery and preflight

Record which values are discovered, verified, unavailable, or unknown:

| Capability | Evidence to obtain |
| --- | --- |
| Production mutation | Existing CMS API/tool, repository workflow trigger, or deploy command; identify side effects of every push/write |
| Authority | One owner of deployment; selected CI workflow/environment, CMS publish operation, or authorized direct deployment |
| Destination | Actual site/account/environment, canonical origin, repository/branch or CMS collection |
| Access | Available authenticated tool and required permission; check nonmutating identity/access endpoints where supported |
| Identity/query | Lookup by saved external ID and a stable external article key; enough pagination to rule out duplicates |
| Conflict protection | CMS revision/ETag conditions or Git base/remote ancestry; determine whether branch protection requires a PR |
| Idempotency | Provider support and retention, or a persistent unique external key with lookup; URL/title alone is not an atomic uniqueness guarantee |
| Preview | Existing preview/build/runtime, revision binding, intended crawler visibility |
| Completion | API revision status or CI run/deployment that identifies the exact expected commit and target |
| Verification | Canonical page/body, links/images/meta/schema, HTTP behavior, robots/sitemap where intended, actual rendered browser checks |

Inspect real CI triggers before deciding a Git push is harmless. If direct writes are prohibited, prepare the PR with the approved payload and follow the actual merge/deploy path; do not bypass protection. A pending review or missing production credential is a named blocker. No test credential or simulated success replaces it.

For a CMS without atomic uniqueness/idempotency, serialize all writes through one authority, query by stable key immediately before creation, and reconcile uncertain outcomes. If independent writers cannot be coordinated and duplicate-free creation cannot be guaranteed, state that limitation and stop before unattended creation. Never infer global safety from a process-local lock.

## Saved publication record

Persist records outside a temporary process directory. Use atomic replacement and durable writes appropriate to the store; retain stage history, not just a final boolean. Keep credentials and raw private responses out of public records.

```json
{
  "articleId": "example-article",
  "runId": "example-update-02",
  "operation": "update",
  "mode": "draft",
  "reviewedRevision": "reviewed-content-digest",
  "reviewCyclesUsed": 2,
  "reviewStatus": "passed",
  "payloadSha256": "digest-of-exact-payload",
  "expectedManifestSha256": "digest-of-reviewed-rendered-manifest",
  "canonicalUrl": "https://example.invalid/guides/example/",
  "externalId": "existing-cms-or-git-path-id",
  "expectedBaseRevision": "previous-approved-revision",
  "authority": {"kind": "git-ci", "target": "configured-production-target"},
  "frozenInput": {"commit": "approved-commit", "artifactSha256": "built-artifact-digest"},
  "stage": "prepared",
  "operations": [],
  "deployment": null,
  "verification": {"status": "not-performed"}
}
```

These are illustrative field names, not valid identities or verified data. Add toolchain/environment hashes when build output depends on them. Bind associated assets and CMS transformation settings; hashing article text alone does not bind its rendered citations, figures, or surrounding publication behavior.

Each operation has an immutable key derived from `articleId`, `runId`, payload hash, and operation type. Record `intentAt`, expected base, attempted target, and then the observed receipt. A timeout leaves the receipt unknown. The same key must not be reused with a changed payload.

## Creation, updates, and concurrency

- **Create:** query the saved external identity/key; adopt an existing object only if its identity and revision match this operation. An object at the intended slug with different content is a conflict, not a reason to select another slug.
- **Update:** retain `articleId`, external ID, canonical URL, and prior run. Create a new revision run, complete its required checks, and compare-and-set the expected prior revision. Refuse unexpected concurrent edits. Do not delete old reviewer findings to regain review cycles.
- **Git:** keep the reviewed commit immutable. Immediately before push, refresh remote state and verify the expected base/ancestry. Push without force, using branch protections as configured. A newer remote head requires reconciliation and new checks if relevant inputs change. Deploy the frozen commit/artifact, not whatever `HEAD` or the working tree later becomes.
- **CMS:** use the adapter's conditional update/version endpoint. If it lacks conflict protection, do not call an unguarded overwrite safe; reconcile and serialize within the actual available guarantees.
- **CI:** monitor the workflow/deployment for the recorded commit, environment, and repository. A green run for another commit does not qualify. Coordinate ordering across all authorities; cancel/suppress an obsolete deployment or stop rather than overwrite newer production.

## Stage-specific recovery

| Saved stage | Read actual state | Allowed next action |
| --- | --- | --- |
| `prepared` | Check frozen inputs and whether any recorded write intent has an unknown result | Submit only if no write occurred; otherwise reconcile first |
| `write-requested` | CMS lookup by stable key/version, or remote Git ref plus commit ancestry | Adopt the matching write; stop on conflict; retry the same idempotent operation only when outcome is resolved |
| `written` | Confirm recorded CMS revision/commit exists and still belongs to this identity | Request publication/deployment through the single authority |
| `deployment-requested` | Find the authority's run/deployment by exact commit/revision and target | Resume monitoring an existing operation; do not launch a second deployment because the caller timed out |
| `deployed-unverified` | Confirm expected deployment completed and remains current; fetch the real page | Repeat verification; do not redeploy an older payload over a newer one |
| `verified` | If asked to retry, confirm recorded revision is still current | Return/reverify that identity; do not create or deploy again |
| `blocked` | Inspect the precise failed precondition and saved external receipts | Resolve deliberately; retain history and unknown outcomes |

Use bounded polling suited to the provider; save a pending status when a job exceeds it. A transient 404/cache delay is not proof that no deployment happened. Do not treat cancellation as a confirmed rollback. Rollback is a separate authorized operation with its own frozen target and verification.

If process death occurred before saving a returned external ID, the intent key and external lookup must recover it. If the provider cannot identify whether the write happened, stop with `outcome-unknown`; blind retry risks duplication. Recovered acknowledgements remain distinct from observed live verification.

## Completion and verification

Only verify after the selected authority confirms completion of the exact expected revision. Capture requested and final URL, status, relevant response headers, capture time, deployment identity, and expected/observed content digests. Avoid changing production to perform a verification.

Compare rendered article content including numbers, order, headings, link destinations, image sources/alt, relevant metadata and parsed structured data. Confirm canonical URL and intended robots directives in HTML and HTTP headers. Separately check actual robots.txt for the intended crawler/path and sitemap inclusion when intended. For intentional `noindex`, verify it remains applied and do not require search inclusion. A static match does not replace browser rendering checks.

If content is transformed by a CMS, approve a preview of that transformation and its manifest before release. Ignore dynamic fields only through an explicit reviewed rule with narrow scope; do not exclude citations or article body to make a comparison pass.

Save `verifiedAt` only after these observations. A deployment followed by a failed/missing check is `deployed-unverified`. Reverification must update the persistent record if it is reported as saved. Journal-only commits must use a route that does not trigger another unobserved release; if the repository deploys every push, keep runtime journals elsewhere or explicitly await every resulting deployment.
