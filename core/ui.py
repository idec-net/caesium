import base64
import curses
import hashlib
import json
import os
import pickle
import re
import subprocess
import textwrap
import time
import sys
from abc import ABC
from collections import deque
from datetime import datetime
from enum import Enum
from itertools import cycle
from shutil import copyfile
from typing import Optional, List, Tuple, TypeVar, Generic, Union, Callable

import api.ait
from api import MsgMetadata, FindQuery
from core import __version__, parser, utils, config, mailer, client, cmd
from core.cmd import Common, Reader, Selector, Qs, Out
from core.config import (
    getColor, loadColors, Config, Echo, CFG, TOKEN2UI, ECHO_FIND,
    UI_BORDER, UI_COMMENT, UI_CURSOR, UI_STATUS, UI_SCROLL, UI_TITLES, UI_TEXT,
)
from lwtui import keystroke, theme
from lwtui.layout import GridLayout, CC
from lwtui.widget import (
    Widget, LabelWidget, SeparatorHWidget, CheckBoxWidget,
    InputWidget, InputRegexWidget, InputDateWidget, Window
)

THEME = theme.THEME
API = api.ait
LABEL_SEARCH = "<введите regex для поиска>"
LABEL_ANY_KEY = "Нажмите любую клавишу"
LABEL_ESC = "Esc - отмена"
LABEL_FIND = "Поиск "  # extra space for wide unicode icon (use wcwidth)

stdscr = None  # type: Optional[curses.window]
version = "Caesium/%s │" % __version__


def loadTheme(cfg: Config):
    try:
        loadColors(cfg.themeColors)
    except ValueError as err:
        loadColors("default")
        stdscr.refresh()
        showMessageBox("Цветовая схема %s не установлена.\n"
                       "%s\n"
                       "Будет использована схема по-умолчанию."
                       % (cfg.themeColors, str(err)))
    #
    theme.THEME = theme.ThemeAscii
    if cfg.themeWidgets in theme.THEMES:
        theme.THEME = theme.THEMES[cfg.themeWidgets]
    elif cfg.themeWidgets:
        showMessageBox("Неизвестная схема виджетов %s\n"
                       "Будет использована схема по-умолчанию."
                       % cfg.themeWidgets)
    global THEME
    THEME = theme.THEME

    THEME.sepH.color = getColor(UI_COMMENT)

    THEME.label.cEnabled = getColor(UI_TEXT)
    THEME.label.cDisabled = getColor(UI_COMMENT)

    THEME.checkbox.cEnabled = getColor(UI_TEXT)
    THEME.checkbox.cFocused = getColor(UI_TITLES)
    THEME.checkbox.cDisabled = getColor(UI_COMMENT) | curses.A_ITALIC

    THEME.input.cEnabled = getColor(UI_CURSOR)
    THEME.input.cFocused = getColor(UI_CURSOR)
    THEME.input.cDisabled = getColor(UI_TEXT)


def initializeCurses():
    global stdscr
    stdscr = curses.initscr()
    curses.start_color()
    curses.use_default_colors()
    curses.noecho()
    curses.set_escdelay(50)  # ms
    curses.curs_set(0)
    curses.raw()
    stdscr.keypad(True)


def terminateCurses():
    curses.curs_set(1)
    if stdscr:
        stdscr.keypad(False)
    curses.echo(True)
    curses.noraw()
    curses.endwin()


def initKeys():
    # keystroke sequences
    keystroke.KsSeq.sequences = []
    for k, group in cmd.__dict__.items():
        if not isinstance(group, type):
            continue  #
        for attr, val in group.__dict__.items():
            if isinstance(val, cmd.Cmd) and val.ks:
                keystroke.KsSeq.sequences += [_ for _ in val.ks if " " in _]
    # common navigation keys
    for name, val in keystroke.Keys.__dict__.items():
        if name.isupper() and isinstance(val, list) and hasattr(cmd.Common, name):
            setattr(keystroke.Keys, name, getattr(cmd.Common, name).ks)


def getKeystroke(timeout=-1):
    stdscr.timeout(timeout)
    key = -1
    if not keystroke.PENDING_KEYS:
        key = stdscr.getch()
    stdscr.timeout(0)
    ks, key, _ = keystroke.getkeystroke(stdscr, key)
    stdscr.timeout(-1)
    if ks == "C-c" or ks in Common.QUIT:
        sys.exit(0)
    return ks, key, _


def drawSplash(scr, splash):  # type: (curses.window, List[str]) -> None
    scr.clear()
    h, w = scr.getmaxyx()
    x = (w - len(splash[1])) // 2 - 1
    y = (h - len(splash)) // 2
    color = getColor(UI_TEXT)
    for i, line in enumerate(splash):
        scr.addstr(y + i, x, line, color)
    scr.refresh()


def drawTitle(scr, y, x, title):
    _, w = scr.getmaxyx()
    x = max(0, x)
    borders = len(THEME.title[0]) + len(THEME.title[1])
    if (x + len(title) + borders) > w:
        title = title[:w - x - borders - len(THEME.ellipsis)] + THEME.ellipsis
    #
    border = getColor(UI_BORDER)
    if THEME.title[0]:
        scr.addstr(y, x, THEME.title[0], border)
    color = getColor(UI_TITLES)
    scr.addstr(y, x + len(THEME.title[0]), title, color)
    if THEME.title[1]:
        scr.addstr(y, x + len(THEME.title[0]) + len(title), THEME.title[1], border)


def drawMessageBox(smsg, wait):
    msg = smsg.split("\n")
    if wait:
        msg.extend(LABEL_ANY_KEY)
    height, width = stdscr.getmaxyx()
    boxW = int(width * 0.75) if width > 80 else width - 2
    boxW = min(boxW, max(map(lambda x: len(x), msg))) + 2
    msg = list(map(lambda p: textwrap.fill(p, boxW - 2),
                   smsg.split("\n")))
    msg = "\n".join(msg).split("\n")  # re-split after textwrap.fill added \n
    boxH = len(msg) + 2  # len + border
    if wait:
        boxH += 2  # + new line + LABEL_ANY_KEY
    win = curses.newwin(boxH, boxW,
                        int((height - boxH) / 2),
                        int((width - boxW) / 2))
    win.bkgd(' ', curses.color_pair(config.COLOR_PAIRS[UI_TEXT][0]))
    win.attrset(getColor(UI_BORDER))
    win.border()

    color = getColor(UI_TEXT)
    for i, line in enumerate(msg, start=1):
        if i >= height - 1:
            break
        win.addstr(i, 1, line, color)

    color = getColor(UI_TITLES)
    if wait:
        win.addstr(len(msg) + 2, int((boxW - len(LABEL_ANY_KEY)) / 2),
                   LABEL_ANY_KEY, color)
    win.refresh()


def showMessageBox(smsg):
    drawMessageBox(smsg, True)
    stdscr.getch()
    stdscr.clear()


def drawScrollBarV(scr, y, x, scroll):
    # type: (curses.window, int, int, ScrollCalc) -> None
    color = getColor(UI_SCROLL)
    for i in range(y, y + scroll.track):
        scr.addstr(i, x, "░", color)
    for i in range(y + scroll.thumbPos, y + scroll.thumbPos + scroll.thumbSz):
        scr.addstr(i, x, "█", color)


def drawScrollBarH(scr, y, x, scroll):
    # type: (curses.window, int, int, ScrollCalc) -> None
    color = getColor(UI_SCROLL)
    scr.addstr(y, x, "░" * scroll.track, color)
    scr.addstr(y, x + scroll.thumbPos, "█" * scroll.thumbSz, color)


def drawStatusBar(scr, mode=None, text=None):
    # type: (curses.window, Union[ReaderMode, SelectorMode], str) -> None
    h, w = scr.getmaxyx()
    color = getColor(UI_STATUS)
    scr.insstr(h - 1, 0, " " * w, color)
    scr.addstr(h - 1, 1, version, color)
    scr.addstr(h - 1, w - 8, "│ " + datetime.now().strftime("%H:%M"), color)
    if text:
        scr.addstr(h - 1, len(version) + 2, text, color)
    if mode:
        scr.addstr(h - 1, w - 11, mode.value, color)
    if parser.INLINE_STYLE_ENABLED:
        scr.addstr(h - 1, w - 10, "~", color)
    scr.addstr(h - 1, w - 9, "-" if parser.HORIZONTAL_SCROLL_ENABLED else "=",
               color)


def drawReader(scr, echo: str, msgid, out):
    h, w = scr.getmaxyx()
    color = getColor(UI_BORDER)
    scr.addstr(0, 0, "─" * w, color)
    scr.addstr(4, 0, "─" * w, color)
    if out:
        drawTitle(scr, 0, 0, echo)
        if msgid.endswith(".out"):
            ns = "не отправлено"
            drawTitle(scr, 4, w - len(ns) - 2, ns)
    else:
        if w >= 80:
            drawTitle(scr, 0, 0, echo + " / " + msgid)
        else:
            drawTitle(scr, 0, 0, echo)
    for i in range(1, 4):
        scr.addstr(i, 0, " " * w, 1)
    color = getColor(UI_TITLES)
    scr.addstr(1, 1, "От:   ", color)
    scr.addstr(2, 1, "Кому: ", color)
    scr.addstr(3, 1, "Тема: ", color)


class ScrollCalc:
    content: int  # scrollable content length
    view: int  # scroll view length
    thumbSz: int  # thumb size
    track: int  # track length
    _pos: int = 0  # scroll position in the scrollable content
    #
    thumbPos: int  # calculated thumb position on the track
    isScrollable = False

    def __init__(self, content: int, view: int,
                 pos: int = 0, track: int = None):
        self.content = content
        self.view = view
        self.thumbSz = max(1, min(self.view, int(self.view * self.view
                                                 / max(1, content) + 0.5)))
        self.track = track or view
        self.isScrollable = self.content > self.view
        self._pos = max(0, min(self.content - self.view, pos))
        self.calc()

    @property
    def pos(self):
        return self._pos

    @pos.setter
    def pos(self, pos):
        if self._pos == pos:
            return
        self._pos = max(0, min(self.content - self.view, pos))
        self.calc()

    def posBottom(self):
        return max(0, min(self.pos + self.view, self.content) - 1)

    def calc(self):
        availableTrack = self.track - self.thumbSz
        thumbPos = 0
        if self.isScrollable:
            thumbPos = int((self.pos / (self.content - self.view))
                           * availableTrack + 0.5)
        self.thumbPos = max(0, min(availableTrack, thumbPos))

    def ensureVisible(self, pos, center=False):
        if pos < self.pos:
            self.pos = pos  # scroll up
            if center:
                self.pos -= self.view // 2
        elif pos >= self.pos + self.view:
            self.pos = pos - self.view + 1  # scroll down
            if center:
                self.pos += self.view // 2

    # region search.Pager implementation
    def nextPageTop(self):
        return self.pos + self.view

    def prevPageBottom(self):
        return self.pos - 1
    # endregion search.Pager implementation


class SelectWindow(Window):
    scroll: ScrollCalc

    def __init__(self, scr: curses.window, title, items):
        super().__init__(scr)
        self.title = title
        self.items = items
        self.cursor = 0
        self.win = self.initWin(self.items, self.title)
        self.resized = False

    def initWin(self, items, title, win=None):
        testWidth = items + [LABEL_ESC + THEME.title[0] + THEME.title[1],
                             title + THEME.title[0] + THEME.title[1]]
        height, width = self.scr.getmaxyx()
        w = 0 if not items else max(map(lambda it: len(it), testWidth))
        h = min(height - 2, len(items))
        w = min(width - 2, w)
        y = max(0, int(height / 2 - h / 2 - 1))
        x = max(0, int(width / 2 - w / 2 - 1))
        if win:
            win.resize(h + 2, w + 2)
            win.mvwin(y, x)
        else:
            win = curses.newwin(h + 2, w + 2, y, x)
        color = getColor(UI_BORDER)
        lblTitle = title[0:min(w - 2, len(title))]
        lblEsc = LABEL_ESC[0:min(w - 2, len(LABEL_ESC))]
        win.attrset(color)
        win.border()
        win.addstr(0, 1, THEME.title[0], color)
        win.addstr(0, 2 + len(lblTitle), THEME.title[1], color)
        win.addstr(h + 1, 1, THEME.title[0], color)
        win.addstr(h + 1, 2 + len(lblEsc), THEME.title[1], color)

        color = getColor(UI_TITLES)
        win.addstr(0, 2, lblTitle, color)
        win.addstr(h + 1, 2, lblEsc, color)
        self.scroll = ScrollCalc(len(items), h)
        self.h, self.w, self.y, self.x = h + 2, w + 2, y, x
        return win

    def show(self):
        while True:
            self.draw(self.win)
            self.win.refresh()
            #
            ks, key, _ = getKeystroke()
            #
            if key == curses.KEY_RESIZE:
                stdscr.clear()
                stdscr.refresh()
                self.win = self.initWin(self.items, self.title, self.win)
                self.resized = True
            elif ks in Selector.ENTER:
                return self.cursor + 1  # return 1-based index
            elif ks in Reader.QUIT:
                return False  #
            else:
                self.onKeyPressed(ks, key)

    def draw(self, win):
        self._draw(win, self.items, self.cursor, self.scroll)

    def _draw(self, win, items, cursor, scroll):
        if self.h < 3 or self.w < 5:
            if self.h > 0 and self.w > 0:
                win.insstr(0, 0, "#" * self.w)
            return  # no space to draw
        #
        scroll.ensureVisible(cursor)
        for i, item in enumerate(items[scroll.pos:scroll.pos + self.h - 2]):
            color = getColor(UI_TEXT if i + scroll.pos != cursor else
                             UI_CURSOR)
            win.addstr(i + 1, 1, " " * (self.w - 2), color)
            win.addstr(i + 1, 1, item[:self.w - 2], color)

        if scroll.isScrollable:
            drawScrollBarV(win, 1, self.w - 1, scroll)

    def onKeyPressed(self, ks, key):
        self._onKeyPressed(ks, self.scroll)

    def _onKeyPressed(self, ks: str, scroll: ScrollCalc):
        if ks in Reader.UP:
            self.cursor -= 1
            if self.cursor < 0:
                self.cursor = scroll.content - 1
        elif ks in Reader.DOWN:
            self.cursor += 1
            if self.cursor >= self.scroll.content:
                self.cursor = 0
        elif ks in Reader.HOME:
            self.cursor = 0
        elif ks in Reader.MEND:
            self.cursor = scroll.content - 1
        elif ks in Reader.PPAGE:
            if self.cursor > scroll.pos:
                self.cursor = scroll.pos
            else:
                self.cursor = max(0, self.cursor - scroll.view)
        elif ks in Reader.NPAGE:
            pageBottom = scroll.posBottom()
            if self.cursor < pageBottom:
                self.cursor = pageBottom
            else:
                self.cursor = min(scroll.content - 1, pageBottom + scroll.view)


# region Modes
T = TypeVar('T')
V = TypeVar('V')


class ReaderMode(Enum):
    ECHO = 'E'  # Regular mode reading whole echo conference
    SUBJ = 'S'  # Specified subject and answers (Re: )
    SEARCH = 'Q'  # Quick Search results on MsgListScreen
    FIND = 'F'  # Find results


class SelectorMode(Enum):
    ECHO = 'E'  # Regular mode w Node echoareas
    ARCH = 'A'  # Archives mode w Node archived echoareas
    SEARCH = 'Q'  # Quick Search results


class ModeStackABC(ABC, Generic[T, V]):
    def __init__(self, mode: T, data: List[V], idx: int = 0):
        self.stack = []  # type: List[Tuple[T, List[V], int]]
        self.mode = mode  # type: T
        self.data = data  # type: List[V]
        self.idx = idx

    def curItem(self):
        if self.idx > -1:
            return self.data[self.idx]
        return None

    def push(self, mode: T, data: List[V]):
        m = self.curItem()
        #
        if self.mode != mode:
            self.stack.append((self.mode, self.data, self.idx))
        self.mode = mode
        self.data = data
        #
        if m:
            self.idx = self.findItemIdx(m)

    def pop(self):
        m = self.curItem()
        #
        if self.stack:
            self.mode, self.data, self.idx = self.stack.pop()
        #
        if m:
            idx = self.findItemIdx(m)
            if idx > -1:
                self.idx = idx
        return self.mode, self.data, self.idx

    def findItemIdx(self, it: V, data: List[V] = None) -> int:
        ...


class MsgModeStack(ModeStackABC[ReaderMode, MsgMetadata]):
    def modeSubjOn(self, data):
        data = sorted(data, key=lambda m: m.time)
        self.push(ReaderMode.SUBJ, data)

    def modeSubjOff(self):
        if self.mode != ReaderMode.SUBJ:
            return
        self.pop()

    def modeQsOn(self, indexes):
        data = sorted([self.data[idx] for idx in indexes],
                      key=lambda m: m.time)
        self.push(ReaderMode.SEARCH, data)

    def hasNext(self):
        return self.idx < len(self.data) - 1 and self.data

    def findItemIdx(self, it, data=None) -> int:
        return self.findMsgidIdx(it.msgid, data)

    def findMsgidIdx(self, msgid, data=None):
        for i, d in enumerate(data or self.data):
            if d.msgid == msgid:
                return i
        return -1


class EchoModeStack(ModeStackABC[SelectorMode, Echo]):
    def isArch(self):
        return (self.mode == SelectorMode.ARCH
                or (self.mode == SelectorMode.SEARCH
                    and self.stack[-1][0] == SelectorMode.ARCH))

    def modeArchOn(self, data: List[Echo]):
        self.push(SelectorMode.ARCH, data)

    def modeArchOff(self):
        if not self.isArch():
            return
        self.pop()
        if self.isArch():  # quick search in Archive mode is Archive mode too
            self.pop()

    def modeQsOn(self, indexes: List[int]):
        data = [self.data[idx] for idx in indexes]
        self.push(SelectorMode.SEARCH, data)

    def findItemIdx(self, it: Echo, data: List[Echo] = None) -> int:
        for i, d in enumerate(data or self.data):
            if d == it:
                return i
        return -1
# endregion Modes


class MsgListScreen(Window):
    msgs: MsgModeStack = None
    scroll: ScrollCalc = None

    def __init__(self, scr, echo: str, msgs: MsgModeStack):
        super().__init__(scr)
        self.echo = echo
        self.msgs = msgs
        self.scroll = ScrollCalc(len(msgs.data), self.h - 2)
        self.scroll.ensureVisible(msgs.idx, center=True)
        self.resized = False
        self.qs = None  # type: Optional[QuickSearch]

    def show(self):  # type: () -> int
        self.scr.clear()
        self.drawTitle(self.scr, self.echo)
        while True:
            self.scroll.ensureVisible(self.msgs.idx)
            self.draw(self.scr)
            if self.qs:
                self.qs.draw(self.scr)
            #
            ks, key, _ = getKeystroke()
            #
            if key == curses.KEY_RESIZE:
                self.onResize()
            elif self.qs:
                if ks in Qs.CLOSE:
                    self.qs = None
                    curses.curs_set(0)
                elif ks in Qs.APPLY:
                    if self.qs.result:
                        self.msgs.modeQsOn(self.qs.result)
                        self.updateScroll()
                    self.qs = None
                    curses.curs_set(0)
                else:
                    # noinspection PyTypeChecker
                    self.qs.onKeyPressedSearch(key, ks, self.scroll)
                    self.msgs.idx = self.qs.ensureCursorVisible(
                        ks, self.msgs.idx, self.scroll)
            elif ks in Qs.OPEN:
                self.qs = newQuickSearch(self.msgs.data, self.onSearchItem)
            elif ks in Selector.ENTER and self.msgs.data:
                return self.msgs.idx  #
            elif ks in Reader.QUIT:
                if not self.msgs.stack:
                    return -1  #
                self.msgs.pop()
                self.updateScroll()
            else:
                self.onKeyPressed(ks, self.scroll)

    def drawTitle(self, win, echo):
        color = getColor(UI_BORDER)
        win.addstr(0, 0, "─" * self.w, color)
        if echo == ECHO_FIND:
            if self.w >= 80:
                drawTitle(win, 0, 0, f"Найденные сообщения"
                                     f" '{FindQueryWindow.query}'")
            else:
                drawTitle(win, 0, 0, f"'{FindQueryWindow.query}'")
        else:
            if self.w >= 80:
                drawTitle(win, 0, 0, "Список сообщений в конференции " + echo)
            else:
                drawTitle(win, 0, 0, echo)

    def draw(self, win):
        self._draw(win, self.msgs.data, self.msgs.idx, self.scroll)

    def _draw(self, win, data, cursor, scroll):
        # type: (curses.window, List[MsgMetadata], int, ScrollCalc) -> None
        for i in range(1, self.h - 1):
            color = getColor(UI_TEXT if scroll.pos + i - 1 != cursor else
                             UI_CURSOR)
            win.addstr(i, 0, " " * self.w, color)
            pos = scroll.pos + i - 1
            if pos >= scroll.content:
                continue  #
            #
            msg = data[pos]
            win.addstr(i, 0, msg.fr, color)
            win.addstr(i, 16, msg.subj[:self.w - 27], color)
            win.addstr(i, self.w - 11, msg.strtime(), color)
            #
            if self.qs and pos in self.qs.result:
                idx = self.qs.result.index(pos)
                mName, mSubj = self.qs.matches[idx]  # type: List[re.Match], List[re.Match]
                for m in mName:
                    win.addstr(i, 0 + m.start(), msg.fr[m.start():m.end()],
                               color | curses.A_REVERSE)
                for m in mSubj:
                    end = min(self.w - 27, m.end())
                    if m.start() + 16 > self.w - 12:
                        continue
                    win.addstr(i, 16 + m.start(), msg.subj[m.start():end],
                               color | curses.A_REVERSE)
        #
        if scroll.isScrollable:
            drawScrollBarV(win, 1, self.w - 1, scroll)
        drawStatusBar(win, mode=self.msgs.mode,
                      text=utils.msgnStatus(len(data), cursor, self.w))

    def updateScroll(self):
        self.scroll = ScrollCalc(len(self.msgs.data), self.h - 2)
        self.scroll.ensureVisible(self.msgs.idx, center=True)

    def onKeyPressed(self, ks, scroll):
        if ks in Reader.MSUBJ:
            if self.msgs.mode != ReaderMode.SUBJ:
                m = self.msgs.curItem()
                data = API.findSubjMsgids(m.echo, m.subj)
                self.msgs.modeSubjOn(data)
            else:
                self.msgs.modeSubjOff()
            self.updateScroll()
        elif ks in Selector.UP:
            self.msgs.idx = max(0, self.msgs.idx - 1)
        elif ks in Selector.DOWN:
            self.msgs.idx = min(scroll.content - 1, self.msgs.idx + 1)
        elif ks in Selector.PPAGE:
            if self.msgs.idx > scroll.pos:
                self.msgs.idx = scroll.pos
            else:
                self.msgs.idx = max(0, self.msgs.idx - scroll.view)
        elif ks in Selector.NPAGE:
            page_bottom = scroll.posBottom()
            if self.msgs.idx < page_bottom:
                self.msgs.idx = page_bottom
            else:
                self.msgs.idx = min(scroll.content - 1, page_bottom + scroll.view)
        elif ks in Selector.HOME:
            self.msgs.idx = 0
        elif ks in Selector.END:
            self.msgs.idx = scroll.content - 1

    # noinspection PyUnusedLocal
    @staticmethod
    def onSearchItem(sidx: int, pattern: re.Pattern, it: MsgMetadata
                     ) -> Optional[List[Tuple[List[re.Match], List[re.Match]]]]:
        resultName = utils.quickSearch(pattern, it.fr)
        resultSubj = utils.quickSearch(pattern, it.subj)
        if resultName or resultSubj:
            return [(resultName, resultSubj)]
        return None

    def onResize(self):
        self.h, self.w = self.scr.getmaxyx()
        self.drawTitle(self.scr, self.echo)
        self.scroll = ScrollCalc(len(self.msgs.data), self.h - 2)
        self.resized = True
        if self.qs:
            self.qs.y = self.h - 1
            self.qs.onResize(self.w - len(version) - 13)


class FindQueryWindow(Window):
    layout: GridLayout = None
    query = FindQuery()
    resized: bool = False
    focusedWid: Widget = None
    go: bool = True
    #
    findInProgress: bool = None
    findProgressBar = None
    findCancel: bool = False
    findResult: List[MsgMetadata] = None
    findTick: float = 0

    def __init__(self, scr, cfg: Config):
        super().__init__(scr)
        self.cfg = cfg
        self.findProgressBar = cycle(THEME.spinner)
        self.win = self.initWin()
        #
        self.inpQuery = InputRegexWidget(
            self.query.query, 1,
            placeholder="<введите текст для поиска>",
            regexOn=self.query.regex)
        self.inpQueryNot = InputRegexWidget(
            self.query.queryNot, 2,
            placeholder="<введите текст для исключения>",
            regexOn=self.query.regex)

        self.inpDtFr = InputDateWidget(2.1, dt=self.query.dtFr)
        self.inpDtTo = InputDateWidget(2.2, dt=self.query.dtTo)
        self.chkMsgid = CheckBoxWidget("Id", 3, checked=self.query.msgid)
        self.chkBody = CheckBoxWidget("Тело", 4, checked=self.query.body)
        self.chkSubj = CheckBoxWidget("Тема", 5, checked=self.query.subj)
        self.chkFrom = CheckBoxWidget("От", 6, checked=self.query.fr)
        self.chkTo = CheckBoxWidget("Кому", 7, checked=self.query.to)

        self.chkEcho = CheckBoxWidget("Конференция:", 12,
                                      checked=self.query.echo)
        self.inpEcho = InputWidget(self.query.echoQuery, 13,
                                   placeholder="<введите эхоконференцию>")
        self.inpEchoNot = InputWidget(self.query.echoQueryNot, 14,
                                      placeholder="<введите эхоконференцию>")
        self.chkSkipArch = CheckBoxWidget("Пропускать архивные", 15,
                                          checked=bool(self.query.echoSkipArch))

        self.inpLimit = InputWidget(str(self.query.limit), 16,
                                    mask=re.compile(r"^[0-9]{0,7}$"),
                                    placeholder=str(FindQuery.DEFAULT_LIMIT))

        self.chkRegex = CheckBoxWidget("Regex", 8,
                                       checked=self.query.regex)
        self.chkCase = CheckBoxWidget("Учитывать регистр", 9,
                                      checked=self.query.case)
        self.chkWord = CheckBoxWidget("Слово целиком", 10,
                                      checked=self.query.word)
        self.chkOrig = CheckBoxWidget("Пропускать подписи", 11,
                                      checked=not self.query.orig)
        self.lblProgress = LabelWidget("")

        inpErrLen = len(THEME.input.left + THEME.input.right) + THEME.error.len
        self.layout = GridLayout(
            (GridLayout(
                (LabelWidget("Искать: "), "hAlign right"),
                (self.inpQuery, "fillX growX wrap"),

                (LabelWidget("И НЕ: "), "hAlign right"),
                (self.inpQueryNot, "fillX growX wrap"),
            ), "w 100% h 2 fillX growX wrap"),
            #
            (GridLayout(
                (LabelWidget("В:"), "w 50%"),
                (LabelWidget("Дата с: "), "hAlign right"),
                (self.inpDtFr, f"hAlign left wPref {11 + inpErrLen} growX wrap"),

                (self.chkMsgid, "w 50% pad 1 0"),
                (LabelWidget("Дата по: "), "hAlign right"),
                (self.inpDtTo, f"hAlign left wPref {11 + inpErrLen} growX wrap")
            ), "w 100% h 2 fillX wrap"),
            (GridLayout(
                (SeparatorHWidget(), "colSpan 2 fillX wrap"),
                (self.chkBody, "w 50%"), (self.chkRegex, "wrap"),
                (self.chkSubj, "w 50%"), (self.chkCase, "wrap"),
                (self.chkFrom, "w 50%"), (self.chkWord, "wrap"),
                (self.chkTo, "growY"), (self.chkOrig, "wrap"),
                (SeparatorHWidget(), "colSpan 2 fillX wrap"),
            ), "pad 1 0 w 100% h 6 fillX wrap"),
            #
            (GridLayout(
                (self.chkEcho, f"w {self.chkEcho.w + 2} pad 1 0"),
                (self.inpEcho, "fillX wrap"),

                (LabelWidget("И НЕ: "), "hAlign right"),
                (self.inpEchoNot, "fillX wrap")),
             "w 100% h 2 fillX wrap"),
            (GridLayout(
                (self.chkSkipArch, "pad 1 0 w 50%"),
                (LabelWidget("Лимит: "), ""),
                (self.inpLimit, CC(wPref=(7 + len(THEME.input.left)
                                          + len(THEME.input.right)),
                                   hAlign="left",
                                   growX=True))
            ), "h 1 w 100% fillX wrap"),
            #
            (self.lblProgress, "w 100% fill growY wrap"),
        )
        self.layout.pack(offsetX=2, offsetY=1, width=self.w - 4, height=self.h - 2)
        self.widgets = deque(sorted(list(self.layout.collectWidgets()),
                                    key=lambda _: _.focusOrder))
        #
        self.setFocused(self.inpQuery)
        self.updateState()

    def setFocused(self, focusWid):  # type: (Optional[Widget]) -> None
        if self.focusedWid == focusWid:
            return
        if self.focusedWid:
            self.focusedWid.setFocused(False)
        self.focusedWid = focusWid
        if self.focusedWid:
            self.focusedWid.setFocused(True)

    def initWin(self, win=None):
        height, width = self.scr.getmaxyx()
        w = max(len(LABEL_FIND) + 2, min(80, int(width)))
        h = min(height, 16)
        w = min(width, w)
        y = max(0, int((height - h) / 2))
        x = max(0, int((width - w) / 2))
        if win:
            win.resize(h, w)
            win.mvwin(y, x)
        else:
            win = curses.newwin(h, w, y, x)
        self.h, self.w, self.y, self.x = h, w, y, x
        return win

    def show(self):
        self.drawTitle(self.win)
        while self.go:
            self._show()
            self._keys()
        return self.findResult

    def _show(self):
        self.drawContent(self.win)
        self.win.refresh()

    def _keys(self):
        if self.findInProgress:
            ks, key, _ = getKeystroke(0)
        else:
            ks, key, _ = getKeystroke()
        self.go = self.onKeyPressed(ks, key)

    def drawTitle(self, win: curses.window):
        win.bkgd(" ", curses.color_pair(config.COLOR_PAIRS[UI_TEXT][0]))
        #
        border = getColor(UI_BORDER)
        win.attrset(border)
        win.border()

        x = (self.w - len(THEME.findIcon) - len(LABEL_FIND)) // 2 - 1
        drawTitle(win, 0, x, THEME.findIcon + LABEL_FIND)

    def drawContent(self, win: curses.window):
        win.addstr(self.lblProgress.y, 1, " " * (self.w - 2))  # lbl_progress
        if self.w > 20 and self.h > 10:
            for wid in self.widgets:
                wid.draw(win)
        else:
            lines = textwrap.wrap("Маленькое окошко!", self.w - 2)
            for y, line in enumerate(lines):
                win.addstr(1 + y, 1, line + (" " * (self.w - 2 - len(line))))

    def onKeyPressed(self, ks, key):
        if key == curses.KEY_RESIZE:
            self.scr.clear()
            self.scr.refresh()
            self.win = self.initWin(self.win)
            self.win.clear()
            self.layout.pack(offsetX=2, offsetY=1, width=self.w - 4, height=self.h - 2)
            #
            self.drawTitle(self.win)
            self.resized = True
        elif ks in Qs.CLOSE:
            curses.curs_set(0)
            if self.findInProgress:
                self.findCancel = True
            else:
                return False  # close win
        elif ks in Qs.APPLY and not self.findInProgress:
            if self.inpQuery.err or self.inpDtFr.err or self.inpDtTo.err:
                self.refreshCursor()
                return True  #
            curses.curs_set(0)
            self.findTick = 0
            self.find()
            self.findCancel = False
            if self.findResult:
                return False  # close win
            self.updateState()
        elif key != -1:
            if ks in keystroke.Keys.NFOCUS or ks in keystroke.Keys.DOWN:
                wid = self.nextFocus(self.focusedWid)
                while wid and not (wid.enabled and wid.focusable):
                    wid = self.nextFocus(wid)
                self.setFocused(wid)

            elif ks in keystroke.Keys.PFOCUS or ks in keystroke.Keys.UP:
                wid = self.prevFocus(self.focusedWid)
                while wid and not (wid.enabled and wid.focusable):
                    wid = self.prevFocus(wid)
                self.setFocused(wid)

            elif self.focusedWid:
                self.focusedWid.onKeyPressed(ks, key)
            self.updateState()
        return True  #

    def nextFocus(self, wid):
        if not wid:
            return self.widgets[0]
        elif self.widgets:
            idx = self.widgets.index(wid)
            self.widgets.rotate(-1)
            return self.widgets[idx]
        return None

    def prevFocus(self, wid):
        if not wid:
            return self.widgets[0]
        elif self.widgets:
            idx = self.widgets.index(wid)
            self.widgets.rotate(1)
            return self.widgets[idx]
        return None

    def updateState(self):
        if self.findInProgress:
            return  #
        self.inpEcho.setEnabled(self.chkEcho.checked)
        self.inpEchoNot.setEnabled(self.chkEcho.checked)
        self.chkWord.setEnabled(not self.chkRegex.checked)
        self.inpQuery.setRegexOn(self.chkRegex.checked)
        self.inpQueryNot.setRegexOn(self.chkRegex.checked)

        self.query.query = self.inpQuery.txt
        self.query.queryNot = self.inpQueryNot.txt
        self.query.dtFr = self.inpDtFr.getDate()
        self.query.dtTo = self.inpDtTo.getDate()
        self.query.msgid = self.chkMsgid.checked
        self.query.body = self.chkBody.checked
        self.query.subj = self.chkSubj.checked
        self.query.fr = self.chkFrom.checked
        self.query.to = self.chkTo.checked
        self.query.echo = self.chkEcho.checked
        self.query.echoQuery = self.inpEcho.txt
        self.query.echoQueryNot = self.inpEchoNot.txt
        self.query.echoSkipArch = self.chkSkipArch.checked
        self.query.limit = int(self.inpLimit.txt or "0") or FindQuery.DEFAULT_LIMIT
        self.query.regex = self.chkRegex.checked
        self.query.case = self.chkCase.checked
        self.query.word = self.chkWord.checked
        self.query.orig = not self.chkOrig.checked

        if self.findInProgress is None:
            self.lblProgress.setTxt("")
        else:
            self.lblProgress.setTxt("Ничего не найдено")
        self.refreshCursor()

    def refreshCursor(self):
        if isinstance(self.focusedWid, InputWidget):
            y, x = self.win.getbegyx()
            inp_cursor_x = self.focusedWid.getWinCursorPos()
            stdscr.move(y + self.focusedWid.y,
                        x + self.focusedWid.x + inp_cursor_x)
            curses.curs_set(1)
        else:
            curses.curs_set(0)

    def find(self):
        self.findInProgress = True
        if self.query.echoSkipArch:
            arch = []
            for node in self.cfg.nodes:
                arch += list(map(lambda e: e.name, node.archive + node.stat))
            self.query.echoArch = " ".join(arch)

        self.findResult = API.findQueryMsgids(
            self.query, progressHandler=self._findProgressHandler)
        self.findInProgress = False

    def _findProgressHandler(self, param=None):
        now = time.time()
        self._keys()
        if self.findCancel:
            return API.FIND_CANCEL
        if (now - self.findTick) < 0.250:  # ms
            return API.FIND_OK
        self.findTick = now
        progress = f" Поиск{THEME.ellipsis} " + next(self.findProgressBar)
        if param:
            progress += (
                    f" Found: {param[5]}"
                    f" TMsg: {param[4]}" + (f"/{param[6]}" if len(param) > 6 else "") +
                    (f" E: {param[0]}/{param[1]}" if param[0] or param[1] else "") +
                    (f" EMsg: {param[2]}/{param[3]}" if param[2] or param[3] else "")
            )
        self.lblProgress.setTxt(progress)
        self._show()
        return API.FIND_OK


class Pager:
    pos: int = 0

    def __init__(self, pos, nextPageTop, prevPageBottom):
        self.pos = pos
        self.nextPageTop = nextPageTop
        self.prevPageBottom = prevPageBottom

    def nextPageTop(self):
        pass

    def prevPageBottom(self):
        pass


def newQuickSearch(items, matcher):
    h, w = stdscr.getmaxyx()
    stdscr.move(h - 1, len(version) + 2)
    curses.curs_set(1)
    return QuickSearch(items, matcher,
                       y=h - 1, x=len(version) + 2,
                       w=w - len(version) - 13)


class QuickSearch(InputRegexWidget):
    def __init__(self, items, matcher,
                 y=0, x=0, w=0, *, placeholder=LABEL_SEARCH, color=UI_STATUS):
        super().__init__(y=y, x=x, w=w, placeholder=placeholder, regexOn=True)
        self.items = items
        self.matches = []
        self.result = []
        self.idx = 0
        self.matcher = matcher
        self.color = getColor(color)
        self.statTxt = ""
        self.statPos = 0

    def draw(self, win):
        # type: (curses.window) -> None
        super().draw(win)
        if self.txt and not self.err:
            win.addstr(self.y, self.x + self.statPos, self.statTxt, self.color)
        win.move(self.y, self.x + self.getWinCursorPos())

    def search(self, query, pos):
        self.result = []
        self.matches = []
        self.idx = -1

        if self.txt != query:
            self.txt = query
            self.template = self._compileRegex()
        if not (query and self.template):
            return  #

        sidx = 0
        for i, item in enumerate(self.items):
            if matches := self.matcher(sidx, self.template, item):
                for m in matches:
                    self.result.append(i)
                    self.matches.append(m)
                    sidx += 1
                    if self.idx == -1 and i >= pos:
                        self.idx = len(self.result) - 1

    def onKeyPressedSearch(self, key, ks, pager: Pager):
        prevTxt = self.txt
        if ks in Qs.HOME:
            self.home()
        elif ks in Qs.END:
            self.end()
        elif ks in Qs.NEXT:
            self.next()
        elif ks in Qs.PREV:
            self.prev()
        elif ks in Qs.NPAGE:
            self.nextAfter(pager.nextPageTop())
        elif ks in Qs.PPAGE:
            self.prevBefore(pager.prevPageBottom())
        elif ks in Qs.LEFT:
            self._moveCursorLeft(1)
        elif ks in Qs.RIGHT:
            self._moveCursorRight(1)
        elif ks in Qs.BS:
            self._delPrevChar()
        elif ks in Qs.DEL:
            self._delCurrentChar()
        else:
            super().onKeyPressed(ks, key)

        if self.txt != prevTxt:
            self.search(self.txt, pager.pos)

        if self.txt and not self.err:
            idx = self.idx + 1 if self.result else 0
            self.statTxt = "(%d/%d)" % (idx, len(self.result))
            self.statPos = self.w - len(self.statTxt) - len(THEME.input.right)
            if self.getWinCursorPos() + 1 >= self.statPos:
                self.offset += self.getWinCursorPos() + 1 - self.statPos
        elif self.err:
            errPos = self.w - THEME.error.len - len(THEME.input.right)
            if self.getWinCursorPos() + 1 >= errPos:
                self.offset += self.getWinCursorPos() + 1 - errPos

    def home(self):
        self.idx = 0

    def end(self):
        self.idx = len(self.result) - 1

    def next(self):
        self.idx += 1
        if self.idx >= len(self.result):
            self.idx = 0

    def prev(self):
        self.idx -= 1
        if self.idx < 0:
            self.idx = len(self.result) - 1

    def nextAfter(self, pos):
        if not self.result:
            return  #
        while self.result[self.idx] < pos:
            self.idx += 1
            if self.idx >= len(self.result):
                self.end()
                break  #

    def prevBefore(self, pos):
        if not self.result:
            return  #
        while self.result[self.idx] > pos:
            self.idx -= 1
            if self.idx < 0:
                self.home()
                break  #

    def ensureCursorVisible(self, ks, cursor, scroll):
        if self.result:
            cursor = self.result[self.idx]
            if ks in Qs.NPAGE:
                scroll.pos = cursor
            elif ks in Qs.PPAGE:
                scroll.pos = cursor - scroll.view
            scroll.ensureVisible(cursor)
        return cursor

    def onResize(self, w):
        self.w = w
        self.statPos = self.w - len(self.statTxt) - len(THEME.input.right)


# region EchoReader
class ReaderWidget(Widget):
    tokens: List[parser.Token]  # message bode tokens
    scrollV: ScrollCalc = None  # message body scroll calculator (vertical)
    scrollH: ScrollCalc = None  # message body scroll calculator (horizontal)
    t2l: List[parser.RangeLines]  # tokens rendered lines range
    #
    msg: List[str] = None
    size: int = 0

    def __init__(self):
        self.msg = ["", "", "", "", "", "", "", "", "Сообщение отсутствует в базе"]

    def setRect(self, x=None, y=None, w=None, h=None):
        if x is not None:
            self.x = x
        if y is not None:
            self.y = y
        if w is not None:
            self.w = w
        if h is not None:
            self.h = h

    def setMsg(self, msg, size):
        self.msg = msg
        self.size = size

    def prerender(self, pos=0):
        self.tokens = parser.tokenize(self.msg[8:])
        height, maxWidth, hScroll = parser.prerender(self.tokens, self.w, self.h)
        self.t2l = parser.tokenLineMap(self.tokens)
        self.scrollV = ScrollCalc(
            height, self.h - (1 if hScroll else 0), pos)
        self.scrollH = ScrollCalc(
            maxWidth, self.w - (1 if self.scrollV.isScrollable else 0), 0)

    def draw(self, scr, qs=None):
        self.renderBody(scr, self.tokens, self.scrollV.pos, self.scrollH.pos, qs)
        if self.scrollV.isScrollable:
            drawScrollBarV(scr, self.y, self.x + self.w - 1, self.scrollV)
        if self.scrollH.isScrollable:
            drawScrollBarH(scr, self.y + self.h - 1, 0, self.scrollH)

    def renderBody(self, scr, tokens, scroll, scrollH=0, qs=None):
        # type: (curses.window, List[parser.Token], int, int, QuickSearch) -> None
        if not tokens:
            return
        tnum, offset = parser.findVisibleToken(tokens, scroll)
        lineNum = tokens[tnum].lineNum
        y, x = (self.y, self.x)
        h, w = (self.y + self.h, self.x + self.w)
        if self.scrollH and self.scrollH.isScrollable:
            h -= 1
        if self.scrollV and self.scrollV.isScrollable:
            w -= 1
        txtAttr = 0
        if parser.INLINE_STYLE_ENABLED:
            # Rewind tokens from the begin of line to apply inline text attributes
            firstToken = tnum
            while tokens[firstToken].lineNum == lineNum and firstToken > 0:
                firstToken -= 1
            for token in tokens[firstToken:tnum]:
                txtAttr = ReaderWidget.applyAttr(token, txtAttr)

        for token in tokens[tnum:]:
            if token.lineNum > lineNum:
                lineNum = token.lineNum
                y, x = (y + 1, self.x)
            if y >= h:
                break  # tokens
            #
            txtAttr = ReaderWidget.applyAttr(token, txtAttr)
            #
            y, x = self.renderToken(scr, token, y, x, w, h, offset,
                                    scrollH, txtAttr, qs)
            offset = 0  # required in the first partial multiline token only

    @staticmethod
    def applyAttr(token, txtAttr):
        if token.type == parser.TT.URL:
            txtAttr |= curses.A_UNDERLINE
        else:
            txtAttr &= ~curses.A_UNDERLINE

        if token.type == parser.TT.ITALIC_BEGIN:
            txtAttr |= curses.A_ITALIC
        elif token.type == parser.TT.ITALIC_END:
            txtAttr &= ~curses.A_ITALIC

        elif token.type == parser.TT.BOLD_BEGIN:
            txtAttr |= curses.A_BOLD
        elif token.type == parser.TT.BOLD_END:
            txtAttr &= ~curses.A_BOLD
        return txtAttr

    def renderToken(self, scr, token: parser.Token, y, x, w, h, offset, scrollH, txtAttr, qs=None):
        matches = []
        # noinspection PyUnresolvedReferences
        if (qs and qs.result
                and hasattr(token, 'searchIdx')
                and token.searchIdx is not None):
            # noinspection PyUnresolvedReferences
            matches = token.searchMatches
        #
        for i, line in enumerate(token.render[offset:]):
            if y + i >= h:
                return y + i, x  #
            attr = getColor(TOKEN2UI.get(token.type, UI_TEXT))
            if line:
                dx = x - self.x - scrollH
                eol = w - (x - self.x - scrollH - dx)
                if x == self.x:
                    scr.addstr(y + i, self.x, line[scrollH:scrollH + w], attr | txtAttr)
                elif dx >= 0:
                    scr.addstr(y + i, self.x + dx, line[0:eol], attr | txtAttr)
                elif -dx < len(line):
                    scr.addstr(y + i, self.x, line[-dx:-dx + eol], attr | txtAttr)

                for off, match in matches:
                    if (off != offset + i
                            or x + match.end() - scrollH - self.x < 0
                            or x + match.start() - scrollH - self.x >= w):
                        continue  # matches
                    dx = x - self.x - scrollH + match.start()
                    if dx >= 0:
                        txt = line[match.start():min(match.end(), match.start() - dx + eol)]
                    else:
                        txt = line[-dx + match.start():min(match.end(), match.start() + (-dx + eol))]
                    scr.addstr(y + i, self.x + max(0, dx), txt,
                               attr | txtAttr | curses.A_REVERSE)

            if len(token.render) > 1 and i + offset < len(token.render) - 1:
                x = self.x  # new line in multiline token -- carriage return
            else:
                x += len(line)  # last/single line -- move caret in line
        return y + (len(token.render) - 1) - offset, x  #

    def onKeyPressed(self, ks, key):
        # vertical
        if ks in Reader.UP:
            self.scrollV.pos -= 1
        elif ks in Reader.DOWN:
            self.scrollV.pos += 1
        elif ks in Reader.PPAGE:
            self.scrollV.pos -= self.scrollV.view
        elif ks in Reader.NPAGE:
            self.scrollV.pos += self.scrollV.view
        elif ks in Reader.HOME:
            self.scrollV.pos = 0
        # horizontal
        elif ks in Reader.LEFT:
            self.scrollH.pos -= 1
        elif ks in Reader.RIGHT:
            self.scrollH.pos += 1
        elif ks in Reader.LEFTP:
            self.scrollH.pos -= self.scrollH.view
        elif ks in Reader.RIGHTP:
            self.scrollH.pos += self.scrollH.view
        elif ks in Reader.MEND:
            self.scrollV.pos = self.scrollV.content - self.scrollV.view
        else:
            return False  # not handled
        return True  # handled

    # region QuickSearch
    def qsPager(self):
        return Pager(
            parser.findVisibleToken(self.tokens, self.scrollV.pos)[0],
            lambda: parser.findVisibleToken(self.tokens, self.scrollV.pos + self.scrollV.view)[0],
            lambda: parser.findVisibleToken(self.tokens, self.scrollV.pos)[0] - 1)

    def ensureVisibleOnQsKey(self, ks, tidx, off):
        if ks in Qs.HOME or ks in Qs.END:
            self.scrollV.ensureVisible(self.t2l[tidx].start + off, center=True)
        elif ks in Qs.NPAGE:
            self.scrollV.ensureVisible(self.t2l[tidx].start + off + self.scrollV.view - 1)
        elif ks in Qs.PPAGE:
            self.scrollV.ensureVisible(self.t2l[tidx].start + off - self.scrollV.view + 1)
        else:
            self.scrollV.ensureVisible(self.t2l[tidx].start + off)
    # endregion QuickSearch


def signMsg(node, out, keyId):
    nodeDir = mailer.directory(node)
    with open(nodeDir + out, "r") as f:
        msg = f.read().split("\n")
    if msg[4].startswith("@repto"):
        header = "\n".join(msg[0:5])
        body = "\n".join(msg[5:])
    else:
        header = "\n".join(msg[0:4])
        body = "\n".join(msg[4:])
    result = parser.gpg.sign(body.encode("utf-8"), keyid=keyId, clearsign=True)
    if result.returncode == 0:
        signedBody = str(result.data, encoding="utf-8")
        if len(signedBody) > len(body):
            with open(nodeDir + out, "w") as f:
                f.write(header)
                f.write("\n")
                f.write(signedBody)
    else:
        showMessageBox(result.stderr)


def saveMessageToFile(msgid, echoarea):
    msg, size = API.readMsg(msgid, echoarea)
    filepath = "downloads/" + msgid + ".txt"
    with open(filepath, "w") as f:
        f.write("== " + msg[1] + " ==================== " + msgid + "\n")
        f.write("От:   " + msg[3] + " (" + msg[4] + ")\n")
        f.write("Кому: " + msg[5] + "\n")
        f.write("Тема: " + msg[6] + "\n")
        f.write("\n".join(msg[7:]))
    showMessageBox("Сообщение сохранено в файл\n" + filepath)


def getMsg(msgid):
    node = CFG.node()
    bundle = client.getBundle(node.url, msgid)
    for msg in filter(None, bundle):
        m = msg.split(":")
        msgid = m[0]
        if len(msgid) == 20 and m[1]:
            msgbody = base64.b64decode(m[1].encode("ascii")).decode("utf8").split("\n")
            if node.to:
                carbonarea = API.getCarbonarea()
                if msgbody[5] in node.to and msgid not in carbonarea:
                    API.addToCarbonarea(msgid, msgbody)
            API.saveMessage([(msgid, msgbody)], node, node.to)


def saveAttachment(token):  # type: (parser.Token) -> None
    filepath = "downloads/" + token.filename
    with open(filepath, "wb") as attachment:
        attachment.write(token.filedata)
    drawMessageBox("Файл сохранён '%s'" % filepath, True)
    stdscr.getch()
    if token.pgpKey and parser.gpg:
        option = SelectWindow(stdscr, "PGP Ключ '%s'" % token.filename,
                              ["Отмена",
                               "Открыть файл",
                               "Добавить в хранилище"]).show()
        if option == 2:
            utils.openFile(filepath)
        elif option == 3:
            result = parser.gpg.import_keys_file(filepath)
            smsg = "\n".join(map(lambda rd: json.dumps(rd, sort_keys=True, indent=2),
                                 filter(lambda r: r['fingerprint'], result.results)))
            showMessageBox(smsg)
    else:
        if SelectWindow(stdscr, "Открыть '%s'?" % token.filename,
                        ["Нет", "Да"]).show() == 2:
            utils.openFile(filepath)


class EchoReaderScreen(Window):
    _msgid: Optional[str] = None  # non-current-echo message id, navigated by ii-link
    qs: Optional[QuickSearch] = None  # quick search helper
    reader: ReaderWidget = None
    #
    go: bool = True  # show reader
    done: bool = False  # close app
    nextEcho: Union[str, bool] = False  # jump to next echo after reader closed
    resized: bool = False

    def __init__(self, scr: curses.window,
                 echo: config.Echo, msgn, archive, counts,
                 mode=ReaderMode.ECHO, msgids=None):
        super().__init__(scr)
        self.echo = echo
        self.msgs = MsgModeStack(mode, msgids, msgn)
        self.archive = archive
        self.counts = counts
        #
        self.out = (echo in (config.ECHO_OUT, config.ECHO_DRAFTS))
        self.drafts = (echo == config.ECHO_DRAFTS)
        self.favorites = (echo == config.ECHO_FAVORITES)
        self.carbonarea = (echo == config.ECHO_CARBON)
        #
        self.repto = ""
        self.stack = []
        if not msgids:
            self.msgs.data = self.getMsgsMetadata()
        else:
            self.msgs.data = msgids
        #
        self.reader = ReaderWidget()
        self.reader.setRect(x=0, y=5, w=self.w, h=self.h - 5 - 1)
        #
        self.msgs.idx = min(msgn, len(self.msgs.data) - 1)
        if self.msgs.data:
            self.readMsgSkipTwit(-1)
            if self.msgs.idx < 0:
                self.nextEcho = True
        self.reader.prerender()

    def msgid(self):
        m = self.msgs.curItem()
        return self._msgid or (m.msgid if m else "")

    def getMsgsMetadata(self):
        if self.out:
            return mailer.getOutMsgsMetadata(CFG.node(), self.drafts)
        elif self.echo == config.ECHO_FIND:
            return self.msgs.data  #
        else:
            return API.getEchoMsgsMetadata(self.echo.name)

    def readCurMsg(self):  # type: () -> (List[str], int)
        self._msgid = None
        if self.out and "." in self.msgid():  # .out, .outmsg, .draft
            self.reader.setMsg(*mailer.readOutMsg(self.msgid(), CFG.node()))
        else:
            m = self.msgs.curItem()
            if not m and self.msgs.data:
                self.msgs.idx = 0
                m = self.msgs.curItem()
            if m:
                self.reader.setMsg(*API.readMsg(self._msgid or m.msgid, m.echo))
            else:
                self.reader.setMsg(*API.readMsg("unknown", "unknown"))

    def readMsgSkipTwit(self, increment):
        self.readCurMsg()
        while self.reader.msg[3] in CFG.twit or self.reader.msg[5] in CFG.twit:
            self.msgs.idx += increment
            if self.msgs.idx < 0 or len(self.msgs.data) <= self.msgs.idx:
                break
            self.readCurMsg()

    def reloadMsgsOrQuit(self):
        self.msgs.data = self.getMsgsMetadata()
        if self.msgs.data:
            if self.msgs.stack:
                self.msgs.mode = self.msgs.stack[0][0]
                self.msgs.stack.clear()
            self.msgs.idx = min(self.msgs.idx, len(self.msgs.data) - 1)
            self.readCurMsg()
            self.reader.prerender()
        else:
            self.go = False

    def showOpenLinkDialog(self, tokens):
        links = list(filter(lambda it: it.type == parser.TT.URL, tokens))
        if len(links) == 1:
            self.openLink(links[0])
        elif links:
            win = SelectWindow(self.scr, "Выберите ссылку", list(map(
                lambda it: (it.url + " " + (it.title or "")).strip(),
                links)))
            i = win.show()
            if win.resized:
                self.onResize()
            if i:
                self.openLink(links[i - 1])

    def openLink(self, token):  # type: (parser.Token) -> None
        link = token.url
        if token.filename:
            if token.filedata:
                saveAttachment(token)
        elif link.startswith("#"):  # markdown anchor?
            pos = parser.findAnchorPos(self.reader.tokens, token)
            if pos != -1:
                self.reader.scrollV.pos = pos
        elif not link.startswith("ii://"):
            if not CFG.browser.open(link):
                showMessageBox("Не удалось запустить Интернет-браузер")
        else:  # ii://
            link = link[5:]
            link = link.rstrip("/")
            if "/" in link:  # support ii://echo.area/msgid123
                link = link[link.rindex("/"):]
            if parser.echoTemplate.match(link):  # echoarea
                if self.echo.name == link:
                    showMessageBox("Конференция уже открыта")
                elif (link in CFG.node().echoareas
                      or link in CFG.node().archive
                      or link in CFG.node().stat):
                    self.nextEcho = link
                    self.go = False
                else:
                    showMessageBox("Конференция отсутствует в БД ноды")
            elif link:
                idx = self.msgs.findMsgidIdx(link)
                if idx > -1:  # msgid in same echoarea
                    if not self.stack or self.stack[-1] != self.msgs.idx:
                        self.stack.append(self.msgs.idx)
                    self.msgs.idx = idx
                    self.readCurMsg()
                else:
                    self.reader.setMsg(*API.findMsg(link))
                    self._msgid = link
                    if not self.stack or self.stack[-1] != self.msgs.idx:
                        self.stack.append(self.msgs.idx)
                self.reader.prerender()

    @staticmethod
    def onSearchItem(sidx: int, pattern: re.Pattern, token: parser.Token
                     ) -> Optional[List[Tuple[int, re.Match]]]:
        matches = []
        for offset, line in enumerate(token.render):
            lineMatches = map(lambda m: (offset, m),
                              utils.quickSearch(pattern, line))
            matches.extend(lineMatches)
        if matches:
            token.searchIdx = sidx
            token.searchMatches = matches
        else:
            token.searchIdx = None
            token.searchMatches = None
        return matches or None

    def show(self):
        try:
            while self.go:
                self._show(self.msgs, self.reader)
        except SystemExit:
            self.done = True

        if self.msgs.mode == ReaderMode.ECHO:
            self.counts.lasts[self.echo.name] = self.msgs.idx
            with open("lasts.lst", "wb") as f:
                pickle.dump(self.counts.lasts, f)
        self.scr.clear()
        return not self.done, self.nextEcho

    def _show(self, msgs: MsgModeStack, reader: ReaderWidget):
        self.scr.clear()
        status = None
        if msgs.data:
            self.draw(self.scr)
            status = utils.msgnStatus(len(msgs.data), msgs.idx, self.w)
        else:
            drawReader(self.scr, self.echo.name, "", self.out)
        drawStatusBar(self.scr, mode=msgs.mode, text=status)
        if self.qs:
            self.qs.draw(self.scr)
        #
        ks, key, _ = getKeystroke()
        #
        if key == curses.KEY_RESIZE:
            self.onResize()
        elif self.qs:
            self.onKeyPressedQs(ks, key)
        elif ks in Qs.OPEN:
            self.qs = newQuickSearch(reader.tokens, self.onSearchItem)
        elif ks in Reader.QUIT:
            if msgs.stack:
                self.modeRestore()
            else:
                self.go = False
                self.nextEcho = False
        elif ks in Common.QUIT:
            self.go = False
            self.done = True
        elif reader.onKeyPressed(ks, key):
            return  #
        else:
            self.onKeyPressed(ks, key)

    def draw(self, scr):
        self._draw(scr, self.w, self.reader)

    def _draw(self, scr, w, reader):
        drawReader(scr, reader.msg[1], self.msgid(), self.out)
        if w >= 80 and self.echo == config.ECHO_FIND:
            title = f"Найденные сообщения '{FindQueryWindow.query}'"
            drawTitle(scr, 0, w - 2 - len(title), title)
        elif w >= 80 and self.echo.desc:
            drawTitle(scr, 0, w - 2 - len(self.echo.desc), self.echo.desc)

        color = getColor(UI_TEXT)
        if not self.out:
            if w >= 80:
                scr.addstr(1, 7, reader.msg[3] + " (" + reader.msg[4] + ")", color)
            else:
                scr.addstr(1, 7, reader.msg[3], color)
            msgtime = utils.msgStrftime(reader.msg[2], w)
            scr.addstr(1, w - len(msgtime) - 1, msgtime, color)
        elif CFG.node().to:
            scr.addstr(1, 7, CFG.node().to[0], color)
        scr.addstr(2, 7, reader.msg[5], color)
        scr.addstr(3, 7, reader.msg[6][:w - 8], color)
        strSize = utils.msgStrfsize(reader.size)
        drawTitle(scr, 4, 0, strSize)
        tags = reader.msg[0].split("/")
        if "repto" in tags and 36 + len(strSize) < w:
            self.repto = tags[tags.index("repto") + 1].strip()
            drawTitle(scr, 4, len(strSize) + 3, "Ответ на " + self.repto)
        else:
            self.repto = ""
        reader.draw(scr, self.qs)

    def onKeyPressedQs(self, ks, key):
        if ks in Qs.CLOSE or ks in Qs.APPLY:
            self.qs = None
            curses.curs_set(0)
            return
        #
        self.qs.onKeyPressedSearch(key, ks, self.reader.qsPager())
        if self.qs.result:
            tidx = self.qs.result[self.qs.idx]
            off, _ = self.qs.matches[self.qs.idx]
            self.reader.ensureVisibleOnQsKey(ks, tidx, off)

    def modeRestore(self):
        m = self.msgs.curItem()
        msgid = m.msgid if m else ""
        self.msgs.pop()
        if msgid != self.msgs.curItem().msgid:
            self.stack.clear()
            self.readCurMsg()
            self.reader.prerender()

    def onKeyPressed(self, ks: str, key: int):
        self._onKeyPressed(ks, self.msgs, self.reader)

    def _onKeyPressed(self, ks, msgs: MsgModeStack, reader: ReaderWidget):
        if ks in Reader.MSUBJ:
            if msgs.mode != ReaderMode.SUBJ:
                data = API.findSubjMsgids(reader.msg[1], reader.msg[6])
                msgs.modeSubjOn(data)
                if msgs.data and msgs.idx == -1:
                    msgs.idx = 0
            else:
                msgs.modeSubjOff()
            self.stack.clear()
            self.readCurMsg()
            reader.prerender()

        elif ks in Reader.PREV and msgs.idx > 0 and msgs.data:
            msgs.idx -= 1
            self.stack.clear()
            tmp = msgs.idx
            self.readMsgSkipTwit(-1)
            if msgs.idx < 0:
                msgs.idx = tmp + 1
            reader.prerender()

        elif ks in Reader.NEXT and msgs.hasNext():
            msgs.idx += 1
            self.stack.clear()
            self.readMsgSkipTwit(+1)
            if msgs.idx >= len(msgs.data):
                if msgs.mode == ReaderMode.ECHO:
                    self.go = False
                    self.nextEcho = True
                else:
                    msgs.idx = len(msgs.data) - 1
            reader.prerender()

        elif ks in Reader.NEXT and not msgs.hasNext():
            if msgs.mode == ReaderMode.ECHO:
                self.go = False
                self.nextEcho = True

        elif ks in Reader.PREP and not any((self.favorites, self.carbonarea, self.out)) and self.repto:
            idx = msgs.findMsgidIdx(self.repto)
            if idx > -1:
                self.stack.append(msgs.idx)
                msgs.idx = idx
                self.readCurMsg()
            else:
                reader.setMsg(*API.findMsg(self.repto))
                self._msgid = self.repto
                if not self.stack or self.stack[-1] != msgs.idx:
                    self.stack.append(msgs.idx)
            reader.prerender()

        elif ks in Reader.NREP and len(self.stack) > 0:
            msgs.idx = self.stack.pop()
            self.readCurMsg()
            reader.prerender()

        elif ks in Reader.UKEYS:
            if not msgs.data or reader.scrollV.pos >= reader.scrollV.content - reader.scrollV.view:
                if not msgs.hasNext():
                    if msgs.mode == ReaderMode.ECHO:
                        self.nextEcho = True
                        self.go = False
                else:
                    msgs.idx += 1
                    self.stack.clear()
                    self.readCurMsg()
                    reader.prerender()
            else:
                reader.scrollV.pos += reader.scrollV.view

        elif ks in Reader.BEGIN and msgs.data:
            msgs.idx = 0
            self.stack.clear()
            self.readCurMsg()
            reader.prerender()

        elif ks in Reader.END and msgs.data:
            msgs.idx = len(msgs.data) - 1
            self.stack.clear()
            self.readCurMsg()
            reader.prerender()

        elif ks in Reader.INS and not any((self.archive, self.out, self.favorites, self.carbonarea)):
            mailer.newMsg(self.echo.name)
            callEditor(CFG.node())
            self.counts.getCounts(CFG.node(), False)

        elif ks in Reader.SAVE and not self.out:
            saveMessageToFile(self.msgid(), reader.msg[1])

        elif ks in Reader.FAVORITES and not self.out:
            saved = API.saveToFavorites(self.msgid(), reader.msg)
            drawMessageBox("Подождите", False)
            self.counts.getCounts(CFG.node(), False)
            showMessageBox("Сообщение добавлено в избранные" if saved else
                           "Сообщение уже есть в избранных")

        elif ((ks in Reader.QUOTE or ks in Reader.QUOTE_NOT)
              and not any((self.archive, self.out)) and msgs.data):
            mode = CFG.oldquote
            if ks in Reader.QUOTE_NOT:
                mode = not CFG.oldquote
            mailer.quoteMsg(self.msgid(), reader.msg, mode)
            callEditor(CFG.node())
            self.counts.getCounts(CFG.node(), False)

        elif ks in Reader.INFO:
            subj = textwrap.fill(reader.msg[6], int(self.w * 0.75) - 8,
                                 subsequent_indent="      ")
            showMessageBox("id:   %s\naddr: %s\nsubj: %s"
                           % (self.msgid(), reader.msg[4], subj))

        elif ks in Out.EDIT and self.out:
            if self.msgid().endswith(".out") or self.msgid().endswith(".draft"):
                copyfile(mailer.directory(CFG.node()) + self.msgid(), "temp")
                callEditor(CFG.node(), self.msgid())
                self.reloadMsgsOrQuit()
            else:
                showMessageBox("Сообщение уже отправлено")

        elif ks in Out.SIGN and self.out:
            self.signMsg()

        elif ks in Out.DEL and self.favorites and msgs.data:
            drawMessageBox("Подождите", False)
            API.removeFromFavorites(self.msgid())
            self.counts.getCounts(CFG.node(), False)
            self.reloadMsgsOrQuit()

        elif ks in Out.DEL and self.drafts and msgs.data:
            if SelectWindow(self.scr, "Удалить черновик '%s'?" % self.msgid(),
                            ["Нет", "Да"]).show() == 2:
                os.remove(mailer.directory(CFG.node()) + self.msgid())
                self.counts.getCounts(CFG.node(), False)
                self.reloadMsgsOrQuit()

        elif ks in Reader.GETMSG and reader.size == 0 and self._msgid:
            try:
                drawMessageBox("Подождите", False)
                getMsg(self._msgid)
                self.counts.getCounts(CFG.node(), True)
                reader.setMsg(*API.findMsg(self._msgid))
                reader.prerender()
            except Exception as ex:
                showMessageBox("Не удалось определить msgid.\n" + str(ex))

        elif ks in Reader.LINKS:
            self.showOpenLinkDialog(reader.tokens)

        elif ks in Reader.TO_OUT and self.drafts:
            draft = mailer.directory(CFG.node()) + self.msgid()
            os.rename(draft, draft.replace(".draft", ".out"))
            self.counts.getCounts(CFG.node(), False)
            self.reloadMsgsOrQuit()

        elif ks in Reader.TO_DRAFTS and self.out and not self.drafts:
            if self.msgid().endswith(".out"):
                out = mailer.directory(CFG.node()) + self.msgid()
                os.rename(out, out.replace(".out", ".draft"))
                self.counts.getCounts(CFG.node(), False)
                self.reloadMsgsOrQuit()
            else:
                showMessageBox("Сообщение уже отправлено")

        elif ks in Reader.LIST and msgs.data:
            mode = msgs.mode
            msgid = msgs.curItem().msgid
            win = MsgListScreen(self.scr, self.echo.name, self.msgs)
            selectedMsgn = win.show()
            msgs = win.msgs
            self.msgs = win.msgs
            if selectedMsgn == -1:
                msgs.idx = msgs.findMsgidIdx(msgid)
            if mode != msgs.mode or selectedMsgn > -1:
                if win.resized:
                    self.resized = True
                    self.h, self.w = self.scr.getmaxyx()
                    self.reader.setRect(x=0, y=5, w=self.w, h=self.h - 5 - 1)
                self.stack.clear()
                self.readCurMsg()
                reader.prerender()
            elif win.resized:
                self.onResize()

        elif ks in Reader.INLINES:
            parser.INLINE_STYLE_ENABLED = not parser.INLINE_STYLE_ENABLED
            reader.prerender(reader.scrollV.pos)

        elif ks in Reader.HSCROLL:
            parser.HORIZONTAL_SCROLL_ENABLED = not parser.HORIZONTAL_SCROLL_ENABLED
            reader.prerender(reader.scrollV.pos)

    def onResize(self):
        self.resized = True
        self.h, self.w = self.scr.getmaxyx()
        self.reader.setRect(x=0, y=5, w=self.w, h=self.h - 5 - 1)
        self.reader.prerender(self.reader.scrollV.pos)
        self.scr.clear()
        if self.qs:
            self.qs.items = self.reader.tokens
            self.qs.y = self.h - 1
            self.qs.onResize(self.w - len(version) - 13)
            tnum, _ = parser.findVisibleToken(self.reader.tokens,
                                              self.reader.scrollV.pos)
            self.qs.search(self.qs.txt, tnum)

    def signMsg(self):
        if (not self.msgid().endswith(".out")
                and not self.msgid().endswith(".draft")):
            showMessageBox("Подпись невозможна."
                           " Сообщение уже отправлено")
            return  #

        if not parser.gpg:
            showMessageBox("Подпись невозможна."
                           " Не установлен пакет python-gnupg")
            return  #

        privateKeys = parser.gpg.list_keys(secret=True)
        if not privateKeys:
            showMessageBox("Не удалось подписать сообщение.\n"
                           "Нет приватных ключей в хранилище:\n%s"
                           % os.path.abspath(parser.gpg.gnupghome))
            return  #

        items = []
        for k in privateKeys:
            user = k['uids'][0]
            items.append((k['keyid'], "%s (%s)" % (user, k['keyid'])))
        selected = SelectWindow(self.scr, "Подписать ключом",
                                [it[1] for it in items]).show()
        if selected > 0:
            signMsg(CFG.node(), self.msgid(), items[selected - 1][0])
            self.readCurMsg()
            self.reader.prerender()
# endregion EchoReader


# region EchoSelector
def callEditor(node, out=''):
    terminateCurses()
    h = hashlib.sha1(str.encode(open("temp", "r", ).read())).hexdigest()
    subprocess.Popen(CFG.editor + " ./temp", shell=True).wait()
    initializeCurses()
    if h != hashlib.sha1(str.encode(open("temp", "r", ).read())).hexdigest():
        if not out:
            filepath = mailer.outcount(node) + ".draft"
        else:
            filepath = mailer.directory(node) + out
        mailer.saveOut(filepath)
    else:
        os.remove("temp")


class Counts:
    total: dict[str, int]
    lasts: dict[str, int]
    counts: List[List[str]]

    def __init__(self):
        self.total = {}
        self.lasts = {}
        if os.path.exists("lasts.lst"):
            with open("lasts.lst", "rb") as f:
                self.lasts = pickle.load(f)

    def getLast(self, echo):
        last = 0
        if echo.name in self.lasts:
            last = self.lasts[echo.name]
        return max(0, min(self.total[echo.name], last))

    def getCounts(self, node, new=False):
        for echo in node.echoareas:  # type: config.Echo
            if new or echo.name not in self.total:
                self.total[echo.name] = API.getEchoLength(echo.name)
        for echo in node.archive:  # type: config.Echo
            if echo.name not in self.total:
                self.total[echo.name] = API.getEchoLength(echo.name)
        self.total[config.ECHO_CARBON.name] = len(API.getCarbonarea())
        self.total[config.ECHO_FAVORITES.name] = len(API.getFavoritesList())
        self.total[config.ECHO_DRAFTS.name] = mailer.getOutLength(node, True)
        self.total[config.ECHO_OUT.name] = mailer.getOutLength(node, False)

    def rescanCounts(self, echoareas):
        self.counts = []
        for echo in echoareas:
            total = self.total[echo.name]
            if echo.name in self.lasts:
                unread = total - self.lasts[echo.name]
            else:
                unread = total + 1
            unread = max(1, unread)
            self.counts.append([str(total), str(unread - 1)])
        return self.counts

    def findNew(self, cursor):
        for n, (_, unread) in enumerate(self.counts):
            if n >= cursor and int(unread) > 0:
                return n
        return cursor


class EchoSelectorScreen(Window):
    echoCursor: int = 0
    archiveCursor: int = 0
    nextEcho: bool = False
    echos: EchoModeStack = None
    scroll: ScrollCalc = None
    qs: Optional[QuickSearch] = None
    go: bool = True

    def __init__(self, scr: curses.window, onEditCfg: Callable):
        super().__init__(scr)
        self.counts = Counts()
        self.reloadEchoareas()
        self.onEditCfg = onEditCfg

    def reloadEchoareas(self):
        self.echoCursor = 0
        self.archiveCursor = 0
        self.echos = EchoModeStack(SelectorMode.ECHO,
                                   CFG.node().echoareas)
        drawMessageBox("Подождите", False)
        self.counts.getCounts(CFG.node(), True)
        self.scr.clear()
        self.updateScroll()

    def updateScroll(self):
        self.scroll = ScrollCalc(len(self.echos.data), self.h - 2)
        self.scroll.ensureVisible(self.echos.idx, center=True)
        self.counts.rescanCounts(self.echos.data)

    def toggleArchive(self):
        if not self.echos.isArch() and CFG.node().archive:
            self.echoCursor = self.echos.idx
            self.echos.modeArchOn(CFG.node().archive)
            self.echos.idx = self.archiveCursor
        elif self.echos.isArch():
            self.archiveCursor = self.echos.idx
            self.echos.modeArchOff()
            self.echos.idx = self.echoCursor
        self.scr.clear()
        self.updateScroll()

    # noinspection PyUnusedLocal
    @staticmethod
    def onSearchItem(sidx: int, pattern: re.Pattern, echo: config.Echo
                     ) -> Optional[List[List[re.Match]]]:
        if echo in (config.ECHO_OUT, config.ECHO_DRAFTS,
                    config.ECHO_CARBON, config.ECHO_FAVORITES):
            return None
        result = utils.quickSearch(pattern, echo.name)
        return [result] if result else None

    def show(self):
        while self.go:
            self.scroll.ensureVisible(self.echos.idx)
            self.draw(self.scr)
            #
            ks, key, _ = getKeystroke()
            #
            if key == curses.KEY_RESIZE:
                self.onResize()
            elif self.qs:
                if ks in Qs.CLOSE or ks in Qs.APPLY:
                    if ks in Qs.APPLY and self.qs.result:
                        self.echos.modeQsOn(self.qs.result)
                        self.updateScroll()
                    self.qs = None
                    curses.curs_set(0)
                else:
                    # noinspection PyTypeChecker
                    self.qs.onKeyPressedSearch(key, ks, self.scroll)
                    self.echos.idx = self.qs.ensureCursorVisible(
                        key, self.echos.idx, self.scroll)
            elif ks in Qs.OPEN:
                self.qs = newQuickSearch(self.echos.data, self.onSearchItem)
            elif ks in Reader.QUIT and self.echos.stack:
                self.echos.pop()
                self.updateScroll()
            elif ks in Common.QUIT:
                self.go = False
            else:
                self.onKeyPressed(ks, key)

    def draw(self, win):
        self.drawEchoSelector(win, self.scroll.pos, self.echos.idx,
                              self.qs, self.counts.counts)
        if self.scroll.isScrollable:
            drawScrollBarV(win, 1, self.w - 1, self.scroll)
        if self.qs:
            self.qs.draw(win)
        win.refresh()

    def drawEchoSelector(self, win, start, cursor, qs, counts):
        # type: (curses.window, int, int, QuickSearch, List[List[str]]) -> None
        color = getColor(UI_BORDER)
        win.addstr(0, 0, "─" * self.w, color)
        if self.echos.isArch():
            drawTitle(win, 0, 0, "Архив")
        else:
            drawTitle(win, 0, 0, "Конференция")
        #
        m = min(self.w - 38, max(map(lambda e: len(e.desc), self.echos.data)))
        count = "Сообщений"
        unread = "Не прочитано"
        description = "Описание"
        showDesc = (self.w >= 80) and m > 0
        if self.w < 80 or m == 0:
            m = len(unread) - 7
        drawTitle(win, 0, self.w + 2 - m - len(count) - len(unread) - 1, count)
        drawTitle(win, 0, self.w - 8 - m - 1, unread)
        if showDesc:
            drawTitle(win, 0, self.w - len(description) - 2, description)

        for y in range(1, self.h - 1):
            echoN = y - 1 + start
            if echoN == cursor:
                color = getColor(UI_CURSOR)
            else:
                color = getColor(UI_TEXT)
            win.addstr(y, 0, " " * self.w, color)
            if echoN >= len(self.echos.data):
                continue  #
            #
            win.attrset(color)
            echo = self.echos.data[echoN]
            total, unread = counts[echoN]
            if int(unread) > 0:
                win.addstr(y, 0, "+")
            win.addstr(y, 2, echo.title or echo.name)
            win.addstr(y, self.w - 10 - m - len(total), total)
            win.addstr(y, self.w - 2 - m - len(unread), unread)
            if showDesc:
                win.addstr(y, max(self.w - m - 1, self.w - 1 - len(echo.desc)),
                           echo.desc[0:self.w - 38])
            #
            if qs and echoN in qs.result:
                idx = qs.result.index(echoN)
                for match in qs.matches[idx]:
                    win.addstr(y, 2 + match.start(),
                               echo.name[match.start():match.end()],
                               color | curses.A_REVERSE)

        drawStatusBar(win, mode=self.echos.mode, text=CFG.node().nodename)

    def onKeyPressed(self, ks, key):
        if ks in Selector.UP:
            self.echos.idx = max(0, self.echos.idx - 1)
        elif ks in Selector.DOWN:
            self.echos.idx = min(self.scroll.content - 1, self.echos.idx + 1)
        elif ks in Selector.PPAGE:
            if self.echos.idx > self.scroll.pos:
                self.echos.idx = self.scroll.pos
            else:
                self.echos.idx = max(0, self.echos.idx - self.scroll.view)
        elif ks in Selector.NPAGE:
            pageBottom = self.scroll.posBottom()
            if self.echos.idx < pageBottom:
                self.echos.idx = pageBottom
            else:
                self.echos.idx = min(self.scroll.content - 1,
                                     pageBottom + self.scroll.view)
        elif ks in Selector.HOME:
            self.echos.idx = 0
        elif ks in Selector.END:
            self.echos.idx = self.scroll.content - 1
        elif ks in Selector.GET or ks in Selector.FGET:
            self.fetchMail(forceFullIdx=(ks in Selector.FGET))
        elif ks in Selector.ARCHIVE and len(CFG.node().archive) > 0:
            self.toggleArchive()
        elif ks in Selector.ENTER:
            self.readEcho(self.echos.curItem())
        elif ks in Selector.OUT:
            self.readEcho(config.ECHO_OUT)
        elif ks in Selector.DRAFTS:
            self.readEcho(config.ECHO_DRAFTS)
        elif ks in Selector.NNODE:
            CFG.nextNode()
            self.reloadEchoareas()
        elif ks in Selector.PNODE:
            CFG.prevNode()
            self.reloadEchoareas()
        elif ks in Selector.CONFIG:
            self.onEditCfg()
            self.reloadEchoareas()
        elif ks in Selector.FIND:
            win = FindQueryWindow(self.scr, cfg=CFG)
            findResult = win.show()
            if win.resized:
                self.onResize()
            if findResult:
                findResult = sorted(findResult, key=lambda m: m.time)
                self.showReader(EchoReaderScreen(
                    self.scr, config.ECHO_FIND, 0, True, self.counts,
                    mode=ReaderMode.FIND, msgids=findResult))

    def fetchMail(self, forceFullIdx):
        terminateCurses()
        os.system('cls' if os.name == 'nt' else 'clear')
        mailer.fetchMail(CFG.node(), forceFullIdx)
        initializeCurses()
        drawMessageBox("Подождите", False)
        self.counts.getCounts(CFG.node(), True)
        self.counts.rescanCounts(self.echos.data)
        self.scr.clear()
        self.echos.idx = self.counts.findNew(0)

    def readEcho(self, echo):
        drawMessageBox("Подождите", False)
        last = self.counts.getLast(echo)
        self.showReader(EchoReaderScreen(
            self.scr, echo, last, self.echos.isArch(), self.counts))
        #
        self.counts.rescanCounts(self.echos.data)
        if self.nextEcho and isinstance(self.nextEcho, bool):
            self.echos.idx = self.counts.findNew(self.echos.idx)
            self.nextEcho = False
        elif self.nextEcho and isinstance(self.nextEcho, str):
            node = CFG.node()
            if ((not self.echos.isArch() and self.nextEcho in node.archive)
                    or (self.echos.isArch() and (self.nextEcho in node.echoareas
                                                 or self.nextEcho in node.stat))):
                self.toggleArchive()
            # noinspection PyTypeChecker
            self.echos.idx = self.echos.findItemIdx(self.nextEcho)
            if self.echos.idx == -1:
                self.echos.idx = 0
            self.nextEcho = False

    def showReader(self, reader):
        self.go, self.nextEcho = reader.show()
        if reader.resized:
            self.onResize()

    def onResize(self):
        self.h, self.w = self.scr.getmaxyx()
        self.scroll = ScrollCalc(len(self.echos.data), self.h - 2,
                                 self.echos.idx)
        self.scr.clear()
        if self.qs:
            self.qs.y = self.h - 1
            self.qs.onResize(self.w - len(version) - 13)
# endregion EchoSelector
