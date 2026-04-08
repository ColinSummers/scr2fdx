# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Directory Contains

132 ScriptWare (.SCR) binary files — TV scripts from Nell Scovell's career (primarily *Sabrina the Teenage Witch*, plus *Charmed*, *Coach*, pilots, and spec scripts). These files date from 1996–2008 and cannot be opened by any modern application. ScriptWare (by Cinovation) was discontinued in the early 2000s.

23 files have parenthetical annotations (e.g., `BOOK (Episode 1-20 Meeting Dads Girlfriend).SCR`) — these appear to be annotated copies of the base file (e.g., `BOOK.SCR`).

## ScriptWare Binary Format (Reverse-Engineered)

### File Versions Present

| Format | Version Strings | Count |
|--------|----------------|-------|
| Scriptware Script | 1.30, 1.504, 1.521, 2.08w–2.21w | ~129 files |
| ScriptThing WinVer | 2.40b, 3.10 | 2–3 files |

### Binary Layout

- **Bytes 0x00–0x0A**: Length-prefixed magic string `\x0bScriptware`
- **Bytes 0x0B–0x0F**: Unknown flags/version bytes
- **Bytes 0x10–0x2F**: Version string, e.g., `Scriptware Script 2.08w:4;6031`, null-terminated
- **Bytes 0x30–0xA9**: Zero-padded (may contain sparse config in some versions)
- **Bytes 0xAA–0xEF**: Header metadata — margin/formatting config (varies by version). Key offsets:
  - 0xAA–0xAB: appears to be a config block size or offset
  - 0xB4–0xB7: possibly page dimensions
- **Bytes 0xF0–0x7FF**: Mostly zeros; sparse formatting/style table entries at intervals of 0x15–0x18 bytes starting around 0xF0
- **Byte 0x800**: **Body section begins** — this is consistent across all examined files

### Body Section Structure (0x800+)

The body uses a record-based structure with these recurring 2-byte markers:

| Marker | Hex | Meaning |
|--------|-----|---------|
| `4S` | 0x3453 | Paragraph/element start marker |
| `DS` | 0x4453 | Dialogue/structural block marker |
| `W4` | 0x5734 | Text content pointer/reference |

**Text content** is stored as length-prefixed strings. The first byte (or two bytes for longer content) before readable ASCII text indicates the string length. Text lines are interspersed with formatting/control bytes.

Script element types (scene headings, action, character names, dialogue, parentheticals, transitions) are encoded in the control bytes preceding each text block. The exact element-type encoding differs slightly between version families (1.x vs 2.x).

### Metadata Tables (End of File)

After the body, each file contains lookup tables in order:
1. `SCRWARE` sentinel
2. **Character List** — all character names used in the script
3. **Transitions** — `CUT TO:`, `DISSOLVE TO:`, `FADE OUT:`, etc.
4. **Extensions** — `O.S.)`, `V.O.)`
5. **Scene headings** (numbered Scene 1–5) — location prefixes like `INT.`, `EXT.`
6. **Misc.** — structural labels (`Cold Opening`, `Teaser`, `Tag`, `Epilogue`, etc.)
7. Font name and style continuation markers (`CONT'D`, `(CONT'D)`, `CONTINUED`)

### Quick Text Extraction (Lossy)

`strings -n 5 FILE.SCR` extracts readable text but loses all formatting, element types, and ordering context. It's useful for content verification but not for proper script reconstruction.

## Goal: SCR-to-FDX Converter

The purpose of working in this directory is to build a Python tool that converts .SCR files to .FDX (Final Draft XML) format, preserving:
- Script element types (scene headings, action, character, dialogue, parenthetical, transition)
- Page breaks and act breaks
- Character lists
- Proper screenplay formatting

### FDX Target Format

Final Draft XML (.fdx) uses `<Paragraph Type="...">` elements where Type is one of:
`Scene Heading`, `Action`, `Character`, `Dialogue`, `Parenthetical`, `Transition`, `General`

### Validation Strategy

Use `SAMPLE.SCR` as the primary test file — it's the ScriptWare sample/demo script with known content (Max Trucco scene). Compare extracted text against `strings` output to verify completeness. Then validate against larger files like `SABRINA.SCR` (full episode).

## Rules

- **Do not modify or delete any .SCR file.** These are irreplaceable originals.
- **Quote all paths** — filenames contain spaces, parentheses, and tildes.
- Output converted files to a separate directory (e.g., `converted/`).
- The converter must handle all version variants (1.x, 2.x, ScriptThing).
