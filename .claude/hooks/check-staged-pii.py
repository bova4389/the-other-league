#!/usr/bin/env python3
"""PreToolUse hook on `git commit`: refuse to commit entrant PII.

Why this exists
---------------
`the-majors-golf`, `basic-bros-ryder-cup` and `the-other-league` are all PUBLIC
repos, and the DreamHost workflows upload ./* to the public webroot. So anything
committed is published twice: in git history permanently, and at a plain URL.

The Majors pool stores real entrant email addresses and phone numbers, which land
on disk in data-archive/**/picks.csv, data-archive/*picks_raw*.json and Picks/.
.gitignore blocks those three paths, but a new export path, a renamed folder, or a
`git add -f` would walk straight past it. This hook is the backstop: it inspects
the actual staged blobs and denies the commit if any real contact detail is in them.

Design notes
------------
* Scans EVERY git repo in the workspace, because the hook cannot tell which repo a
  given `git commit` is aimed at (the command may use `git -C`, a preceding `cd`,
  or just inherit a cwd). Checking all of them is cheap and cwd-independent.
* Reads staged blobs with `git show :<path>` rather than the working tree, so it
  sees exactly what the commit would contain.
* Skips binaries and large blobs.
* Prints counts and filenames only — never the matched values.
* Fails OPEN on internal error: a broken hook must not wedge all committing.
"""
import json
import os
import re
import subprocess
import sys

WORKSPACE = r"C:\Users\bovac\OneDrive\Desktop\Claude Code"

EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.]{2,}")
PHONE = re.compile(r"\b(?:\+?1[-. ]?)?\(?\d{3}\)?[-. ]\d{3}[-. ]\d{4}\b")

# Placeholders and non-personal addresses that must not trigger a block.
ALLOWED_EMAILS = {
    "you@email.com",
    "you@example.com",
    "user@example.com",
    "noreply@anthropic.com",
    "noreply@github.com",
}
# Matt's own number, published on purpose on the BBRC bio-submission page so the
# Bros can text him a photo. It is the site owner's number, not entrant data, and
# has been public since the bio form shipped. Every OTHER phone number still
# blocks — this list exists so one intentional, self-published number does not
# wedge every BBRC commit. Do not add entrants' numbers here.
ALLOWED_PHONES = {
    "317-440-2782",
}


def _normalise_phone(p):
    """Strip formatting so 317-440-2782, (317) 440-2782 and 317.440.2782 match."""
    return re.sub(r"\D", "", p).lstrip("1")


def _is_real_email(e):
    """Reject pinned CDN package specs that parse as an address.

    `globe.gl@2.46.2` in a https://unpkg.com/... URL matches EMAIL as
    local=globe.gl, domain=2, tld=46.2 -- and these projects pin every CDN
    dependency that way, so version bumps would keep wedging commits. A real
    TLD always contains a letter and an all-digits one never does, so this
    drops version specs without loosening detection of actual addresses.
    """
    tld = e.rsplit(".", 1)[-1]
    return any(ch.isalpha() for ch in tld)
# Extensions worth scanning; anything else is treated as opaque.
TEXTY = {
    ".csv", ".json", ".txt", ".md", ".html", ".htm", ".js", ".css", ".py",
    ".yml", ".yaml", ".tsv", ".xml", ".webmanifest", "",
}
MAX_BLOB = 4_000_000


def git(repo, *args):
    try:
        return subprocess.run(
            ["git", "-C", repo, *args],
            capture_output=True, text=True, errors="replace", timeout=30,
        ).stdout
    except Exception:
        return ""


def find_repos(root):
    repos = []
    if os.path.isdir(os.path.join(root, ".git")):
        repos.append(root)
    try:
        for name in os.listdir(root):
            sub = os.path.join(root, name)
            if os.path.isdir(os.path.join(sub, ".git")):
                repos.append(sub)
    except OSError:
        pass
    return repos


def scan_repo(repo):
    """Return list of (path, n_emails, n_phones) for staged blobs containing PII."""
    hits = []
    # numstat marks binary files with '-' so we can skip them
    binary = set()
    for line in git(repo, "diff", "--cached", "--numstat").splitlines():
        parts = line.split("\t")
        if len(parts) == 3 and parts[0] == "-" and parts[1] == "-":
            binary.add(parts[2])
    for path in git(repo, "diff", "--cached", "--name-only").splitlines():
        path = path.strip()
        if not path or path in binary:
            continue
        if os.path.splitext(path)[1].lower() not in TEXTY:
            continue
        blob = git(repo, "show", f":{path}")
        if not blob or len(blob) > MAX_BLOB:
            continue
        emails = {e for e in EMAIL.findall(blob)
                  if e.lower() not in ALLOWED_EMAILS and _is_real_email(e)}
        allowed_digits = {_normalise_phone(p) for p in ALLOWED_PHONES}
        phones = {p for p in PHONE.findall(blob)
                  if _normalise_phone(p) not in allowed_digits}
        if emails or phones:
            hits.append((path, len(emails), len(phones)))
    return hits


def main() -> int:
    try:
        json.load(sys.stdin)  # payload unused; presence confirms hook invocation
    except Exception:
        pass

    try:
        findings = []
        for repo in find_repos(WORKSPACE):
            for path, n_e, n_p in scan_repo(repo):
                findings.append(f"{os.path.basename(repo)}/{path} "
                                f"({n_e} email(s), {n_p} phone number(s))")
    except Exception:
        return 0  # fail open — never wedge committing over a hook bug

    if not findings:
        return 0

    listing = "; ".join(findings[:10]) + ("; ..." if len(findings) > 10 else "")
    reason = (
        "BLOCKED: staged files contain what look like real email addresses or phone "
        f"numbers -> {listing}. These repos are PUBLIC and the DreamHost workflows "
        "upload ./* to the public webroot, so committing would publish personal "
        "contact details in git history permanently and at a plain URL. Unstage them "
        "(git restore --staged <path>) and add the path to .gitignore. Entrant PII "
        "belongs only on disk and in OneDrive, never in git. If this is a false "
        "positive (a placeholder address), add it to ALLOWED_EMAILS in "
        ".claude/hooks/check-staged-pii.py."
    )
    print(json.dumps({
        "systemMessage": "Commit blocked: possible entrant PII in staged files.",
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": reason,
        },
    }))
    return 0


if __name__ == "__main__":
    sys.exit(main())
