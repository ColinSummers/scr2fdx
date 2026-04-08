"""Binary parser for ScriptWare (.SCR) files."""

from __future__ import annotations

from pathlib import Path
from typing import Optional, Union

from .models import ElementType, Script, ScriptElement, ScriptMetadata


# Body section always starts at this offset
BODY_OFFSET = 0x800

# The first record marker always appears at this offset in the body
FIRST_RECORD_OFFSET = 0x826

# Text prefix: 5 bytes that reliably precede every length-prefixed text block
TEXT_PREFIX = b"\x01\x00\x00\x00\x00"


def parse_scr(path: str | Path) -> Script:
    """Parse a ScriptWare .SCR file and return a Script object."""
    data = Path(path).read_bytes()
    _validate_header(data)
    version = _read_version(data)
    metadata = _parse_metadata(data)
    metadata.version = version
    elements = _parse_body(data, metadata)
    script = Script(metadata=metadata, elements=elements)
    _deduplicate_elements(script)
    return script


def _validate_header(data: bytes) -> None:
    """Check for ScriptWare magic bytes."""
    if len(data) < BODY_OFFSET:
        raise ValueError(f"File too small ({len(data)} bytes)")
    if data[1:11] != b"Scriptware":
        if b"ScriptThing" in data[:64]:
            raise ValueError("ScriptThing format is not supported (only ScriptWare)")
        raise ValueError("Not a ScriptWare file (bad magic bytes)")


def _read_version(data: bytes) -> str:
    """Extract version string from header."""
    end = data.index(0, 0x11)
    return data[0x11:end].decode("ascii", errors="replace")


def _detect_record_marker(data: bytes) -> bytes:
    """Detect the 2-byte record marker for this file.

    Different ScriptWare versions use different 2-byte markers as their
    record-type identifier (equivalent of 'DS' in v2.08). The marker
    is always at offset 0x826 (first record in body).

    Known markers: 4453 (DS), 685e, 7491, ba5a, d254, 6090
    """
    return bytes([data[FIRST_RECORD_OFFSET], data[FIRST_RECORD_OFFSET + 1]])


def _parse_metadata(data: bytes) -> ScriptMetadata:
    """Parse the SCRWARE metadata tables at end of file."""
    meta = ScriptMetadata()

    # Find metadata start — some files have SCRWARE sentinel, others don't
    scrware_idx = data.find(b"SCRWARE")
    search_start = scrware_idx if scrware_idx >= 0 else BODY_OFFSET

    char_section_start = data.find(b"Character List", search_start)
    if char_section_start < 0:
        return meta

    trans_section_start = data.find(b" Transitions", char_section_start)
    if trans_section_start < 0:
        trans_section_start = len(data)

    # Parse character entries: 0c 00 01 00 <index> 00 <name_len> <name>
    pos = char_section_start
    while pos < trans_section_start:
        if (pos + 7 < len(data)
            and data[pos] == 0x0C and data[pos + 1] == 0x00
            and data[pos + 2] == 0x01 and data[pos + 3] == 0x00):
            char_idx = data[pos + 4]
            name_len = data[pos + 6]
            if 0 < name_len < 30 and pos + 7 + name_len <= len(data):
                name = data[pos + 7:pos + 7 + name_len].decode("ascii", errors="replace").rstrip()
                if name and name[0] not in (" ", "\x00", "?"):
                    meta.characters[char_idx] = name
                pos += 7 + name_len
                continue
        pos += 1

    # Parse transitions: 0c 00 02 00 ...
    pos = trans_section_start
    ext_section = data.find(b" Extensions", pos)
    if ext_section < 0:
        ext_section = len(data)
    while pos < ext_section:
        if (pos + 7 < len(data)
            and data[pos] == 0x0C and data[pos + 1] == 0x00
            and data[pos + 2] == 0x02 and data[pos + 3] == 0x00):
            entry_idx = data[pos + 4]
            name_len = data[pos + 6]
            if 0 < name_len < 30 and pos + 7 + name_len <= len(data):
                name = data[pos + 7:pos + 7 + name_len].decode("ascii", errors="replace").rstrip()
                if name and name[0] not in (" ", "\x00", "?"):
                    meta.transitions.append(name)
                pos += 7 + name_len
                continue
        pos += 1

    return meta


def _find_text_blocks(data: bytes, start: int, end: int) -> list[str]:
    """Find all text blocks in a byte range using the reliable prefix pattern.

    Text blocks are stored as: ... 01 00 00 00 00 <length_byte> <ascii_text> ...
    Returns list of decoded text strings.
    """
    texts = []
    pos = start
    while pos < end - 6:
        if data[pos:pos + 5] == TEXT_PREFIX:
            length = data[pos + 5]
            if 0 < length < 80 and pos + 6 + length <= len(data):
                text_bytes = data[pos + 6:pos + 6 + length]
                check_len = min(6, length)
                if all(32 <= b < 127 for b in text_bytes[:check_len]):
                    text = text_bytes.decode("ascii", errors="replace").rstrip(" \x00")
                    if text:
                        texts.append(text)
                    pos += 6 + length
                    continue
        pos += 1
    return texts


def _parse_body(data: bytes, metadata: ScriptMetadata) -> list[ScriptElement]:
    """Parse record markers from the body section and extract script elements.

    The record marker varies by file version (DS/0x4453, 0xba5a, 0x685e, etc.)
    but the record structure is always the same: 20 bytes with element type at +11.
    """
    # Find end of body section — SCRWARE sentinel or Character List
    scrware_idx = data.find(b"SCRWARE")
    if scrware_idx < 0:
        # Fall back to Character List location
        scrware_idx = data.find(b"Character List", BODY_OFFSET)
        if scrware_idx >= 0:
            # Back up to find the start of the metadata record before the label
            scrware_idx = max(BODY_OFFSET, scrware_idx - 50)
        else:
            scrware_idx = len(data)

    record_marker = _detect_record_marker(data)
    m0, m1 = record_marker[0], record_marker[1]

    body = data[BODY_OFFSET:scrware_idx]
    body_len = len(body)

    # First pass: find all record positions and their element types
    records = []  # (abs_offset, element_type, char_index)
    offset = 0
    while offset < body_len - 20:
        if body[offset] == m0 and body[offset + 1] == m1:
            elem_type_byte = body[offset + 11]
            try:
                elem_type = ElementType(elem_type_byte)
            except ValueError:
                elem_type = None

            char_idx = None
            if elem_type == ElementType.CHARACTER:
                char_idx = body[offset + 13]

            if elem_type is not None and elem_type != ElementType.STRUCTURAL:
                records.append((BODY_OFFSET + offset, elem_type, char_idx))
            offset += 20
        else:
            offset += 1

    # Second pass: extract text for each record
    elements = []
    for i, (abs_offset, elem_type, char_idx) in enumerate(records):
        if elem_type in (ElementType.PARENTHETICAL_LINK, ElementType.UNKNOWN_28):
            continue

        if elem_type == ElementType.CHARACTER:
            name = metadata.characters.get(char_idx, f"CHARACTER_{char_idx}")
            elements.append(ScriptElement(
                element_type=elem_type,
                text=name,
                char_index=char_idx,
            ))
            continue

        # Search for text between this record and the next
        next_boundary = scrware_idx
        for j in range(i + 1, len(records)):
            next_boundary = records[j][0]
            break

        text_start = abs_offset + 20
        texts = _find_text_blocks(data, text_start, next_boundary)

        if texts:
            full_text = " ".join(texts)
            elements.append(ScriptElement(
                element_type=elem_type,
                text=full_text,
            ))
        elif elem_type == ElementType.FADE_IN:
            elements.append(ScriptElement(
                element_type=elem_type,
                text="FADE IN:",
            ))

    return elements


def _deduplicate_elements(script: Script) -> None:
    """Remove duplicate ParenText/Dialogue pairs and format real parentheticals."""
    filtered = []
    elements = script.elements
    i = 0
    while i < len(elements):
        elem = elements[i]

        if elem.element_type == ElementType.PARENTHETICAL_TEXT:
            if i + 1 < len(elements) and elements[i + 1].element_type == ElementType.DIALOGUE:
                dialogue = elements[i + 1]
                if elem.text == dialogue.text:
                    i += 1
                    continue
                else:
                    paren_text = elem.text
                    if not paren_text.startswith("("):
                        paren_text = f"({paren_text}"
                    if not paren_text.endswith(")"):
                        paren_text = f"{paren_text})"
                    filtered.append(ScriptElement(
                        element_type=elem.element_type,
                        text=paren_text,
                    ))
                    i += 1
                    continue

        filtered.append(elem)
        i += 1

    script.elements = filtered
