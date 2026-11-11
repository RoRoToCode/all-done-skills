# Release assets

Each GitHub Release of this repository attaches **one `.zip` per skill**, built
by `release_all.py`. Download a skill's zip, unzip it into your agent's skills
directory, restart the session.

## File → skill map (v1.4.1)

| Asset | Skill |
| --- | --- |
| `111ai-prompt-reader.zip` | `ai-prompt-reader` |
| `111archive-all-done.zip` | `archive-all-done` |
| `已经上传audio-all-done.zip` | `audio-all-done` |
| `av-transcribe.zip` | `av-transcribe` |
| `已经上传data-all-done.zip` | `data-all-done` |
| `111doc-data-extract.zip` | `doc-data-extract` |
| `已经上传ebook-all-done.zip` | `ebook-all-done` |
| `已经上传ile-all-done.zip` | `file-all-done` |
| `image-all-done.zip` | `image-all-done` |
| `ocr-workshop.zip` | `ocr-workshop` |
| `office-all-done.zip` | `office-all-done` |
| `已经上传pdf-workshop.zip` | `pdf-workshop` |
| `已经上传pipeline-all-done.zip` | `pipeline-all-done` |
| `privacy-all-done.zip` | `privacy-all-done` |
| `text-all-done.zip` | `text-all-done` |
| `video-all-done.zip` | `video-all-done` |
| `web-capture.zip` | `web-capture` |

> Asset filenames preserve the build run's labels. The folder **inside** each
> zip is always the correct skill name (e.g. `file-all-done/`), regardless of
> the asset's own filename.

## Install

```bash
# WorkBuddy
unzip <asset>.zip -d ~/.workbuddy/skills/

# Other agents
unzip <asset>.zip -d <agent-skills-dir>/
```

## Integrity

SHA-256 checksums are produced by `release_all.py` at build time and live in
`release_manifest.json` on the build machine; they are not re-published here.
To verify a package, unzip it and run:

```bash
python <skill>/scripts/actions.py check
```
