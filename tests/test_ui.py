import curses

import pytest

from api import MsgMetadata
from core import parser, ui
from core.ui import MsgModeStack, ReaderMode, QuickSearch, EchoReaderScreen

# pycodestyle - Error codes
# https://pycodestyle.pycqa.org/en/latest/intro.html#error-codes


def _colorPairMock(num):
    return num


@pytest.fixture(autouse=True)
def options():
    parser.INLINE_STYLE_ENABLED = False
    parser.HORIZONTAL_SCROLL_ENABLED = False
    curses.color_pair = _colorPairMock


def msg(msgid):
    return MsgMetadata(msgid, "", "", 0, "", "", "", "")


def test_pushPop():
    msgs = MsgModeStack(ReaderMode.ECHO, [], -1)
    assert not msgs.stack
    assert msgs.mode == ReaderMode.ECHO
    assert msgs.data == []
    assert msgs.idx == -1

    # re-write current mode
    msgs.push(ReaderMode.ECHO, [msg("0")])
    assert not msgs.stack
    assert msgs.mode == ReaderMode.ECHO
    assert msgs.data == [msg("0")]
    assert msgs.idx == -1

    # push on new mode only
    msgs.idx = 0
    msgs.push(ReaderMode.SUBJ, [msg("1"), msg("0")])
    assert msgs.stack == [(ReaderMode.ECHO, [msg("0")], 0)]
    assert msgs.mode == ReaderMode.SUBJ
    assert msgs.data == [msg("1"), msg("0")]
    assert msgs.idx == 1

    msgs.pop()
    assert not msgs.stack
    assert msgs.mode == ReaderMode.ECHO
    assert msgs.data == [msg("0")]
    assert msgs.idx == 0


def test_modeSubj():
    msgs = MsgModeStack(ReaderMode.ECHO, [msg("0")], 0)
    #
    msgs.modeSubjOn([msg("1"), msg("0")])
    assert msgs.stack == [(ReaderMode.ECHO, [msg("0")], 0)]
    assert msgs.mode == ReaderMode.SUBJ
    assert msgs.data == [msg("1"), msg("0")]
    assert msgs.idx == 1
    #
    msgs.modeSubjOn([msg("2"), msg("1"), msg("0")])
    assert msgs.stack == [(ReaderMode.ECHO, [msg("0")], 0)]
    assert msgs.mode == ReaderMode.SUBJ
    assert msgs.data == [msg("2"), msg("1"), msg("0")]
    assert msgs.idx == 2
    #
    msgs.modeSubjOff()
    assert not msgs.stack
    assert msgs.mode == ReaderMode.ECHO
    assert msgs.data == [msg("0")]
    assert msgs.idx == 0


def test_modeSubjDifferMsgid():
    msgs = MsgModeStack(ReaderMode.ECHO, [msg("0"), msg("1")], 1)
    #
    msgs.modeSubjOn([msg("1"), msg("01"), msg("001"), msg("0001")])
    assert msgs.stack == [(ReaderMode.ECHO, [msg("0"), msg("1")], 1)]
    assert msgs.mode == ReaderMode.SUBJ
    assert msgs.data == [msg("1"), msg("01"), msg("001"), msg("0001")]
    assert msgs.idx == 0
    #
    msgs.idx = 3  # 0001
    msgs.pop()
    assert not msgs.stack
    assert msgs.mode == ReaderMode.ECHO
    assert msgs.data == [msg("0"), msg("1")]
    assert msgs.idx == 1  # no 0001 msg, restore firstly selected


def test_modeQs():
    msgs = MsgModeStack(ReaderMode.ECHO, [msg("0"), msg("1")], 1)
    #
    msgs.modeQsOn([1])
    assert msgs.stack == [(ReaderMode.ECHO, [msg("0"), msg("1")], 1)]
    assert msgs.mode == ReaderMode.SEARCH
    assert msgs.data == [msg("1")]
    assert msgs.idx == 0
    #
    msgs.modeSubjOn([msg("10"), msg("11"), msg("1")])
    assert msgs.stack == [(ReaderMode.ECHO, [msg("0"), msg("1")], 1),
                          (ReaderMode.SEARCH, [msg("1")], 0)]
    assert msgs.mode == ReaderMode.SUBJ
    assert msgs.data == [msg("10"), msg("11"), msg("1")]
    assert msgs.idx == 2
    #
    msgs.pop()
    msgs.pop()
    msgs.pop()
    #
    assert not msgs.stack
    assert msgs.mode == ReaderMode.ECHO
    assert msgs.data == [msg("0"), msg("1")]
    assert msgs.idx == 1


class ScrMock:
    def __init__(self, h, w):
        self.height = h
        self.width = w
        self.text = [["" for _ in range(w)]
                     for _ in range(h)]

    def clear(self):
        self.text = [["" for _ in range(self.width)]
                     for _ in range(self.height)]

    def getmaxyx(self):
        return self.height, self.width

    def to_str(self):
        return list(map(lambda line: "".join(line), self.text))

    def addstr(self, y, x, line, attr=None):
        assert attr is None or isinstance(attr, int)
        assert y >= 0
        assert y < self.height
        assert x >= 0
        assert x < self.width
        assert x + len(line) <= self.width
        for i, ch in enumerate(line):
            if attr & curses.A_REVERSE:
                self.text[y][x + i] = "_"
            else:
                self.text[y][x + i] = ch


def test_renderTokenRightBorderNewLine():
    tokens = parser.tokenize([
        "aaaaaa> aaa-aa aaaaa aaa aaaaaaaaaa https://aaaa.aaaaaaaa.aa/. ",
        "aaaaaa> aaaaa aaaaaaaa aaaa https://aaaaaa.com/aaaaaaaaaa/aaaaaaaaaaaa-aaa",
        "",
    ])
    parser.prerender(tokens, width=62, height=30)
    scr = ScrMock(w=62, h=30)
    reader = ui.ReaderWidget()
    reader.setRect(x=0, y=5, w=62, h=24)
    # noinspection PyTypeChecker
    reader.renderBody(scr, tokens, 0)
    text = scr.to_str()
    assert text[6] == ". "


def test_renderTokenBottomInlineOverlapped():
    tokens = parser.tokenize([
        "1234567890 234 678 http://a.",
    ])
    parser.prerender(tokens, width=10, height=30)
    scr = ScrMock(8, 10)  # 8 = 5 header + 2 body + 1 status line
    reader = ui.ReaderWidget()
    reader.setRect(x=0, y=5, w=10, h=2)
    # noinspection PyTypeChecker
    reader.renderBody(scr, tokens, 0)
    text = scr.to_str()
    assert text[5] == "1234567890"
    assert text[6] == "234 678 "
    assert text[7] == ""  # status line


def test_renderTokenNewLineAtLastSpace():
    tokens = parser.tokenize([
        "aaaa.aa aaaaaaaa aaaaaa aaaaa. aaaaaaaa aaa aaaaaaaaaaa a aaa: "
        "https://aaaaaa\r"])

    parser.prerender(tokens, width=62, height=30)
    scr = ScrMock(30, 62)
    reader = ui.ReaderWidget()
    reader.setRect(x=0, y=5, w=62, h=24)
    # noinspection PyTypeChecker
    reader.renderBody(scr, tokens, 0)
    text = scr.to_str()
    assert text[5] == "aaaa.aa aaaaaaaa aaaaaa aaaaa. aaaaaaaa aaa aaaaaaaaaaa a aaa:"
    assert text[6] == "https://aaaaaa"
    assert text[7] == ""


def test_renderHorizontalScrollableMatches():
    parser.INLINE_STYLE_ENABLED = True
    parser.HORIZONTAL_SCROLL_ENABLED = True
    msgCode = ["", "", "", "", "", "", "", "",
               "a `c` a _i_ a **b** http://u",
               "====",
               "012345678901234567890",
               "===="]
    scr = ScrMock(30, 10)
    r = ui.ReaderWidget()
    r.setRect(x=0, y=5, w=10, h=24)
    r.setMsg(msgCode, 0)
    r.prerender(0)
    qs = QuickSearch(r.tokens, EchoReaderScreen.onSearchItem)
    qs.search("1", 0)

    # 0_234567890_23456789
    assert r.tokens[13].searchMatches[0][1].span() == (1, 2)
    assert r.tokens[13].searchMatches[1][1].span() == (11, 12)

    # noinspection PyTypeChecker
    r.renderBody(scr, r.tokens, scroll=0, scrollH=0, qs=qs)
    assert scr.to_str()[5:9] == ["a c a i a ",
                                 "b http://u",
                                 "====",
                                 "0_23456789"]
    scr.clear()

    # noinspection PyTypeChecker
    r.renderBody(scr, r.tokens, scroll=0, scrollH=1, qs=qs)
    assert scr.to_str()[5:9] == [" c a i a ",
                                 " http://u",
                                 "===",
                                 "_234567890"]
    scr.clear()

    # noinspection PyTypeChecker
    r.renderBody(scr, r.tokens, scroll=0, scrollH=2, qs=qs)
    assert scr.to_str()[5:9] == ["c a i a ",
                                 "http://u",
                                 "==",
                                 "234567890_"]
    scr.clear()

    # noinspection PyTypeChecker
    r.renderBody(scr, r.tokens, scroll=0, scrollH=3, qs=qs)
    assert scr.to_str()[5:9] == [" a i a ",
                                 "ttp://u",
                                 "=",
                                 "34567890_2"]
    scr.clear()

    # noinspection PyTypeChecker
    r.renderBody(scr, r.tokens, scroll=0, scrollH=4, qs=qs)
    assert scr.to_str()[5:9] == ["a i a ",
                                 "tp://u",
                                 "",
                                 "4567890_23"]
    scr.clear()

    # noinspection PyTypeChecker
    r.renderBody(scr, r.tokens, scroll=0, scrollH=5, qs=qs)
    assert scr.to_str()[5:9] == [" i a ",
                                 "p://u",
                                 "",
                                 "567890_234"]
    scr.clear()

    # noinspection PyTypeChecker
    r.renderBody(scr, r.tokens, scroll=0, scrollH=6, qs=qs)
    assert scr.to_str()[5:9] == ["i a ",
                                 "://u",
                                 "",
                                 "67890_2345"]
    scr.clear()
