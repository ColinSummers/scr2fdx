"""Generate Final Draft XML (.fdx) from parsed script elements."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from xml.dom import minidom
from pathlib import Path

from .models import ElementType, FDX_TYPE_MAP, Script


def write_fdx(script: Script, output_path: str | Path) -> None:
    """Write a Script to a Final Draft .fdx file."""
    xml_str = script_to_fdx_string(script)
    Path(output_path).write_text(xml_str, encoding="utf-8")


def script_to_fdx_string(script: Script) -> str:
    """Convert a Script to an FDX XML string."""
    root = ET.Element("FinalDraft", {
        "DocumentType": "Script",
        "Template": "No",
        "Version": "5",
    })

    content = ET.SubElement(root, "Content")

    for elem in script.elements:
        fdx_type = FDX_TYPE_MAP.get(elem.element_type, "General")

        para = ET.SubElement(content, "Paragraph", Type=fdx_type)
        text_node = ET.SubElement(para, "Text")
        text_node.text = elem.text

        # Add alignment for centered elements
        if fdx_type in ("Character", "Transition"):
            text_node.set("Style", "")

    # Add character list as TitlePage info (optional metadata)
    if script.metadata.characters:
        title_page = ET.SubElement(root, "TitlePage")
        content_elem = ET.SubElement(title_page, "Content")
        para = ET.SubElement(content_elem, "Paragraph", Type="General")
        text_node = ET.SubElement(para, "Text")
        chars = sorted(script.metadata.characters.values())
        text_node.text = f"Characters: {', '.join(chars)}"

    # Pretty-print
    rough = ET.tostring(root, encoding="unicode")
    dom = minidom.parseString(rough)
    pretty = dom.toprettyxml(indent="  ", encoding=None)

    # Remove the XML declaration minidom adds (FDX uses its own)
    lines = pretty.split("\n")
    if lines[0].startswith("<?xml"):
        lines = lines[1:]

    header = '<?xml version="1.0" encoding="UTF-8" standalone="no" ?>'
    return header + "\n" + "\n".join(lines)
