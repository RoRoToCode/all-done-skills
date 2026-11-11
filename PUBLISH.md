# Publish to GitHub

This repository is already committed and tagged (`main` @ `v1.4.1`). The 17
release packages (`*.zip`) are excluded from git on purpose — they are meant
to be attached to a GitHub **Release**, not stored in the repo tree.

> The build environment that produced this snapshot has **no outbound internet
> to github.com**, so the push / release must be run on your own machine (which
> has network + git credentials). These are the exact commands.

## Option A — `gh` CLI (recommended, one pass)

Installed and authenticated `gh` does repo-create, push, and release upload in
one go.

```bash
cd /f/skills

# 1) Create the public repo and push the current branch + tag
gh repo create RoRoToCode/all-done-skills --public --source . --remote origin --push

# 2) Push the version tag (Release is built on it)
git push origin v1.4.1

# 3) Create the Release and attach all 17 packages
gh release create v1.4.1 \
  --title "All Done Skills v1.4.1" \
  --notes-file RELEASE_NOTES.md \
  *.zip
```

Replace `RoRoToCode/all-done-skills` with your GitHub owner/name. If the repo
already exists, skip step 1 and just `git remote add origin <url>` then push.

## Option B — git + GitHub web UI (no `gh`)

```bash
cd /f/skills
git remote add origin https://github.com/RoRoToCode/all-done-skills.git
git push -u origin main
git push origin v1.4.1
```

Then on github.com → open the repo → **Releases → New release** → choose tag
`v1.4.1` → title `All Done Skills v1.4.1` → paste `RELEASE_NOTES.md` content
into the notes → **drag the 17 `*.zip` files** into the attachments → publish.

## What gets published

- **Repo tree** — 17 skill folders + `README.md`, `README.zh.md`, `LICENSE`,
  `CHANGELOG.md`, `RELEASE_NOTES.md`, `PUBLISH.md`, `.gitignore` (321 files).
- **Release `v1.4.1`** — 17 clean, skill-named `.zip` packages, each containing
  the skill folder (no `__pycache__`, `*.pyc`, or test run-residue).

## Notes

- `_local-only/` (test artifacts, old market packages, project memory backup) is
  git-ignored and never published.
- `vramfit/` is a separate project with its own repo; it is also git-ignored here.
- Primary maintenance stays on the WorkBuddy Skills Market; this GitHub repo is a
  read-only source mirror.
