#!/usr/bin/env python3
import curses
import dataclasses

from core import ui
from core.config import UI_HEADER, UI_TEXT, UI_CODE
from lwtui.keystroke import KsSeq
from lwtui.layout import GridLayout, CC
from lwtui.widget import Widget


def lbl(txt, color):
    label = ui.LabelWidget(txt)
    label.style = dataclasses.replace(label.style, cEnabled=ui.getColor(color))
    # noinspection PyProtectedMember
    label.color = label._color(label.style)
    return label


def show_key():
    ui.initializeCurses()
    lblKs = lbl("", UI_CODE)
    KsSeq.sequences += ["C-w C-r z", "C-n C-f"]
    layout = GridLayout(
        (lbl("Caesium Keystroke tester", UI_HEADER), "h 2 wrap"),
        (lbl("Press keys to see how its translated to keystrokes.", UI_TEXT), "h 2 wrap"),
        (lbl("Test sequences: " + "; ".join(KsSeq.sequences), UI_TEXT), "h 2 wrap"),
        (lbl("Press Ctrl+C to exit.", UI_TEXT), "h 2 wrap"),
        (lblKs, "growY"),
    )
    h, w = ui.stdscr.getmaxyx()
    layout.pack(2, 2, height=h - 4, width=w - 4)
    while True:
        for wid, _ in layout.widgets:  # type: (Widget, CC)
            wid.draw(ui.stdscr)
        #
        ks, key, _ = ui.getKeystroke()
        #
        if key == curses.KEY_RESIZE:
            h, w = ui.stdscr.getmaxyx()
            layout.pack(2, 2, height=h - 4, width=w - 4)
        ui.stdscr.addstr(lblKs.y, lblKs.x, " " * lblKs.w)
        lblKs.setTxt(f"{ks} ({key})")


if __name__ == "__main__":
    try:
        ui.initializeCurses()
        ui.loadColors("default")
        show_key()
    finally:
        ui.terminateCurses()
