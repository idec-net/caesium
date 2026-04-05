import curses


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

    def draw(self, win):  # type: (curses.window) -> None
        pass
