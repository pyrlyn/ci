# Consumer migration to ci.yml (proposal B)

Per repository: the thin callers to add, the config, and what to delete. `<SHA>` is the infra
commit this lands as (then Dependabot moves it, see _common/github-dependabot.yml).
Nothing here is committed to a consumer repository yet.

| Repo | Add / replace | Delete | Keep local |
| --- | --- | --- | --- |
| the coding agent | ci.yml, .github/infra.yml, dependabot.yml, sync-docs.yml; release-plz.yml pin | pipeline.yml, sonarcloud.yml | release.yml (own publish-then-tag flow), nightly.yml (manual fuzz), .github/actions/{rust,bwrap} (used by release.yml / scripts) |
| the coding agent PR #65 | + infra.p37-desktop.patch.yml merged into .github/infra.yml; desktop inline steps -> scripts/desktop/{lint,ci}.sh | same | same |
| the package manager | ci.yml, .github/infra.yml, dependabot.yml, sync-docs.yml, bump.yml, release-plz.yml | pipeline.yml, sonarcloud.yml, verify.yml | release.yml + tap.yml (cargo-dist generated / dist custom job), review.yml (`/review`), .github/actions/rust |
| the token CLI | ci.yml, .github/infra.yml, dependabot.yml, sync-docs.yml, bump.yml; release-plz.yml pin | pipeline.yml, sonarcloud.yml, verify.yml | release.yml (dist), marketplace.yml (manual, repo tooling) |

Check names change: `pipeline / gate` -> `ci / gate` (no repository has required checks or
branch protection today, so nothing blocks on the old name).
