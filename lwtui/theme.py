import curses


# pyTermTk
# https://github.com/ceccopierangiolieugenio/pyTermTk/blob/main/libs/pyTermTk/TermTk/TTkTheme/theme.py
class ThemeAscii:
    NAME = "ascii"
    checkbox = ["[ ] ", "[x] ", "[/] "]
    input = ["[", "]", curses.A_NORMAL]
    spinner = r"-\|/"
    error = ["(!)", curses.A_BOLD]
    title = ["[", "]"]
    ellipsis = "..."
    findIcon = " "


class ThemeUtf8:
    NAME = "utf8"
    checkbox = ["□ ", "▣ ", "◪ "]
    input = ["", "", curses.A_UNDERLINE]
    # TODO: Cool Android-compatible UTF-spinner
    # Right side only braille cells (dots ⊆ 4568)
    # incorrect in Noto except Symbols 2, on mobile only #3935
    # https://github.com/google/fonts/issues/3935
    spinner = ["⣄⠀", "⡆⠀", "⠇⠀", "⠋⠀", "⠉⠁", "⠈⠃", "⠀⠇", "⠀⡆", "⢀⡄", "⣀⡀"]
    error = ["⛔", curses.A_BOLD]
    title = ["┤", "├"]
    ellipsis = "…"
    findIcon = "🔍"


THEME = ThemeAscii
THEMES = {t.NAME: t for t in (ThemeAscii, ThemeUtf8)}
