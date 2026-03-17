import curses
import re

import keys.default as keys

LABEL_SEARCH = "<введите regex для поиска>"


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


class QuickSearch:
    def __init__(self, items, matcher, width=0):
        self.items = items
        self.query = ""
        self.cursor = 0
        self.matches = []
        self.result = []
        self.idx = 0
        self.err = ""
        self.matcher = matcher
        self.width = width

    def draw(self, win, y, x, color):
        # type: (curses.window, int, int, int) -> None
        win.addstr(y, x, " " * (self.width or len(self.query)), color)
        if self.query:
            idx = self.idx + 1 if self.result else 0
            line = "%s  (%s%d / %d)" % (self.query, self.err, idx, len(self.result))
            win.addnstr(y, x, line, self.width or len(line), color)
        else:
            win.addstr(y, x, LABEL_SEARCH, color)
        win.move(y, x + len(self.query))

    def search(self, query, pos):
        self.result = []
        self.matches = []
        self.idx = -1
        self.query = query
        self.err = ""
        if not query:
            return  #
        try:
            template = re.compile(query, re.IGNORECASE)
        except re.error:
            self.err = "err "
            return  # error

        sidx = 0
        for i, item in enumerate(self.items):
            if matches := self.matcher(sidx, template, item):
                for m in matches:
                    self.result.append(i)
                    self.matches.append(m)
                    sidx += 1
                    if self.idx == -1 and i >= pos:
                        self.idx = len(self.result) - 1

    def on_key_pressed_search(self, key, keystroke, pager):
        if "Space" == keystroke:
            keystroke = " "
        if key in keys.s_home:
            self.home()
        elif key in keys.s_end:
            self.end()
        elif key in keys.s_down:
            self.next()
        elif key in keys.s_up:
            self.prev()
        elif key in keys.s_npage:
            self.next_after(pager.next_page_top())
        elif key in keys.s_ppage:
            self.prev_before(pager.prev_page_bottom())
        elif key == curses.KEY_LEFT:
            self.cursor = max(0, self.cursor - 1)
        elif key == curses.KEY_RIGHT:
            self.cursor = min(len(self.query), self.cursor + 1)
        elif key in (curses.KEY_BACKSPACE, 127):
            # 127 - Ctrl+? - Android backspace
            self.search(self.query[0:max(0, self.cursor - 1)]
                        + self.query[self.cursor:], pager.pos)
            self.cursor = max(0, self.cursor - 1)
        elif key == curses.KEY_DC:  # DEL
            self.search(self.query[0:max(0, self.cursor)]
                        + self.query[self.cursor + 1:], pager.pos)
        elif len(keystroke) == 1 and (not self.width
                                      or len(self.query) < self.width):
            self.search(self.query[0:self.cursor]
                        + keystroke
                        + self.query[self.cursor:], pager.pos)
            self.cursor = min(len(self.query), self.cursor + 1)

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

    def ensure_cursor_visible(self, key, cursor, scroll):
        if self.result:
            cursor = self.result[self.idx]
            if key in keys.s_npage:
                scroll.pos = cursor
            elif key in keys.s_ppage:
                scroll.pos = cursor - scroll.view
            scroll.ensure_visible(cursor)
        return cursor
