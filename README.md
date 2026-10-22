# Blog publisher

A reusable agent skill for publishing an exact reviewed article through a site's actual CMS API or Git/deployment workflow. It defines adapter discovery, preview gates, immutable publication inputs, duplicate prevention, update runs, interruption recovery, and live verification.

Start with [SKILL.md](SKILL.md). The package includes supporting contracts, synthetic evaluation scenarios, and a Python helper for comparing rendered article manifests.

## Install

Clone this repository into a skill directory supported by your agent, for example:

```sh
git clone https://github.com/AyushRajSinghParihar/blog-publisher.git .agents/skills/blog-publisher
```

Use `$blog-publisher` with the reviewed article revision and the target project's publishing configuration.

## Capability boundary

This package is not a CMS integration or deployment service. The host agent must inspect the project's actual workflow, select one deployment authority, and establish a capable adapter before changing publication state. Unsupported or missing capabilities remain explicit blockers. Draft mode prepares a preview without publishing.

The rendered-manifest helper compares supplied HTML. It does not deploy, fetch authenticated pages, verify source truth or image rights, inspect screenshots, or prove which commit a server deployed. The publishing workflow must separately establish those facts and retain the evidence.

See the bundled references for helper usage and behavioral evaluation. Synthetic tests are not live publication evidence.

## Check the helper

The helper requires Python and uses only its standard library:

```sh
python3 scripts/rendered_manifest.py --help
python3 -m unittest discover -s tests -p 'test_*.py'
```

See [the publishing contract](references/publishing-contract.md), [HTML comparison guide](references/rendered-manifest.md), and [evaluation scenarios](references/evaluations.md).

## Privacy

The package contains neutral fixtures, not a site's configuration. Store credentials outside the repository and keep real publication journals, private CMS identifiers, preview tokens, and browser artifacts in the consuming project's appropriate storage. Do not add them here.

## License

[MIT](LICENSE).
