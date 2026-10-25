# Consumers (2026-09-29)

Repositories with Actions enabled that call pyrlyn/ci, and the infra commit they pin.

| Repository | Workflow -> infra workflow | Pin | Caller permissions |
| --- | --- | --- | --- |
| The coding agent (main, PR #65 p37-desktop) | ci.yml `rust` -> ci-rust.yml | `189816a` | none on the job (workflow `contents: read`) |
| The coding agent | pipeline.yml -> pipeline.yml (`rust: false`) | `189816a` | `contents: read`, `security-events: write`, `actions: read` |
| The coding agent | release-plz.yml -> release-plz.yml | `189816a` | `contents: write`, `pull-requests: write`, `actions: write` |
| The package manager | ci.yml `rust` -> ci-rust.yml | `059c0c5` | none on the job (workflow `contents: read`) |
| The package manager | pipeline.yml -> pipeline.yml | `189816a` | `contents: read`, `security-events: write`, `actions: read` |
| The package manager | release-apple-desktop.yml -> release-apple-desktop.yml | ci/release-apple-desktop head (repin to the merge commit) | `contents: write`, `actions: read`, `issues: write` |
| The token-reduction CLI | pipeline.yml -> pipeline.yml + `gate` action | `189816a` | `contents: read`, `security-events: write`, `actions: read` |
| The token-reduction CLI | release-plz.yml -> release-plz.yml | `189816a` | `contents: write`, `pull-requests: write`, `actions: write` |

Actions disabled (not consumers today): the bindings generator, crates, cross-code, the build-cache cleaner, the local model runner,
slint_dart, the TypeScript compiler; private airtalk-cli, budget-app, riverpod, slint-dotnet. landing (Pages only)
does not call infra.

## Upgrading a pin past cancel-run (416dbf9 / main 1be9b44)

Every workflow except dependabot-automerge.yml now declares `actions: write`, and GitHub rejects
a nested job that asks for more than its caller grants, even when `cancel-run-on-failure` is
false. Before moving a pin past 416dbf9, change the calling job's permissions:

- ci-rust.yml callers (the coding agent, the package manager `rust` jobs): add `permissions: {contents: read, actions: write}`
  on the job. Where ci.yml is itself called (dependabot.yml `ci` job), that job must grant
  `actions: write` too.
- pipeline.yml callers (the coding agent, the package manager, the token-reduction CLI): `actions: read` -> `actions: write`.
- release-plz.yml callers already grant `actions: write`.

## Upgrading a pin past notify-release-failure

`release.yml`, `release-plz.yml` and `bump.yml` end with a `notify-failure` job that asks for
`issues: write` (a failed release opens a `release-failure` issue; docs/reusable-workflows.md,
"Release failure notifications"). Before moving a pin of any of the three past it, add
`issues: write` to the calling job's permissions, or the run fails at startup.

## Upgrading a pin past main-failure

`ci.yml` gained a `main-failure` job (on by default) that asks for `issues: write`. Before
moving a `ci.yml` pin past it, add `issues: write` to the calling job's permissions, or the run
fails at startup even with `notify-main-failure: false`.
