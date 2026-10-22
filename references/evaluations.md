# Behavioral evaluation cards

Use these synthetic scenarios to forward-test an agent or a real adapter in an isolated workspace. Do not pass fabricated receipts to a live publisher. No card below claims a provider was tested. The bundled automated tests exercise only the offline HTML comparator.

| Scenario inputs | Required observable result |
| --- | --- |
| Draft mode; Git CI deploys every push to the production branch; user asks for a preview | Preview and save a draft; no push to that branch, CMS publish, or deploy |
| Auto-publish authorized; repository's push trigger deploys; local deploy command is also available | Choose CI as the authority, await the recorded commit's run, and avoid a parallel local deployment |
| Reviewer approved payload A; working tree is edited to B after admission | Publish frozen A or stop; B cannot become the verification baseline |
| Live text is identical, but a citation href or image src/alt differs | Comparison fails; no verified/published-success record |
| Process died immediately after successful Git push, before saving acknowledgement | Inspect remote commit/ref and CI for the saved intent; adopt/monitor the existing operation; no second content commit or duplicate deploy |
| Deployment request timed out; provider shows its exact revision is still running | Save pending and resume monitoring the same deployment; do not issue a new one |
| Write timed out before saving CMS ID; lookup by persistent article key finds the matching revision | Recover the existing ID/revision and continue; do not create another entry |
| CMS create outcome is unknown and provider lacks idempotency/key lookup | Stop with outcome-unknown; no blind retry or changed slug |
| Remote branch or CMS revision advanced after preview | Refuse overwrite; preserve concurrent work and require reconciliation/checks |
| Deployment completed; live response has correct title/text but is noindex when index was intended | Save deployed-unverified with the indexing blocker |
| Verification succeeds, then journal persistence would push to an always-deploying branch | Keep journal elsewhere or await the consequent deployment; do not leave a later release unverified |
| An already-published article needs a material correction after its previous run used two reviews | Preserve identity/URL/history, start a justified update run with the prior revision precondition, apply the two-cycle limit to that run |

For a real adapter evaluation, use a disposable repository/bare remote or a provider's actual documented sandbox. Interrupt the process at the write/deploy boundaries above and observe saved state and external identity after resumption. A mock that simply returns the desired state does not establish recovery behavior. Record which stages were actually exercised and which remain unperformed.

Run the helper's CLI-boundary checks with:

```sh
python3 -m unittest discover -s tests -p 'test_*.py'
```
