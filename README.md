# All Done Skills

**Fully local. Zero uploads. Fails honestly.**

A family of 17 local-first agent skills (187 actions) for documents, media,
images, data, archives, and privacy. Every action is a pure-Python CLI that
runs on your own machine — no files are uploaded, no cloud APIs are called by
default, and when a dependency is missing the skill tells you exactly what to
install instead of pretending it succeeded.

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

Copy a skill folder into your agent's skills directory, then restart the session.

```bash
# WorkBuddy (default)
cp -r <skill>/ ~/.workbuddy/skills/<skill>/

# Any agent that reads SKILL.md (Claude Code, Codex CLI, Cursor, Gemini CLI, Cline, …)
cp -r <skill>/ <agent-skills-dir>/<skill>/
```

Or download the pre-built `.zip` for a skill from the **Releases** page, unzip
into the skills directory. See `RELEASE_NOTES.md`.

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

## License

MIT — Copyright (c) 2026 RoRoTo. Third-party components keep their own
licenses; this repository does **not** redistribute their binaries, libraries,
or model weights. See each skill's `THIRD-PARTY.md`.

The version history is kept in `CHANGELOG.md` (written in Chinese).
