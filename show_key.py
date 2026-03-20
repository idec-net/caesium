#!/usr/bin/env python3
import curses

from core import ui
from core.config import UI_HEADER, UI_TEXT, UI_CODE
from core.keystroke import KsSeq
from core.layout import GridLayout


def show_key():
    ui.initialize_curses()
    lbl_ks = ui.LabelWidget(color=UI_CODE)
    KsSeq.sequences += ["C-w C-r z", "C-n C-f"]
    layout = GridLayout(
        (ui.LabelWidget("Caesium Keystroke tester",
                        color=UI_HEADER), "h 2 wrap"),
        (ui.LabelWidget("Press keys to see how its translated to keystrokes.",
                        color=UI_TEXT), "h 2 wrap"),
        (ui.LabelWidget("Test sequences: " + "; ".join(KsSeq.sequences),
                        color=UI_TEXT), "h 2 wrap"),
        (ui.LabelWidget("Press Ctrl+C to exit.",
                        color=UI_TEXT), "h 2 wrap"),
        (lbl_ks, "growY"),
    )
    layout.pack(2, 2, height=ui.HEIGHT - 4, width=ui.WIDTH - 4)
    while True:
        for wid, _ in layout.widgets:  # type: (ui.Widget, ui.CC)
            wid.draw(ui.stdscr)
        #
        ks, key, _ = ui.get_keystroke()
        #
        if key == curses.KEY_RESIZE:
            ui.set_term_size()
            layout.pack(2, 2, height=ui.HEIGHT - 4, width=ui.WIDTH - 4)
        ui.stdscr.addstr(lbl_ks.y, lbl_ks.x, " " * lbl_ks.w)
        lbl_ks.set_txt(f"{ks} ({key})")


if __name__ == "__main__":
    try:
        ui.initialize_curses()
        ui.load_colors("default")
        show_key()
    finally:
        ui.terminate_curses()
