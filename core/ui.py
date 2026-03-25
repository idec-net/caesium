import curses
import re
import textwrap
import time
import sys
from abc import ABC
from collections import deque
from datetime import datetime
from enum import Enum
from itertools import cycle
from typing import Optional, List, Tuple, TypeVar, Generic, Union

import api.ait as api
from api import MsgMetadata, FindQuery
from core import __version__, parser, utils, keystroke
from core.cmd import Common, Reader, Selector, Qs
from core.config import (
    get_color, load_colors, Config, TOKEN2UI, ECHO_FIND,
    UI_BORDER, UI_COMMENT, UI_CURSOR, UI_STATUS, UI_SCROLL, UI_TITLES, UI_TEXT, Echo
)
from core.layout import GridLayout, CC

LABEL_SEARCH = "<введите regex для поиска>"
LABEL_ANY_KEY = "Нажмите любую клавишу"
LABEL_ESC = "Esc - отмена"
LABEL_FIND = "Поиск "  # extra space for wide unicode icon (use wcwidth)
HEIGHT = 0
WIDTH = 0

stdscr = None  # type: Optional[curses.window]
version = "Caesium/%s │" % __version__


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


def load_theme(cfg: Config):
    try:
        load_colors(cfg.themeColors)
    except ValueError as err:
        load_colors("default")
        stdscr.refresh()
        show_message_box("Цветовая схема %s не установлена.\n"
                         "%s\n"
                         "Будет использована схема по-умолчанию."
                         % (cfg.themeColors, str(err)))
    #
    global THEME
    THEME = ThemeAscii
    if cfg.themeWidgets in THEMES:
        THEME = THEMES[cfg.themeWidgets]
    elif cfg.themeWidgets:
        show_message_box("Неизвестная схема виджетов %s\n"
                         "Будет использована схема по-умолчанию."
                         % cfg.themeWidgets)


class ReaderMode(Enum):
    ECHO = 'E'  # Regular mode reading whole echo conference
    SUBJ = 'S'  # Specified subject and answers (Re: )
    SEARCH = 'Q'  # Quick Search results on MsgListScreen
    FIND = 'F'  # Find results


class SelectorMode(Enum):
    ECHO = 'E'  # Regular mode w Node echoareas
    ARCH = 'A'  # Archives mode w Node archived echoareas
    SEARCH = 'Q'  # Quick Search results


def set_term_size():
    global HEIGHT, WIDTH, stdscr
    HEIGHT, WIDTH = stdscr.getmaxyx()


def initialize_curses():
    global stdscr
    stdscr = curses.initscr()
    curses.start_color()
    curses.use_default_colors()
    curses.noecho()
    curses.set_escdelay(50)  # ms
    curses.curs_set(0)
    curses.raw()
    stdscr.keypad(True)
    set_term_size()


def terminate_curses():
    curses.curs_set(1)
    if stdscr:
        stdscr.keypad(False)
    curses.echo(True)
    curses.noraw()
    curses.endwin()


def get_keystroke(timeout=-1):
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


def draw_splash(scr, splash):  # type: (curses.window, List[str]) -> None
    scr.clear()
    h, w = scr.getmaxyx()
    x = int((w - len(splash[1])) / 2) - 1
    y = int((h - len(splash)) / 2)
    color = get_color(UI_TEXT)
    for i, line in enumerate(splash):
        scr.addstr(y + i, x, line, color)
    scr.refresh()


def draw_title(scr, y, x, title):
    h, w = scr.getmaxyx()
    x = max(0, x)
    borders = len(THEME.title[0]) + len(THEME.title[1])
    if (x + len(title) + borders) > w:
        title = title[:w - x - borders - len(THEME.ellipsis)] + THEME.ellipsis
    #
    border = get_color(UI_BORDER)
    if THEME.title[0]:
        scr.addstr(y, x, THEME.title[0], border)
    color = get_color(UI_TITLES)
    scr.addstr(y, x + len(THEME.title[0]), title, color)
    if THEME.title[1]:
        scr.addstr(y, x + len(THEME.title[0]) + len(title), THEME.title[1], border)


def draw_message_box(smsg, wait):
    msg = smsg.split("\n")
    if wait:
        msg.extend(LABEL_ANY_KEY)
    max_width = int(WIDTH * 0.75) if WIDTH > 80 else WIDTH - 2
    max_width = min(max_width, max(map(lambda x: len(x), msg))) + 2
    msg = list(map(lambda p: textwrap.fill(p, max_width - 2),
                   smsg.split("\n")))
    msg = "\n".join(msg).split("\n")  # re-split after textwrap.fill added \n
    box_height = len(msg) + 2  # len + border
    if wait:
        box_height += 2  # + new line + LABEL_ANY_KEY
    win = curses.newwin(box_height, max_width,
                        int((HEIGHT - box_height) / 2),
                        int((WIDTH - max_width) / 2))
    win.bkgd(' ', get_color(UI_TEXT))
    win.attrset(get_color(UI_BORDER))
    win.border()

    color = get_color(UI_TEXT)
    for i, line in enumerate(msg, start=1):
        if i >= HEIGHT - 1:
            break
        win.addstr(i, 1, line, color)

    color = get_color(UI_TITLES)
    if wait:
        win.addstr(len(msg) + 2, int((max_width - len(LABEL_ANY_KEY)) / 2),
                   LABEL_ANY_KEY, color)
    win.refresh()


def show_message_box(smsg):
    draw_message_box(smsg, True)
    stdscr.getch()
    stdscr.clear()


def draw_scrollbarV(scr, y, x, scroll):
    # type: (curses.window, int, int, ScrollCalc) -> None
    color = get_color(UI_SCROLL)
    for i in range(y, y + scroll.track):
        scr.addstr(i, x, "░", color)
    for i in range(y + scroll.thumb_pos, y + scroll.thumb_pos + scroll.thumb_sz):
        scr.addstr(i, x, "█", color)


def draw_status_bar(scr, mode=None, text=None):
    # type: (curses.window, Union[ReaderMode, SelectorMode], str) -> None
    h, w = scr.getmaxyx()
    color = get_color(UI_STATUS)
    scr.insstr(h - 1, 0, " " * w, color)
    scr.addstr(h - 1, 1, version, color)
    scr.addstr(h - 1, w - 8, "│ " + datetime.now().strftime("%H:%M"), color)
    if text:
        scr.addstr(h - 1, len(version) + 2, text, color)
    if parser.INLINE_STYLE_ENABLED:
        scr.addstr(h - 1, w - 10, "~", color)
    if mode:
        scr.addstr(h - 1, w - 11, mode.value, color)


def draw_reader(scr, echo: str, msgid, out):
    h, w = scr.getmaxyx()
    color = get_color(UI_BORDER)
    scr.addstr(0, 0, "─" * w, color)
    scr.addstr(4, 0, "─" * w, color)
    if out:
        draw_title(scr, 0, 0, echo)
        if msgid.endswith(".out"):
            ns = "не отправлено"
            draw_title(scr, 4, w - len(ns) - 2, ns)
    else:
        if w >= 80:
            draw_title(scr, 0, 0, echo + " / " + msgid)
        else:
            draw_title(scr, 0, 0, echo)
    for i in range(1, 4):
        scr.addstr(i, 0, " " * w, 1)
    color = get_color(UI_TITLES)
    scr.addstr(1, 1, "От:   ", color)
    scr.addstr(2, 1, "Кому: ", color)
    scr.addstr(3, 1, "Тема: ", color)


class ScrollCalc:
    content: int  # scrollable content length
    view: int  # scroll view length
    thumb_sz: int  # thumb size
    track: int  # track length
    _pos: int = 0  # scroll position in the scrollable content
    #
    thumb_pos: int  # calculated thumb position on the track
    is_scrollable = False

    def __init__(self, content: int, view: int,
                 pos: int = 0, track: int = None):
        self.content = content
        self.view = view
        self.thumb_sz = max(1, min(self.view, int(self.view * self.view
                                                  / max(1, content) + 0.5)))
        self.track = track or view
        self.is_scrollable = self.content > self.view
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

    def pos_bottom(self):
        return max(0, min(self.pos + self.view, self.content) - 1)

    def calc(self):
        available_track = self.track - self.thumb_sz
        thumb_pos = 0
        if self.is_scrollable:
            thumb_pos = int((self.pos / (self.content - self.view))
                            * available_track + 0.5)
        self.thumb_pos = max(0, min(available_track, thumb_pos))

    def ensure_visible(self, pos, center=False):
        if pos < self.pos:
            self.pos = pos  # scroll up
            if center:
                self.pos -= self.view // 2
        elif pos >= self.pos + self.view:
            self.pos = pos - self.view + 1  # scroll down
            if center:
                self.pos += self.view // 2

    # region search.Pager implementation
    def next_page_top(self):
        return self.pos + self.view

    def prev_page_bottom(self):
        return self.pos - 1
    # endregion implementation


class SelectWindow:
    scroll: ScrollCalc

    def __init__(self, title, items):
        self.title = title
        self.items = items
        self.cursor = 0
        self.win = self.init_win(self.items, self.title)
        self.resized = False

    def init_win(self, items, title, win=None):
        test_width = items + [LABEL_ESC + THEME.title[0] + THEME.title[1],
                              title + THEME.title[0] + THEME.title[1]]
        w = 0 if not items else max(map(lambda it: len(it), test_width))
        h = min(HEIGHT - 2, len(items))
        w = min(WIDTH - 2, w)
        y = max(0, int(HEIGHT / 2 - h / 2 - 1))
        x = max(0, int(WIDTH / 2 - w / 2 - 1))
        if win:
            win.resize(h + 2, w + 2)
            win.mvwin(y, x)
        else:
            win = curses.newwin(h + 2, w + 2, y, x)
        color = get_color(UI_BORDER)
        lbl_title = title[0:min(w - 2, len(title))]
        lbl_esc = LABEL_ESC[0:min(w - 2, len(LABEL_ESC))]
        win.attrset(color)
        win.border()
        win.addstr(0, 1, THEME.title[0], color)
        win.addstr(0, 2 + len(lbl_title), THEME.title[1], color)
        win.addstr(h + 1, 1, THEME.title[0], color)
        win.addstr(h + 1, 2 + len(lbl_esc), THEME.title[1], color)

        color = get_color(UI_TITLES)
        win.addstr(0, 2, lbl_title, color)
        win.addstr(h + 1, 2, lbl_esc, color)
        self.scroll = ScrollCalc(len(items), h)
        return win

    def show(self):
        while True:
            self.draw(self.win, self.items, self.cursor, self.scroll)
            self.win.refresh()
            #
            ks, key, _ = get_keystroke()
            #
            if key == curses.KEY_RESIZE:
                set_term_size()
                stdscr.clear()
                stdscr.refresh()
                self.win = self.init_win(self.items, self.title, self.win)
                self.resized = True
            elif ks in Selector.ENTER:
                return self.cursor + 1  # return 1-based index
            elif ks in Reader.QUIT:
                return False  #
            else:
                self.on_key_pressed(ks, self.scroll)

    @staticmethod
    def draw(win, items, cursor, scroll):
        h, w = win.getmaxyx()
        if h < 3 or w < 5:
            if h > 0 and w > 0:
                win.insstr(0, 0, "#" * w)
            return  # no space to draw
        #
        scroll.ensure_visible(cursor)
        for i, item in enumerate(items[scroll.pos:scroll.pos + h - 2]):
            color = get_color(UI_TEXT if i + scroll.pos != cursor else
                              UI_CURSOR)
            win.addstr(i + 1, 1, " " * (w - 2), color)
            win.addstr(i + 1, 1, item[:w - 2], color)

        if scroll.is_scrollable:
            draw_scrollbarV(win, 1, w - 1, scroll)

    def on_key_pressed(self, ks, scroll):  # type: (str, ScrollCalc) -> None
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
            page_bottom = scroll.pos_bottom()
            if self.cursor < page_bottom:
                self.cursor = page_bottom
            else:
                self.cursor = min(scroll.content - 1, page_bottom + scroll.view)


T = TypeVar('T')
V = TypeVar('V')


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


class MsgListScreen:
    msgs: MsgModeStack = None
    scroll: ScrollCalc = None

    def __init__(self, echo: str, msgs: MsgModeStack):
        self.echo = echo
        self.msgs = msgs
        self.scroll = ScrollCalc(len(msgs.data), HEIGHT - 2)
        self.scroll.ensure_visible(msgs.idx, center=True)
        self.resized = False
        self.qs = None  # type: Optional[QuickSearch]

    def show(self):  # type: () -> int
        stdscr.clear()
        self.draw_title(stdscr, self.echo)
        while True:
            self.scroll.ensure_visible(self.msgs.idx)
            self.draw(stdscr, self.msgs.data, self.msgs.idx, self.scroll)
            if self.qs:
                self.qs.draw(stdscr)
            #
            ks, key, _ = get_keystroke()
            #
            if key == curses.KEY_RESIZE:
                set_term_size()
                self.scroll = ScrollCalc(len(self.msgs.data), HEIGHT - 2)
                self.resized = True
                if self.qs:
                    self.qs.y = HEIGHT - 1
                    self.qs.width = WIDTH - len(version) - 12
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
                    self.qs.on_key_pressed_search(key, ks, self.scroll)
                    self.msgs.idx = self.qs.ensure_cursor_visible(
                        ks, self.msgs.idx, self.scroll)
            elif ks in Qs.OPEN:
                self.qs = newQuickSearch(self.msgs.data, self.on_search_item)
            elif ks in Selector.ENTER and self.msgs.data:
                return self.msgs.idx  #
            elif ks in Reader.QUIT:
                if not self.msgs.stack:
                    return -1  #
                self.msgs.pop()
                self.updateScroll()
            else:
                self.on_key_pressed(ks, self.scroll)

    @staticmethod
    def draw_title(win, echo):
        _, w = win.getmaxyx()
        color = get_color(UI_BORDER)
        win.addstr(0, 0, "─" * w, color)
        if echo == ECHO_FIND:
            if w >= 80:
                draw_title(win, 0, 0, f"Найденные сообщения"
                                      f" '{FindQueryWindow.query}'")
            else:
                draw_title(win, 0, 0, f"'{FindQueryWindow.query}'")
        else:
            if w >= 80:
                draw_title(win, 0, 0, "Список сообщений в конференции " + echo)
            else:
                draw_title(win, 0, 0, echo)

    def draw(self, win, data, cursor, scroll):
        # type: (curses.window, List[MsgMetadata], int, ScrollCalc) -> None
        h, w = win.getmaxyx()
        for i in range(1, h - 1):
            color = get_color(UI_TEXT if scroll.pos + i - 1 != cursor else
                              UI_CURSOR)
            win.addstr(i, 0, " " * w, color)
            pos = scroll.pos + i - 1
            if pos >= scroll.content:
                continue  #
            #
            msg = data[pos]
            win.addstr(i, 0, msg.fr, color)
            win.addstr(i, 16, msg.subj[:w - 27], color)
            win.addstr(i, w - 11, msg.strtime(), color)
            #
            if self.qs and pos in self.qs.result:
                idx = self.qs.result.index(pos)
                m_name, m_subj = self.qs.matches[idx]  # type: List[re.Match], List[re.Match]
                for m in m_name:
                    win.addstr(i, 0 + m.start(), msg.fr[m.start():m.end()],
                               color | curses.A_REVERSE)
                for m in m_subj:
                    end = min(w - 27, m.end())
                    if m.start() + 16 > w - 12:
                        continue
                    win.addstr(i, 16 + m.start(), msg.subj[m.start():end],
                               color | curses.A_REVERSE)
        #
        if scroll.is_scrollable:
            draw_scrollbarV(win, 1, w - 1, scroll)
        draw_status_bar(win, mode=self.msgs.mode,
                        text=utils.msgn_status(len(data), cursor, w))

    def updateScroll(self):
        self.scroll = ScrollCalc(len(self.msgs.data), HEIGHT - 2)
        self.scroll.ensure_visible(self.msgs.idx, center=True)

    def on_key_pressed(self, ks, scroll):
        if ks in Reader.MSUBJ:
            if self.msgs.mode != ReaderMode.SUBJ:
                m = self.msgs.curItem()
                data = api.find_subj_msgids(m.echo, m.subj)
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
            page_bottom = scroll.pos_bottom()
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
    def on_search_item(sidx, pattern, it):
        # type: (int, re.Pattern, MsgMetadata) -> Optional[List[Tuple[List[re.Match], List[re.Match]]]]
        result_name = []
        result_subj = []
        p = 0
        while match := pattern.search(it.fr, p):
            if p >= len(it.fr) or match.start() == match.end():
                break
            result_name.append(match)
            p = match.end()
        p = 0
        while match := pattern.search(it.subj, p):
            if p >= len(it.subj) or match.start() == match.end():
                break
            result_subj.append(match)
            p = match.end()
        if result_name or result_subj:
            return [(result_name, result_subj)]
        return None


class Widget:
    focused: bool = False
    enabled: bool = True
    focusable: bool = True
    focusOrder: int = 0
    x: int = 0
    y: int = 0
    w: int = 0
    h: int = 0

    def right(self):
        return self.x + self.w

    def set_focused(self, focused):
        pass

    def on_key_pressed(self, ks, key):
        pass

    def draw(self, win):  # type: (curses.window) -> None
        pass


class SeparatorHWidget(Widget):
    focusable: bool = False
    h: int = 1

    def __init__(self, y=0, x=0, color: str = UI_COMMENT):
        self.x = x
        self.y = y
        if color:
            self.color = get_color(color)

    def draw(self, win):  # type: (curses.window) -> None
        win.addstr(self.y, self.x, "─" * self.w, self.color)


class LabelWidget(Widget):
    focusable: bool = False
    h: int = 1

    def __init__(self, txt="", y=0, x=0, enabled=True, color: str = None):
        self.x = x
        self.y = y
        self.w = len(txt)
        self.txt = txt
        self.enabled = enabled
        if color:
            self.color = get_color(color)
        else:
            self.color = self._color(self.enabled)

    # noinspection PyUnusedLocal
    @staticmethod
    def _color(enabled):
        if enabled:
            return get_color(UI_TEXT)
        return get_color(UI_COMMENT)

    def set_enabled(self, enabled):
        if self.enabled == enabled:
            return
        self.enabled = enabled
        self.color = self._color(enabled)

    def set_txt(self, txt):
        self.txt = txt
        self.w = len(txt)

    def draw(self, win):  # type: (curses.window) -> None
        _, width = win.getmaxyx()
        w = min(width - self.x - 1, self.w)
        if w > 0:  # android termux curses v6.5.20240832 crashes on addnstr w zero width
            win.addstr(self.y, self.x, " " * w, self.color)
            win.addnstr(self.y, self.x, self.txt, w, self.color)


class CheckBoxWidget(Widget):
    h: int = 1

    def __init__(self, lbl="", fOrder=0, y=0, x=0, checked=False, enabled=True):
        self.focusOrder = fOrder
        self.x = x
        self.y = y
        self.lbl = lbl
        self.checked = checked
        self.enabled = enabled
        self.content = self._content(checked, lbl)
        self.color = self._color(self.focused, enabled)
        self.w = len(self.content)

    @staticmethod
    def _content(checked, lbl):
        return "%s%s" % (THEME.checkbox[1 if checked else 0], lbl)

    @staticmethod
    def _color(focused, enabled):
        if enabled:
            return get_color(UI_TITLES if focused else UI_TEXT)
        return get_color(UI_COMMENT) | curses.A_ITALIC

    def set_checked(self, checked):
        if self.checked == checked:
            return
        self.checked = checked
        self.content = self._content(checked, self.lbl)

    def set_focused(self, focused):
        if self.focused == focused:
            return
        self.focused = focused
        self.color = self._color(focused, self.enabled)

    def set_enabled(self, enabled):
        if self.enabled == enabled:
            return
        self.enabled = enabled
        self.color = self._color(self.focused, enabled)

    def draw(self, win):
        if self.w > 0:
            win.addnstr(self.y, self.x, self.content, self.w, self.color)

    def on_key_pressed(self, ks, key):
        if key == ord(" "):
            self.set_checked(not self.checked)


class InputWidget(Widget):
    cursor: int = 0
    offset: int = 0
    h: int = 1

    def __init__(self, txt="", fOrder=0, y=0, x=0, w=0, *, placeholder="", mask=None):
        self.focusOrder = fOrder
        self.x = x
        self.y = y
        self.w = w
        self.txt = txt
        self.placeholder = placeholder
        self.mask = mask
        self.color = self._color(self.focused, self.enabled)

    # noinspection PyUnusedLocal
    @staticmethod
    def _color(focused, enabled):
        if enabled:
            return get_color(UI_CURSOR)
        return get_color(UI_TEXT)

    def set_focused(self, focused):
        if self.focused == focused:
            return
        self.focused = focused
        self.color = self._color(focused, self.enabled)

    def set_enabled(self, enabled):
        if self.enabled == enabled:
            return
        self.enabled = enabled
        self.color = self._color(self.focused, enabled)

    def draw(self, win):  # type: (curses.window) -> None
        if self.w <= 0:
            return
        left = THEME.input[0]
        right = THEME.input[1]
        attr = self.color | THEME.input[2]
        #
        if self.txt:
            txt = self.txt
        else:
            txt = self.placeholder
            attr |= curses.A_ITALIC
        #
        win.addstr(self.y, self.x, " " * self.w, attr)
        if left:
            win.addnstr(self.y, self.x, left, self.w, self.color)
        win.addnstr(self.y, self.x + len(left), txt[self.offset:],
                    self.w - len(left), attr)
        if right:
            win.addstr(self.y, self.x + self.w - len(right), right, self.color)

    def _move_cursor_right(self, increment):
        self.cursor = min(len(self.txt), self.cursor + increment)
        contentWidth = self.w - (len(THEME.input[0]) + len(THEME.input[1]))
        if self.cursor - self.offset > contentWidth - 1:
            self.offset += increment

    def _move_cursor_left(self, decrement):
        self.cursor = max(0, self.cursor - decrement)
        if self.cursor - self.offset < 0:
            self.offset -= decrement
        if self.offset and self.offset == self.cursor:
            self.offset -= 1

    def on_key_pressed(self, ks, key):
        # TODO: Common navigation commands?
        if key == curses.KEY_HOME:
            self.cursor = 0
            self.offset = 0
        elif key == curses.KEY_END:
            self.cursor = len(self.txt)
            contentWidth = self.w - (len(THEME.input[0]) + len(THEME.input[1]))
            self.offset = max(0, self.cursor - contentWidth + 1)
        elif key == curses.KEY_LEFT:
            self._move_cursor_left(1)
        elif key == curses.KEY_RIGHT:
            self._move_cursor_right(1)
        elif key in (curses.KEY_BACKSPACE, 127):
            # 127 - Ctrl+? - Android backspace
            txt = self.txt[0:max(0, self.cursor - 1)] + self.txt[self.cursor:]
            if not self.mask or self.mask.match(txt):
                self.txt = txt
                self._move_cursor_left(1)
        elif key == curses.KEY_DC:  # DEL
            txt = self.txt[0:max(0, self.cursor)] + self.txt[self.cursor + 1:]
            if not self.mask or self.mask.match(txt):
                self.txt = txt
        else:
            if key == ord(" "):
                ks = " "
            if len(ks) == 3 and ks.startswith("S-"):
                ks = ks[-1].upper()
            if len(ks) == 1:
                txt = self.txt[0:self.cursor] + ks + self.txt[self.cursor:]
                if not self.mask or self.mask.match(txt):
                    self.txt = txt
                    self._move_cursor_right(len(ks))

    def get_win_cursor_pos(self):
        return len(THEME.input[0]) + self.cursor - self.offset


class InputRegexWidget(InputWidget):
    regexOn: bool = True
    err: bool = False

    def __init__(self, txt="", fOrder=0, y=0, x=0, w=0,
                 *, placeholder="", regexOn=False):
        super().__init__(txt=txt, fOrder=fOrder, y=y, x=x, w=w,
                         placeholder=placeholder)
        self.x = x
        self.y = y
        self.w = w
        self.txt = txt
        self.placeholder = placeholder
        self.color = self._color(self.focused, self.enabled)
        self.regexOn = regexOn
        self.template = self._compile_regex()

    def _compile_regex(self):
        template = None
        try:
            if self.regexOn:
                template = re.compile(self.txt, re.IGNORECASE)
            self.err = False
        except re.error:
            self.err = True
        return template

    def on_key_pressed(self, ks, key):
        super().on_key_pressed(ks, key)
        self.template = self._compile_regex()

    def set_regexOn(self, regex):
        self.regexOn = regex
        self.template = self._compile_regex()

    def draw(self, win):  # type: (curses.window) -> None
        super().draw(win)
        if self.w > 3 and self.err:
            err = THEME.error[0]
            err_len = len(err) + len(THEME.input[1]) + 1
            win.addstr(self.y, self.x + self.w - err_len,
                       err, self.color | THEME.error[1])


class FindQueryWindow:
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

    def __init__(self, cfg: Config):
        self.cfg = cfg
        self.findProgressBar = cycle(THEME.spinner)
        self.win = self.initWin()
        h, w = self.win.getmaxyx()
        #
        self.inpQuery = InputRegexWidget(
            self.query.query, 1,
            placeholder="<введите текст для поиска>",
            regexOn=self.query.regex)
        self.inpQueryNot = InputRegexWidget(
            self.query.queryNot, 2,
            placeholder="<введите текст для исключения>",
            regexOn=self.query.regex)

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

        self.layout = GridLayout(
            (GridLayout(
                (LabelWidget("Искать: "), ""),
                (self.inpQuery, "fillX growX wrap"),

                (LabelWidget("И НЕ: "), "hAlign right"),
                (self.inpQueryNot, "fillX growX wrap"),
            ), "w 100% h 2 fillX growX wrap"),
            (LabelWidget("В:"), "wrap"),
            #
            (GridLayout(
                (self.chkMsgid, "w 50% wrap"),
                (SeparatorHWidget(), "colSpan 2 fillX wrap"),
                (self.chkBody, "w 50%"), (self.chkRegex, "wrap"),
                (self.chkSubj, "w 50%"), (self.chkCase, "wrap"),
                (self.chkFrom, "w 50%"), (self.chkWord, "wrap"),
                (self.chkTo, "growY"), (self.chkOrig, "wrap"),
                (SeparatorHWidget(), "colSpan 2 fillX wrap"),
            ), "pad 1 0 w 100% h 7 fillX wrap"),
            #
            (GridLayout((self.chkEcho, CC(w=self.chkEcho.w + 2, pad="1 0")),
                        (self.inpEcho, "fillX wrap"),

                        (LabelWidget("И НЕ: "), "hAlign right"),
                        (self.inpEchoNot, "fillX wrap")),
             "w 100% h 2 fillX wrap"),
            (GridLayout(
                (self.chkSkipArch, "pad 1 0 w 50%"),
                (LabelWidget("Лимит: "), ""),
                (self.inpLimit, CC(wPref=(7 + len(THEME.input[0])
                                          + len(THEME.input[1])),
                                   hAlign="left",
                                   growX=True))
            ), "h 1 w 100% fillX wrap"),
            #
            (self.lblProgress, "w 100% fill growY wrap"),
        )
        self.layout.pack(offset_x=2, offset_y=1, width=w - 4, height=h - 2)
        self.widgets = deque(sorted(list(self.layout.collect_widgets()),
                                    key=lambda _: _.focusOrder))
        #
        self.setFocused(self.inpQuery)
        self.updateState()

    def setFocused(self, focusWid):  # type: (Optional[Widget]) -> None
        if self.focusedWid == focusWid:
            return
        if self.focusedWid:
            self.focusedWid.set_focused(False)
        self.focusedWid = focusWid
        if self.focusedWid:
            self.focusedWid.set_focused(True)

    @staticmethod
    def initWin(win=None):
        w = max(len(LABEL_FIND) + 2, min(80, int(WIDTH * 0.75)))
        h = min(HEIGHT, 16)
        w = min(WIDTH, w)
        y = max(0, int((HEIGHT - h) / 2))
        x = max(0, int((WIDTH - w) / 2))
        if win:
            win.resize(h, w)
            win.mvwin(y, x)
        else:
            win = curses.newwin(h, w, y, x)
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
            ks, key, _ = get_keystroke(0)
        else:
            ks, key, _ = get_keystroke()
        self.go = self.onKeyPressed(ks, key)

    @staticmethod
    def drawTitle(win):  # type: (curses.window) -> None
        h, w = win.getmaxyx()
        win.bkgd(" ", get_color(UI_TEXT))
        #
        border = get_color(UI_BORDER)
        win.attrset(border)
        win.border()

        x = (w - len(THEME.findIcon) - len(LABEL_FIND)) // 2 - 1
        draw_title(win, 0, x, THEME.findIcon + LABEL_FIND)

    def drawContent(self, win):  # type: (curses.window) -> None
        h, w = win.getmaxyx()
        win.addstr(self.lblProgress.y, 1, " " * (w - 2))  # lbl_progress
        if w > 20 and h > 10:
            for w in self.widgets:
                w.draw(win)
        else:
            lines = textwrap.wrap("Маленькое окошко!", w - 2)
            for y, line in enumerate(lines):
                win.addstr(1 + y, 1, line + (" " * (w - 2 - len(line))))

    def onKeyPressed(self, ks, key):
        if key == curses.KEY_RESIZE:
            set_term_size()
            stdscr.clear()
            stdscr.refresh()
            self.win = self.initWin(self.win)
            self.win.clear()
            h, w = self.win.getmaxyx()
            self.layout.pack(offset_x=2, offset_y=1, width=w - 4, height=h - 2)
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
            if self.inpQuery.regexOn and self.inpQuery.err:
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
            if ks == "Tab" or key == curses.KEY_DOWN:
                wid = self.nextFocus(self.focusedWid)
                while wid and not (wid.enabled and wid.focusable):
                    wid = self.nextFocus(wid)
                self.setFocused(wid)

            elif ks == "S-Tab" or key == curses.KEY_UP:
                wid = self.prevFocus(self.focusedWid)
                while wid and not (wid.enabled and wid.focusable):
                    wid = self.prevFocus(wid)
                self.setFocused(wid)

            elif self.focusedWid:
                self.focusedWid.on_key_pressed(ks, key)
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
        self.inpEcho.set_enabled(self.chkEcho.checked)
        self.inpEchoNot.set_enabled(self.chkEcho.checked)
        self.chkWord.set_enabled(not self.chkRegex.checked)
        self.inpQuery.set_regexOn(self.chkRegex.checked)
        self.inpQueryNot.set_regexOn(self.chkRegex.checked)

        self.query.query = self.inpQuery.txt
        self.query.queryNot = self.inpQueryNot.txt
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
            self.lblProgress.set_txt("")
        else:
            self.lblProgress.set_txt("Ничего не найдено")
        self.refreshCursor()

    def refreshCursor(self):
        if isinstance(self.focusedWid, InputWidget):
            y, x = self.win.getbegyx()
            inp_cursor_x = self.focusedWid.get_win_cursor_pos()
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

        self.findResult = api.find_query_msgids(
            self.query, progress_handler=self.findProgressHandler)
        self.findInProgress = False

    def findProgressHandler(self, param=None):
        now = time.time()
        self._keys()
        if self.findCancel:
            return api.FIND_CANCEL
        if (now - self.findTick) < 0.250:  # ms
            return api.FIND_OK
        self.findTick = now
        progress = " Поиск... " + next(self.findProgressBar)
        if param:
            progress += (f" Found: {param[5]}"
                         f" TMsg: {param[4]}"
                         f" E: {param[0]}/{param[1]}"
                         f" EMsg: {param[2]}/{param[3]}")
        self.lblProgress.set_txt(progress)
        self._show()
        return api.FIND_OK


class Pager:
    pos: int = 0

    def __init__(self, pos, next_page_top, prev_page_bottom):
        self.pos = pos
        self.next_page_top = next_page_top
        self.prev_page_bottom = prev_page_bottom

    def next_page_top(self):
        pass

    def prev_page_bottom(self):
        pass


def newQuickSearch(items, matcher):
    stdscr.move(HEIGHT - 1, len(version) + 2)
    curses.curs_set(1)
    return QuickSearch(items, matcher,
                       y=HEIGHT - 1, x=len(version) + 2,
                       w=WIDTH - len(version) - 13)


class QuickSearch(InputRegexWidget):
    def __init__(self, items, matcher,
                 y=0, x=0, w=0, *, placeholder=LABEL_SEARCH, color=UI_STATUS):
        super().__init__(y=y, x=x, w=w, placeholder=placeholder, regexOn=True)
        self.items = items
        self.matches = []
        self.result = []
        self.idx = 0
        self.matcher = matcher
        self.color = get_color(color)
        self.statTxt = ""
        self.statPos = 0

    def draw(self, win):
        # type: (curses.window) -> None
        super().draw(win)
        if self.txt and not self.err:
            win.addstr(self.y, self.x + self.statPos, self.statTxt, self.color)
        win.move(self.y, self.x + self.get_win_cursor_pos())

    def search(self, query, pos):
        self.result = []
        self.matches = []
        self.idx = -1

        if self.txt != query:
            self.txt = query
            self.template = self._compile_regex()
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

    def on_key_pressed_search(self, key, ks, pager):
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
            self.next_after(pager.next_page_top())
        elif ks in Qs.PPAGE:
            self.prev_before(pager.prev_page_bottom())
        elif ks in Qs.LEFT:
            self._move_cursor_left(1)
        elif ks in Qs.RIGHT:
            self._move_cursor_right(1)
        else:
            super().on_key_pressed(ks, key)

        if self.txt != prevTxt:
            self.search(self.txt, pager.pos)

        if self.txt and not self.err:
            idx = self.idx + 1 if self.result else 0
            self.statTxt = "(%d/%d)" % (idx, len(self.result))
            self.statPos = self.w - len(self.statTxt) - len(THEME.input[1])
            if self.get_win_cursor_pos() + 1 >= self.statPos:
                self.offset += self.get_win_cursor_pos() + 1 - self.statPos
        elif self.err:
            errPos = self.w - len(THEME.error[0]) - len(THEME.input[1]) - 1  #
            if self.get_win_cursor_pos() + 1 >= errPos:
                self.offset += self.get_win_cursor_pos() + 1 - errPos

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

    def next_after(self, pos):
        if not self.result:
            return  #
        while self.result[self.idx] < pos:
            self.idx += 1
            if self.idx >= len(self.result):
                self.end()
                break  #

    def prev_before(self, pos):
        if not self.result:
            return  #
        while self.result[self.idx] > pos:
            self.idx -= 1
            if self.idx < 0:
                self.home()
                break  #

    def ensure_cursor_visible(self, ks, cursor, scroll):
        if self.result:
            cursor = self.result[self.idx]
            if ks in Qs.NPAGE:
                scroll.pos = cursor
            elif ks in Qs.PPAGE:
                scroll.pos = cursor - scroll.view
            scroll.ensure_visible(cursor)
        return cursor


class ReaderWidget(Widget):
    tokens: List[parser.Token]  # message bode tokens
    scroll: ScrollCalc  # message body scroll calculator
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
        height = parser.prerender(self.tokens, self.w, self.h)
        self.t2l = parser.token_line_map(self.tokens)
        self.scroll = ScrollCalc(height, self.h, pos)

    def draw(self, scr, qs=None):
        self.render_body(scr, self.tokens, self.scroll.pos, qs)
        if self.scroll.is_scrollable:
            draw_scrollbarV(scr, self.y, self.x + self.w - 1, self.scroll)

    def render_body(self, scr, tokens, scroll, qs=None):
        # type: (curses.window, List[parser.Token], int, QuickSearch) -> None
        if not tokens:
            return
        tnum, offset = parser.find_visible_token(tokens, scroll)
        line_num = tokens[tnum].line_num
        y, x = (self.y, self.x)
        h, w = (self.y + self.h, self.x + self.w)
        text_attr = 0
        if parser.INLINE_STYLE_ENABLED:
            # Rewind tokens from the begin of line to apply inline text attributes
            first_token = tnum
            while tokens[first_token].line_num == line_num and first_token > 0:
                first_token -= 1
            for token in tokens[first_token:tnum]:
                text_attr = ReaderWidget.applyAttr(token, text_attr)

        for token in tokens[tnum:]:
            if token.line_num > line_num:
                line_num = token.line_num
                y, x = (y + 1, self.x)
            if y >= h:
                break  # tokens
            #
            text_attr = ReaderWidget.applyAttr(token, text_attr)
            #
            y, x = self.renderToken(scr, token, y, x, h, offset, text_attr, qs)
            offset = 0  # required in the first partial multiline token only

    @staticmethod
    def applyAttr(token, text_attr):
        if token.type == parser.TT.URL:
            text_attr |= curses.A_UNDERLINE
        else:
            text_attr &= ~curses.A_UNDERLINE

        if token.type == parser.TT.ITALIC_BEGIN:
            text_attr |= curses.A_ITALIC
        elif token.type == parser.TT.ITALIC_END:
            text_attr &= ~curses.A_ITALIC

        elif token.type == parser.TT.BOLD_BEGIN:
            text_attr |= curses.A_BOLD
        elif token.type == parser.TT.BOLD_END:
            text_attr &= ~curses.A_BOLD
        return text_attr

    def renderToken(self, scr, token: parser.Token, y, x, h, offset, text_attr, qs=None):
        matches = []
        # noinspection PyUnresolvedReferences
        if (qs and qs.result
                and hasattr(token, 'search_idx')
                and token.search_idx is not None):
            # noinspection PyUnresolvedReferences
            matches = token.search_matches
        #
        for i, line in enumerate(token.render[offset:]):
            if y + i >= h:
                return y + i, x  #
            attr = get_color(TOKEN2UI.get(token.type, UI_TEXT))
            if line:
                scr.addstr(y + i, x, line, attr | text_attr)
                #
                for m_idx, (off, match) in enumerate(matches):
                    if off == offset + i:
                        scr.addstr(y + i, x + match.start(),
                                   line[match.start():match.end()],
                                   attr | text_attr | curses.A_REVERSE)

            if len(token.render) > 1 and i + offset < len(token.render) - 1:
                x = self.x  # new line in multiline token -- carriage return
            else:
                x += len(line)  # last/single line -- move caret in line
        return y + (len(token.render) - 1) - offset, x  #

    def on_key_pressed(self, ks, key):
        if ks in Reader.UP:
            self.scroll.pos -= 1
        elif ks in Reader.DOWN:
            self.scroll.pos += 1
        elif ks in Reader.PPAGE:
            self.scroll.pos -= self.scroll.view
        elif ks in Reader.NPAGE:
            self.scroll.pos += self.scroll.view
        elif ks in Reader.HOME:
            self.scroll.pos = 0
        elif ks in Reader.MEND:
            self.scroll.pos = self.scroll.content - self.scroll.view
        else:
            return False  # not handled
        return True  # handled

    # region QuickSearch
    def qsPager(self):
        return Pager(
            parser.find_visible_token(self.tokens, self.scroll.pos)[0],
            lambda: parser.find_visible_token(self.tokens, self.scroll.pos + self.scroll.view)[0],
            lambda: parser.find_visible_token(self.tokens, self.scroll.pos)[0] - 1)

    def ensureVisibleOnQsKey(self, ks, tidx, off):
        if ks in Qs.HOME or ks in Qs.END:
            self.scroll.ensure_visible(self.t2l[tidx].start + off, center=True)
        elif ks in Qs.NPAGE:
            self.scroll.ensure_visible(self.t2l[tidx].start + off + self.scroll.view - 1)
        elif ks in Qs.PPAGE:
            self.scroll.ensure_visible(self.t2l[tidx].start + off - self.scroll.view + 1)
        else:
            self.scroll.ensure_visible(self.t2l[tidx].start + off)
    # endregion QuickSearch
