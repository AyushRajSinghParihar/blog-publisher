# Validation scope

Checks performed before initial publication:

- Skill frontmatter validation and resolution of packaged relative references.
- Six Python CLI-boundary tests, including content mutations, HTTP/indexing observations, invalid inputs, and stale-success receipt handling. These operate on neutral local artifacts.
- An independent synthetic interruption scenario: a timed-out push was reconciled to an existing commit and pending CI run, with one deployment authority and no duplicate push/deploy. The reviewer retained the frozen reviewed version over a newer unreviewed checkout, rejected identical-text/different-citation verification, and required reconciliation when the remote advanced.
- Public-package inspection for credentials, private local paths, site configuration, and publication artifacts. The repository begins with fresh history; no private project history is included.

No real CMS write, Git publication transaction, CI deployment, live-page fetch, browser preview, robots.txt check, or sitemap verification was performed for this package. Recovery scenarios describe required behavior; they are not integration tests. The offline helper authenticates neither supplied artifacts nor deployment identity. Those checks belong to an actual capable adapter and must remain unperformed or blocked until exercised.
