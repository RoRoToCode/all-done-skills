# All Done Skills

**Fully local. Zero uploads. Fails honestly.**

A family of 17 local-first agent skills (187 actions) for documents, media,
images, data, archives, and privacy. Every action is a pure-Python CLI that
runs on your own machine — no files are uploaded, no cloud APIs are called by
default, and when a dependency is missing the skill tells you exactly what to
install instead of pretending it succeeded.

An optional online toolchain is available at [roroto.com](https://roroto.com/). It is
referenced only as a fallback when a local dependency is missing, is **never
called automatically**, and comes with no guarantee or commercial interest. See
[About external references](#about-external-references).

> **Snapshot notice.** This repository is a source-code snapshot. Primary
> maintenance lives on the WorkBuddy Skills Market. Issues opened here are
> **not guaranteed** to be answered.

## Skills

| Skill | Actions | Covers | Extra deps |
|-------|--------|--------|-----------|
| `pdf-workshop` | 23 | PDF ⇄ Office/images, extract, OCR, merge/split, compress, rotate/crop, redact, watermark, encrypt, MD→PDF | host PDF CLI, `pypdf`, `pymupdf`, OCR engine |
| `ocr-workshop` | 5 | Images / scanned PDF → Markdown, JSON, table CSV, searchable PDF | `rapidocr-onnxruntime` or Tesseract, `pymupdf` |
| `image-all-done` | 12 | Convert, compress, resize, crop, watermark, rotate, collage, background-remove, upscale, OCR, batch, strip EXIF | `Pillow`; optional `rembg`, `realesrgan` |
| `video-all-done` | 13 | Transcode, compress, cut, concat, resize, rotate, watermark, extract audio/frames, GIF, subtitle, slideshow | `ffmpeg`, `Pillow` |
| `av-transcribe` | 5 | Local Whisper transcription, hardsub, subtitle convert/translate, extract audio | `ffmpeg`, `openai-whisper` |
| `office-all-done` | 11 | DOCX/XLSX/PPTX extract, →MD, merge, fill, →PDF | `python-docx`, `openpyxl`, `python-pptx`; LibreOffice for →PDF |
| `doc-data-extract` | 11 | Docs → text/CSV, tables, fields, KV, entities, templates, structure, batch, search, diff | `python-docx`, `openpyxl`, `python-pptx`, `beautifulsoup4` |
| `archive-all-done` | 13 | Create, extract, list, test, add/remove, format convert, encrypt, split, merge, batch | none (7z/rar optional) |
| `ebook-all-done` | 16 | EPUB health/metadata/TOC, extract, search, split/merge, generate, →PDF, Calibre convert | none (Edge/Chrome, Calibre optional) |
| `audio-all-done` | 15 | Transcode, compress, resample, cut, concat, split, speed, volume, loudness, denoise, fade, mix, info, waveform | `ffmpeg` |
| `web-capture` | 9 | Capture page, full-page screenshot, →PDF/Markdown, extract article, batch, crawl, diff | none (Edge/Chrome for render) |
| `ai-prompt-reader` | 5 | Read prompt/seed/sampler/model back out of AI-generated images | none (stdlib) |
| `text-all-done` | 7 | Encoding convert, normalize, line dedup, regex replace, diff, stats, split | none (stdlib) |
| `file-all-done` | 12 | Dir inventory/tree, find, bulk rename (dry-run by default), hash dedup, checksum, classify, size report, dir diff, metadata, safe copy | none (stdlib) |
| `data-all-done` | 12 | CSV/TSV/JSON/NDJSON/XML/YAML/TOML/Markdown convert, validate, merge, filter, map, sort/dedup, profile, diff, schema, split, flatten | none (`PyYAML` optional) |
| `pipeline-all-done` | 8 | Skill/action discovery, routing, pipeline templates, validate, run, resume, status, report | none (stdlib) |
| `privacy-all-done` | 10 | PII scan/redact/batch/report/rules, JPEG/PNG/OOXML/PDF metadata read & clean, QR, Code128 barcode | none (`qrcode`/`opencv` optional) |

## Install

You can install **one**, **several**, or **all** skills. Each skill is a folder;
the Releases page also ships one ready-made `.zip` per skill.

### Option A — download a single skill (recommended for other agents)

```bash
VER=v1.4.1
SKILL=privacy-all-done        # change to any of the 17 skill names
curl -L -o "$SKILL.zip" "https://github.com/RoRoToCode/all-done-skills/releases/download/$VER/$SKILL.zip"
unzip -o "$SKILL.zip" -d ~/.workbuddy/skills/   # or your agent's skills dir
```

### Option B — download all 17

```bash
VER=v1.4.1
for s in ai-prompt-reader archive-all-done audio-all-done av-transcribe \
         data-all-done doc-data-extract ebook-all-done file-all-done \
         image-all-done ocr-workshop office-all-done pdf-workshop \
         pipeline-all-done privacy-all-done text-all-done video-all-done web-capture; do
  curl -L -o "$s.zip" "https://github.com/RoRoToCode/all-done-skills/releases/download/$VER/$s.zip"
  unzip -o "$s.zip" -d ~/.workbuddy/skills/
done
```

### Option C — copy from a cloned repo

```bash
# WorkBuddy (default)
cp -r <skill>/ ~/.workbuddy/skills/<skill>/

# Any agent that reads SKILL.md (Claude Code, Codex CLI, Cursor, Gemini CLI, Cline, …)
cp -r <skill>/ <agent-skills-dir>/<skill>/
```

Restart the session after installing. **Note:** `pdf-workshop` and
`doc-data-extract` call the host `workbuddy-pdf` CLI for some PDF actions and
need a substitute on non-WorkBuddy agents (see Compatibility); the other 15 are
pure standard-library / pip. `privacy-all-done` and `file-all-done` are the
cleanest — zero dependencies, no host coupling.

## Compatibility

The `SKILL.md` files follow the open Agent Skills specification, so any agent
that loads skills by reading `SKILL.md` can use them. They are designed and
tested on WorkBuddy; on other agents the trigger keywords still load a skill,
but you may need to invoke it explicitly.

Two skills — `pdf-workshop` and `doc-data-extract` — call the host's
`workbuddy-pdf` CLI for some PDF actions. On non-WorkBuddy agents, set the
`WORKBUDDY_PDF` environment variable to any compatible PDF CLI, or simply skip
those actions. Every other skill is pure standard-library / pip and runs
wherever Python 3.10+ is available.

## Self-check

Each skill validates itself (read-only):

```bash
cd <skill> && python scripts/actions.py check
```

## About external references

This snapshot is built for WorkBuddy, so a few references point outside the repo:

- **`roroto.com`** — Some skills list `roroto.com` as an *optional* third-party
  online alternative in their `actions.json` (`online` field) and `SKILL.md`.
  These links appear only via `python scripts/actions.py online <id>` when a
  local dependency is missing, and only for actions that actually have a
  matching tool on that site (others are `null`). The skill never calls it
  automatically. This is informational only — the repo gives no guarantee and
  earns nothing from it. All processing is local by default; a file is sent to
  a third party only if *you* open that link yourself, under that site's terms.
- **`workbuddy-*` built-in skills** — `office-all-done` routes single-document
  reading/summarization to WorkBuddy's built-in `workbuddy-docx` /
  `workbuddy-sheetagent` / `workbuddy-pptx`. They are not part of this repo; on
  non-WorkBuddy agents, ignore that routing suggestion and use the
  extraction/export actions provided here instead.

## License

MIT — Copyright (c) 2026 RoRoTo. Third-party components keep their own
licenses; this repository does **not** redistribute their binaries, libraries,
or model weights. See each skill's `THIRD-PARTY.md`.

The version history is kept in `CHANGELOG.md` (written in Chinese).
