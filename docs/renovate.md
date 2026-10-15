# Renovate

pyrlyn uses the hosted [Mend Renovate GitHub App](https://github.com/apps/renovate) (free for
open-source and public repositories; no paid plan). This repository no longer runs a
self-hosted Renovate: the `renovate.yml` workflow and the `renovate/` configs were removed so
that the two setups do not open duplicate pull requests.

The shared preset lives in [pyrlyn/.github](https://github.com/pyrlyn/.github)
(`renovate-config.json`). Each public repository has a small `renovate.json` that extends
`local>pyrlyn/.github:renovate-config`. The preset enables cargo, github-actions, npm and mise,
turns automerge off, runs once a week (Monday, Europe/Kiev) and allows 3 open PRs at a time.

Limitation of the hosted app: updating `mise.lock` runs `mise lock`, an unsafe execution that
only self-hosted `allowedUnsafeExecutions: ["mise"]` permits
([docs](https://docs.renovatebot.com/self-hosted-configuration/#allowedunsafeexecutions)). The
hosted app still bumps the tool versions in `mise.toml`, but `mise.lock` has to be refreshed
by hand (`mise lock`) in the same PR.

Where the CLA check ([`cla.yml`](cla.md)) is enabled, `renovate[bot]` is already allowlisted.
