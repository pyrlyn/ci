# SKIP_CI_TESTS: skip only the test-running steps

`SKIP_CI_TESTS=true` turns off the steps that *run* tests in CI and nothing else. Formatting,
clippy, `cargo check`, builds, `cargo nextest archive` (test compilation), CodeQL, Semgrep and
the gate keep running.

## How it works

Every test-running step has a step-level condition:

```yaml
if: >-
  ... && !inputs.skip-tests && vars.SKIP_CI_TESTS != 'true' && env.SKIP_CI_TESTS != 'true'
```

- `vars.SKIP_CI_TESTS`: Actions variable at organization or repository level. Variables are
  visible inside reusable workflows, so thin callers of `ci.yml` / `pipeline.yml` /
  `ci-rust.yml` inherit it without any change.
- `env.SKIP_CI_TESTS`: workflow- or job-level `env` of the workflow that owns the step.
- `inputs.skip-tests` (`ci-rust.yml`, `ci-dotnet.yml`): explicit `workflow_call` input,
  default `false`.

A skipped step shows as skipped (grey) and its job still succeeds, so the job-level check and
`pipeline / gate` stay green (the gate fails only on `failure`; `skipped` passes). A companion
step prints `::notice title=SKIP_CI_TESTS::tests skipped by SKIP_CI_TESTS` in the run summary.
`ci-dotnet.yml` runs `dotnet build` instead of `dotnet test`.

Gated in this repository: `ci-rust.yml` (`test`, `doctests`, both jobs), `ci-dotnet.yml`
(`dotnet test`), `license-tests.yml` (`Tests`). Repositories with their own test steps gate
them with the same condition.

## Enable

```sh
gh variable set SKIP_CI_TESTS --org pyrlyn --body true --visibility all   # every repository
gh variable set SKIP_CI_TESTS --body true -R pyrlyn/<repo>                # one repository
```

## Disable

```sh
gh variable delete SKIP_CI_TESTS --org pyrlyn
gh variable delete SKIP_CI_TESTS -R pyrlyn/<repo>
```

A repository variable overrides the organization one, so `--body false` on a repository
re-enables its tests while the org flag is on.

## Test

Set the repository variable, re-run CI on a pull request, and check that `test`/`doctests`
are skipped, the notice is shown and `pipeline / gate` is green. Delete the variable afterwards.

## Limitations

- Only the value `true` (lowercase) counts.
- Tests that run inside a build or script step (e.g. a `just ci` recipe) are not covered
  unless that step is split or checks `$SKIP_CI_TESTS` itself.
- Coverage jobs, benchmarks and release workflows are not test gates and are not affected.
- Turn it off as soon as possible: regressions merged while it is on are not caught.
