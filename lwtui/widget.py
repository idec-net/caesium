import curses
import re
from datetime import date, datetime

import lwtui.theme


class Widget:
    focused: bool = False
    enabled: bool = True
    focusable: bool = True
    focusOrder: float = 0
    x: int = 0
    y: int = 0
    w: int = 0
    h: int = 0

    def right(self):
        return self.x + self.w

    def setFocused(self, focused):
        pass

    def onKeyPressed(self, ks, key):
        pass

    def draw(self, win: curses.window) -> None:
        pass


class SeparatorHWidget(Widget):
    focusable: bool = False
    h: int = 1

    def __init__(self, y=0, x=0):
        self.style = lwtui.theme.THEME.sepH
        self.x = x
        self.y = y

    def draw(self, win: curses.window) -> None:
        win.addstr(self.y, self.x, self.style.ch * self.w, self.style.color)


class LabelWidget(Widget):
    focusable: bool = False
    h: int = 1

    def __init__(self, txt="", y=0, x=0, enabled=True):
        self.style = lwtui.theme.THEME.label
        self.x = x
        self.y = y
        self.w = len(txt)
        self.txt = txt
        self.enabled = enabled
        self.color = self._color(self.style)

    def _color(self, style):
        return (style.cEnabled if self.enabled else
                style.cDisabled)

    def setEnabled(self, enabled):
        if self.enabled == enabled:
            return
        self.enabled = enabled
        self.color = self._color(self.style)

    def setTxt(self, txt):
        self.txt = txt
        self.w = len(txt)

    def draw(self, win: curses.window) -> None:
        if self.w <= 0:  # termux curses v6.5.20240832 crashes w zero width
            return
        win.addstr(self.y, self.x, " " * self.w, self.color)
        win.addnstr(self.y, self.x, self.txt, self.w, self.color)


class CheckBoxWidget(Widget):
    h: int = 1

    def __init__(self, lbl="", fOrder=0, y=0, x=0, checked=False, enabled=True):
        self.style = lwtui.theme.THEME.checkbox
        self.focusOrder = fOrder
        self.x = x
        self.y = y
        self.lbl = lbl
        self.checked = checked
        self.enabled = enabled
        self.content = self._content(checked, lbl)
        self.w = len(self.content)
        self.color = self._color(self.style)

    def _color(self, style):
        return (style.cFocused if self.focused and self.enabled else
                style.cEnabled if self.enabled else
                style.cDisabled)

    def _content(self, checked, lbl):
        checkMark = self.style.checked if checked else self.style.unchecked
        return "%s%s" % (checkMark, lbl)

    def setChecked(self, checked):
        if self.checked == checked:
            return
        self.checked = checked
        self.content = self._content(checked, self.lbl)
        self.color = self._color(self.style)

    def setFocused(self, focused):
        if self.focused == focused:
            return
        self.focused = focused
        self.color = self._color(self.style)

    def setEnabled(self, enabled):
        if self.enabled == enabled:
            return
        self.enabled = enabled
        self.color = self._color(self.style)

    def draw(self, win):
        if self.w <= 0:
            return  #
        win.addnstr(self.y, self.x, self.content, self.w, self.color)

    def onKeyPressed(self, ks, key):
        if key == ord(" "):
            self.setChecked(not self.checked)


class InputWidget(Widget):
    cursor: int = 0
    offset: int = 0
    h: int = 1

    def __init__(self, txt="", fOrder: float = 0, y=0, x=0, w=0,
                 *, placeholder="", mask=None):
        self.style = lwtui.theme.THEME.input
        self.focusOrder = fOrder
        self.x = x
        self.y = y
        self.w = w
        self.txt = txt
        self.placeholder = placeholder
        self.mask = mask
        self.color = self._color(self.style)

    def _color(self, style):
        return (style.cFocused if self.focused and self.enabled else
                style.cEnabled if self.enabled else
                style.cDisabled)

    def setFocused(self, focused):
        if self.focused == focused:
            return
        self.focused = focused
        self.color = self._color(self.style)

    def setEnabled(self, enabled):
        if self.enabled == enabled:
            return
        self.enabled = enabled
        self.color = self._color(self.style)

    def draw(self, win: curses.window) -> None:
        if self.w <= 0:
            return  #
        left = self.style.left
        right = self.style.right
        attr = self.color | self.style.attr
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

    def _moveCursorRight(self, increment):
        self.cursor = min(len(self.txt), self.cursor + increment)
        contentWidth = self.w - (len(self.style.left) + len(self.style.right))
        if self.cursor - self.offset > contentWidth - 1:
            self.offset += increment

    def _moveCursorLeft(self, decrement):
        self.cursor = max(0, self.cursor - decrement)
        if self.cursor - self.offset < 0:
            self.offset -= decrement
        if self.offset and self.offset == self.cursor:
            self.offset -= 1

    def onKeyPressed(self, ks, key):
        # TODO: Common navigation commands?
        if key == curses.KEY_HOME:
            self.cursor = 0
            self.offset = 0
        elif key == curses.KEY_END:
            self.cursor = len(self.txt)
            contentWidth = self.w - (len(self.style.left) + len(self.style.right))
            self.offset = max(0, self.cursor - contentWidth + 1)
        elif key == curses.KEY_LEFT:
            self._moveCursorLeft(1)
        elif key == curses.KEY_RIGHT:
            self._moveCursorRight(1)
        elif key in (curses.KEY_BACKSPACE, 127):
            # 127 - Ctrl+? - Android backspace
            txt = self.txt[0:max(0, self.cursor - 1)] + self.txt[self.cursor:]
            if not self.mask or self.mask.match(txt):
                self.txt = txt
                self._moveCursorLeft(1)
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
                    self._moveCursorRight(len(ks))

    def getWinCursorPos(self):
        return len(self.style.left) + self.cursor - self.offset


class ErrIndicator:
    err: bool = False
    w: int = 0
    txt: str = ""

    def __init__(self):
        self.style = lwtui.theme.THEME.error

    def setErr(self, err):
        if self.err == err:
            return
        self.err = err
        self.txt = self.style.ch

    def draw(self, win, y, x, color):
        if self.err:
            win.addstr(y, x - self.style.len, self.txt, color | self.style.attr)

    def __bool__(self):
        return self.err


class InputRegexWidget(InputWidget):
    regexOn: bool = True

    def __init__(self, txt="", fOrder=0, y=0, x=0, w=0,
                 *, placeholder="", regexOn=False):
        super().__init__(txt=txt, fOrder=fOrder, y=y, x=x, w=w,
                         placeholder=placeholder)
        self.x = x
        self.y = y
        self.w = w
        self.txt = txt
        self.err = ErrIndicator()
        self.placeholder = placeholder
        self.regexOn = regexOn
        self.template = self._compileRegex()

    def _compileRegex(self):
        template = None
        try:
            if self.regexOn:
                template = re.compile(self.txt, re.IGNORECASE)
            self.err.setErr(False)
        except re.error:
            self.err.setErr(True)
        return template

    def onKeyPressed(self, ks, key):
        super().onKeyPressed(ks, key)
        self.template = self._compileRegex()

    def setRegexOn(self, regex):
        self.regexOn = regex
        self.template = self._compileRegex()

    def draw(self, win):  # type: (curses.window) -> None
        super().draw(win)
        self.err.draw(win, self.y, self.x + self.w - len(self.style.right),
                      self.color)


class InputDateWidget(InputWidget):
    def __init__(self, fOrder: float = 0, y=0, x=0, w=0, *, dt: date = None):
        super().__init__(fOrder=fOrder, y=y, x=x, w=w,
                         placeholder="DD.MM.YYYY",
                         mask=re.compile(r"^[0-9.]*$"))
        self.err = ErrIndicator()
        if dt:
            self.setDate(dt)

    def getDate(self):
        try:
            return datetime.strptime(self.txt, "%d.%m.%Y").date()
        except ValueError:
            return None

    def setDate(self, d: date):
        self.txt = d.strftime("%d.%m.%Y")

    def onKeyPressed(self, ks, key):
        super().onKeyPressed(ks, key)
        self.err.setErr(bool(self.txt and not self.getDate()))

    def draw(self, win: curses.window) -> None:
        super().draw(win)
        self.err.draw(win, self.y, self.x + self.w - len(self.style.right),
                      self.color)
