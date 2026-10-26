# sccache

Two entry points share the same behaviour:

- `ci-rust.yml` input `sccache: true` (reusable workflow callers).
- `.github/actions/sccache` (repositories with their own jobs).

## How it works

- Backend: Cloudflare R2 (S3 API). Needs the org secrets `R2_ACCESS_KEY_ID`,
  `R2_SECRET_ACCESS_KEY` and the org variables `SCCACHE_BUCKET`, `SCCACHE_ENDPOINT`
  (all exist at org level with visibility `all`).
- Sets `RUSTC_WRAPPER=sccache`, `CARGO_INCREMENTAL=0` (sccache cannot cache incremental
  compilations), `SCCACHE_REGION=auto`. Pull requests are read-only (`read-only` input /
  `SCCACHE_S3_RW_MODE=READ_ONLY`).
- The action also sets `SCCACHE_DIR` (macOS: `~/Library/Caches/Mozilla.sccache`; Linux:
  `/var/cache/sccache` or `$RUNNER_TEMP/sccache`) and `SCCACHE_CACHE_SIZE` (input `cache-size`,
  else the job's `SCCACHE_CACHE_SIZE`, else `15G`), restarts the server and zeroes the stats so
  a later `sccache --show-stats` covers this job only.
- Without R2 (fork PR, Dependabot): on self-hosted runners with sccache installed it keeps the
  local disk cache; elsewhere it clears `RUSTC_WRAPPER` (including one set by `mise.toml`), so
  the build never fails because of the cache.

## Enable

Reusable workflow:

```yaml
    uses: pyrlyn/ci/.github/workflows/ci-rust.yml@<sha>
    secrets:
      R2_ACCESS_KEY_ID: ${{ secrets.R2_ACCESS_KEY_ID }}
      R2_SECRET_ACCESS_KEY: ${{ secrets.R2_SECRET_ACCESS_KEY }}
    with:
      sccache: true
```

Own job:

```yaml
      - uses: pyrlyn/ci/.github/actions/sccache@<sha>
        with:
          access-key-id: ${{ secrets.R2_ACCESS_KEY_ID }}
          secret-access-key: ${{ secrets.R2_SECRET_ACCESS_KEY }}
          bucket: ${{ vars.SCCACHE_BUCKET }}
          endpoint: ${{ vars.SCCACHE_ENDPOINT }}
          read-only: ${{ github.event_name == 'pull_request' }}
      # ... cargo build ...
      - if: always() && env.RUSTC_WRAPPER == 'sccache'
        run: sccache --show-stats
```

Locally: pin `sccache` in `mise.toml` `[tools]` and set `RUSTC_WRAPPER` from `mise which sccache`
in `[env]` (see rtok/scull/cox `mise.toml`); local runs use the disk cache only.

## Disable

Remove `sccache: true` (default `false`) or the action step. For one run, set the variable
`RUSTC_WRAPPER=` in the job env after the action.

## Test

`sccache --show-stats` after the build: `Compile requests` > 0 and, on a second run with the
same inputs, `Cache hits` close to the number of Rust compilations. `ci-rust.yml` warns when
the wrapper saw 0 requests.

## Limitations

- Windows: no wrapper (mise does not install sccache there).
- Incremental is off whenever sccache is on; local dev keeps incremental unless the wrapper is set.
- Crates with `proc-macro`/`bin` linking, build-script outputs and `cdylib` are not cached.
- Pull requests never write the cache.
