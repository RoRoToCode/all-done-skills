# Release assets

Each GitHub Release of this repository attaches **one `.zip` per skill**.
Download a skill's zip, unzip it into your agent's skills directory, restart
the session.

> The source code of every skill already lives in this repository (one folder
> per skill). The zips are convenience packages for agents that install skills
> by dropping a folder — they contain exactly the same files.

## File → skill map (v1.4.1)

Each asset is named after its skill; the folder **inside** the zip is the same
name.

| Asset | Skill |
| --- | --- |
| `ai-prompt-reader.zip` | `ai-prompt-reader` |
| `archive-all-done.zip` | `archive-all-done` |
| `audio-all-done.zip` | `audio-all-done` |
| `av-transcribe.zip` | `av-transcribe` |
| `data-all-done.zip` | `data-all-done` |
| `doc-data-extract.zip` | `doc-data-extract` |
| `ebook-all-done.zip` | `ebook-all-done` |
| `file-all-done.zip` | `file-all-done` |
| `image-all-done.zip` | `image-all-done` |
| `ocr-workshop.zip` | `ocr-workshop` |
| `office-all-done.zip` | `office-all-done` |
| `pdf-workshop.zip` | `pdf-workshop` |
| `pipeline-all-done.zip` | `pipeline-all-done` |
| `privacy-all-done.zip` | `privacy-all-done` |
| `text-all-done.zip` | `text-all-done` |
| `video-all-done.zip` | `video-all-done` |
| `web-capture.zip` | `web-capture` |

These packages were rebuilt from the clean source tree (no `__pycache__`,
`*.pyc`, or test run-residue such as `ext.md` / `idx.json` / `.pdf-workshop`).

## Install

```bash
# WorkBuddy
unzip <asset>.zip -d ~/.workbuddy/skills/

# Other agents (Claude Code, Codex CLI, Cursor, Cline, …)
unzip <asset>.zip -d <agent-skills-dir>/
```

## Verify a package

```bash
python <skill>/scripts/actions.py check
```
