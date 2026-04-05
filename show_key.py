#!/usr/bin/env python3
import curses

from core import ui
from core.config import UI_HEADER, UI_TEXT, UI_CODE
from lwtui.keystroke import KsSeq
from lwtui.layout import GridLayout, CC
from lwtui.widget import Widget


def show_key():
    ui.initializeCurses()
    lblKs = ui.LabelWidget(color=UI_CODE)
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
        (lblKs, "growY"),
    )
    layout.pack(2, 2, height=ui.HEIGHT - 4, width=ui.WIDTH - 4)
    while True:
        for wid, _ in layout.widgets:  # type: (Widget, CC)
            wid.draw(ui.stdscr)
        #
        ks, key, _ = ui.getKeystroke()
        #
        if key == curses.KEY_RESIZE:
            ui.setTermSize()
            layout.pack(2, 2, height=ui.HEIGHT - 4, width=ui.WIDTH - 4)
        ui.stdscr.addstr(lblKs.y, lblKs.x, " " * lblKs.w)
        lblKs.setTxt(f"{ks} ({key})")


if __name__ == "__main__":
    try:
        ui.initializeCurses()
        ui.loadColors("default")
        show_key()
    finally:
        ui.terminateCurses()
