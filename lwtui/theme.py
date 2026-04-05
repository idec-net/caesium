import curses
from dataclasses import dataclass


@dataclass(slots=True)
class SeparatorH:
    ch: str
    color: int = 0


@dataclass(slots=True)
class Label:
    cEnabled: int = 0
    cDisabled: int = 0


@dataclass(slots=True)
class CheckBox:
    unchecked: str
    checked: str
    third: str
    cEnabled: int = 0
    cFocused: int = 0
    cDisabled: int = 0


@dataclass(slots=True)
class InputBox:
    left: str
    right: str
    attr: int
    cEnabled: int = 0
    cFocused: int = 0
    cDisabled: int = 0


@dataclass(slots=True)
class Error:
    ch: str
    len: int  # TODO: Use wcwidth for wide unicode chars???
    attr: int


# pyTermTk
# https://github.com/ceccopierangiolieugenio/pyTermTk/blob/main/libs/pyTermTk/TermTk/TTkTheme/theme.py
class ThemeAscii:
    NAME = "ascii"
    sepH = SeparatorH("─")
    label = Label()
    checkbox = CheckBox("[ ] ", "[x] ", "[/] ")
    input = InputBox("[", "]", curses.A_NORMAL)
    spinner = ["-", "\\", "|", "/"]
    error = Error("(!)", 3, curses.A_BOLD)
    title = ["[", "]"]
    ellipsis = "..."
    findIcon = " "


class ThemeUtf8:
    NAME = "utf8"
    sepH = SeparatorH("─")
    label = Label()
    checkbox = CheckBox("□ ", "▣ ", "◪ ")
    input = InputBox("", "", curses.A_UNDERLINE)
    # TODO: Cool Android-compatible UTF-spinner
    # Right side only braille cells (dots ⊆ 4568)
    # incorrect in Noto except Symbols 2, on mobile only #3935
    # https://github.com/google/fonts/issues/3935
    spinner = ["⣄⠀", "⡆⠀", "⠇⠀", "⠋⠀", "⠉⠁", "⠈⠃", "⠀⠇", "⠀⡆", "⢀⡄", "⣀⡀"]
    error = Error("⛔", 2, curses.A_BOLD)
    title = ["┤", "├"]
    ellipsis = "…"
    findIcon = "🔍"


THEME = ThemeAscii
THEMES = {t.NAME: t for t in (ThemeAscii, ThemeUtf8)}
