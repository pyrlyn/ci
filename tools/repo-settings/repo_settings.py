#!/usr/bin/env python3
"""Apply and verify the shared `main` protection and auto-merge setting for one repository.

Template: the rtok/ketch rulesets ("Block force push to main" and "protect-main").
Required status checks: only the template contexts that have actually run on the
repository's recent `main` commits, so a check that never runs cannot block merges.
allow_auto_merge: on for public repositories, off for private ones.
Rulesets need a public repository on the Free plan; private repositories get the
auto-merge half only and a notice. Exits non-zero on any mismatch left after apply.

Env: GH_TOKEN (admin scope), REPO (owner/name), MODE (apply|verify), COMMITS (default 15).
Stdlib only.
"""
import json
import os
import sys
import urllib.error
import urllib.request

API = "https://api.github.com"
TEMPLATE_CHECKS = [
    "pipeline / gate", "rust / plan", "rust / fmt",
    "rust / x86_64-unknown-linux-gnu", "rust / aarch64-unknown-linux-gnu",
    "rust / aarch64-apple-darwin", "rust / x86_64-pc-windows-msvc",
    "commits", "powershell", "macos-app", "ketch-ffi", "design",
    "package (macos-latest, aarch64-apple-darwin)",
    "package (ubuntu-latest, x86_64-unknown-linux-gnu)",
    "package (windows-latest, x86_64-pc-windows-msvc)",
]
CONDITIONS = {"ref_name": {"include": ["refs/heads/main"], "exclude": []}}
PR_RULE = {"type": "pull_request", "parameters": {
    "required_approving_review_count": 0, "dismiss_stale_reviews_on_push": False,
    "required_reviewers": [], "require_code_owner_review": False,
    "require_last_push_approval": False, "required_review_thread_resolution": False,
    "allowed_merge_methods": ["merge", "squash", "rebase"]}}


def api(method, path, body=None):
    req = urllib.request.Request(API + path, method=method,
                                 data=json.dumps(body).encode() if body is not None else None)
    req.add_header("Authorization", "Bearer " + os.environ["GH_TOKEN"])
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("X-GitHub-Api-Version", "2022-11-28")
    try:
        with urllib.request.urlopen(req) as r:
            data = r.read()
            return r.status, json.loads(data) if data else None
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read() or b"null")
        except ValueError:
            return e.code, None


def existing_checks(repo, n):
    seen = set()
    _, commits = api("GET", f"/repos/{repo}/commits?sha=main&per_page={n}")
    for c in commits or []:
        sha = c["sha"]
        _, runs = api("GET", f"/repos/{repo}/commits/{sha}/check-runs?per_page=100")
        seen |= {r["name"] for r in (runs or {}).get("check_runs", [])}
        _, st = api("GET", f"/repos/{repo}/commits/{sha}/status")
        seen |= {s["context"] for s in (st or {}).get("statuses", [])}
    return seen


def desired(required):
    rules = [{"type": "deletion"}, {"type": "non_fast_forward"}, PR_RULE]
    if required:
        rules.append({"type": "required_status_checks", "parameters": {
            "strict_required_status_checks_policy": False, "do_not_enforce_on_create": True,
            "required_status_checks": [{"context": c} for c in required]}})
    return {
        "protect-main": {"name": "protect-main", "target": "branch", "enforcement": "active",
                         "conditions": CONDITIONS, "rules": rules,
                         "bypass_actors": [{"actor_id": 5, "actor_type": "RepositoryRole",
                                            "bypass_mode": "pull_request"}]},
        "Block force push to main": {"name": "Block force push to main", "target": "branch",
                                     "enforcement": "active", "conditions": CONDITIONS,
                                     "bypass_actors": [], "rules": [{"type": "non_fast_forward"}]},
    }


def contexts(rules):
    return {c["context"] for r in rules if r["type"] == "required_status_checks"
            for c in r["parameters"]["required_status_checks"]}


def satisfies(cur, want):
    """True when `cur` is at least as strict as `want` (extra rules/contexts are kept)."""
    if cur.get("enforcement") != "active":
        return False
    if {r["type"] for r in want["rules"]} - {r["type"] for r in cur["rules"]}:
        return False
    return contexts(want["rules"]) <= contexts(cur["rules"])


def merge_up(cur, want):
    """Union: never drop a rule, context or bypass entry the ruleset already has."""
    body = json.loads(json.dumps(want))
    types = {r["type"] for r in body["rules"]}
    for r in cur["rules"]:
        if r["type"] not in types:
            body["rules"].append(r)
    extra = contexts(cur["rules"]) - contexts(body["rules"])
    if extra:
        rsc = [r for r in body["rules"] if r["type"] == "required_status_checks"]
        if not rsc:
            rsc = [{"type": "required_status_checks", "parameters": {
                "strict_required_status_checks_policy": False, "do_not_enforce_on_create": True,
                "required_status_checks": []}}]
            body["rules"].append(rsc[0])
        rsc[0]["parameters"]["required_status_checks"] += [{"context": c} for c in sorted(extra)]
    body["bypass_actors"] = cur.get("bypass_actors", body["bypass_actors"])
    return body


def main():
    if not os.environ.get("GH_TOKEN", "").strip():
        print("::error::REPO_ADMIN_TOKEN is not set (GH_TOKEN empty); "
              "add a token with Administration: read/write")
        return 1
    repo, mode = os.environ["REPO"], os.environ.get("MODE", "apply")
    errors = []
    st, info = api("GET", f"/repos/{repo}")
    if st != 200:
        print(f"::error::cannot read {repo}: HTTP {st}")
        return 1
    public = not info["private"]
    want_am = public
    if info.get("allow_auto_merge") is None:
        errors.append("allow_auto_merge not visible: the token lacks admin scope")
    elif info["allow_auto_merge"] != want_am:
        if mode == "apply":
            s, _ = api("PATCH", f"/repos/{repo}", {"allow_auto_merge": want_am})
            if s != 200:
                errors.append(f"allow_auto_merge -> {want_am}: HTTP {s}")
            else:
                print(f"allow_auto_merge set to {want_am}")
        else:
            errors.append(f"allow_auto_merge is {info['allow_auto_merge']}, want {want_am}")
    else:
        print(f"allow_auto_merge = {want_am} (ok)")

    if not public:
        print("::notice::private repository: rulesets need a paid plan, protection skipped")
    else:
        seen = existing_checks(repo, int(os.environ.get("COMMITS", "15")))
        required = [c for c in TEMPLATE_CHECKS if c in seen]
        omitted = [c for c in TEMPLATE_CHECKS if c not in seen]
        print("required checks: " + (", ".join(required) or "none"))
        print("omitted (never ran here): " + (", ".join(omitted) or "none"))
        s, lst = api("GET", f"/repos/{repo}/rulesets")
        if s != 200:
            errors.append(f"list rulesets: HTTP {s}")
            lst = None
        by_name = {r["name"]: r["id"] for r in lst or []}
        for name, want in desired(required).items() if lst is not None else []:
            if name in by_name:
                _, cur = api("GET", f"/repos/{repo}/rulesets/{by_name[name]}")
                if satisfies(cur, want):
                    print(f"ruleset '{name}' ok")
                    continue
                if mode != "apply":
                    errors.append(f"ruleset '{name}' differs")
                    continue
                s, _ = api("PUT", f"/repos/{repo}/rulesets/{by_name[name]}", merge_up(cur, want))
            else:
                if mode != "apply":
                    errors.append(f"ruleset '{name}' missing")
                    continue
                s, _ = api("POST", f"/repos/{repo}/rulesets", want)
            if s in (200, 201):
                print(f"ruleset '{name}' applied")
            else:
                errors.append(f"ruleset '{name}': HTTP {s}")
    for e in errors:
        print(f"::error::{e}")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
