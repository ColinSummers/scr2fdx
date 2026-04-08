"""Data classes for parsed ScriptWare elements."""

from dataclasses import dataclass, field
from enum import IntEnum
from typing import Optional


class ElementType(IntEnum):
    """Script element types from DS record flag2 byte."""
    STRUCTURAL = 0x00
    FADE_IN = 0x01
    ACT_BREAK = 0x04
    TRANSITION_END = 0x05  # e.g., CUT TO:
    SCENE_HEADING = 0x08
    ACTION = 0x09
    CHARACTER = 0x0A
    PARENTHETICAL_LINK = 0x0B
    PARENTHETICAL_TEXT = 0x0C
    DIALOGUE = 0x0D
    TRANSITION = 0x1B  # e.g., ON TIMMY (camera direction)
    UNKNOWN_28 = 0x28


# Map to FDX paragraph types
FDX_TYPE_MAP = {
    ElementType.SCENE_HEADING: "Scene Heading",
    ElementType.ACTION: "Action",
    ElementType.CHARACTER: "Character",
    ElementType.DIALOGUE: "Dialogue",
    ElementType.PARENTHETICAL_TEXT: "Parenthetical",
    ElementType.TRANSITION: "Transition",
    ElementType.TRANSITION_END: "Transition",
    ElementType.ACT_BREAK: "Action",  # Act breaks rendered as Action
    ElementType.FADE_IN: "Transition",
}


@dataclass
class ScriptElement:
    """A single script element (paragraph) with its type and text."""
    element_type: ElementType
    text: str
    char_index: Optional[int] = None  # For CHARACTER elements


@dataclass
class ScriptMetadata:
    """Metadata tables from end of SCR file."""
    characters: dict = field(default_factory=dict)  # index -> name
    transitions: list = field(default_factory=list)
    extensions: list = field(default_factory=list)
    scene_prefixes: list = field(default_factory=list)
    misc_labels: list = field(default_factory=list)
    version: str = ""


@dataclass
class Script:
    """A fully parsed script."""
    metadata: ScriptMetadata
    elements: list = field(default_factory=list)  # list of ScriptElement

    @property
    def title(self) -> str:
        """Extract title from first scene heading or return empty."""
        for elem in self.elements:
            if elem.element_type == ElementType.SCENE_HEADING:
                return ""  # No title in format
        return ""
