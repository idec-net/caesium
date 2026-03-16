import curses
import dataclasses
import os
import re
import sys
import webbrowser
from typing import List, Optional

from core import parser

CONFIG_FILEPATH = "caesium.cfg"


def ensure_exists():
    if not os.path.exists(CONFIG_FILEPATH):
        with open("caesium.def.cfg", "r") as def_cfg:
            with open(CONFIG_FILEPATH, "w") as cfg:
                cfg.write(def_cfg.read())


@dataclasses.dataclass
class Echo:
    name: str
    desc: str
    sync: bool

    def __gt__(self, other):
        if other:
            return self.name > other.name
        return False

    def __lt__(self, other):
        if other:
            return self.name < other.name
        return False

    def __eq__(self, other):
        if isinstance(other, str):
            return self.name == other
        return super().__eq__(other)


ECHO_OUT = Echo("out", "Исходящие", False)
ECHO_DRAFTS = Echo("out", "Черновики", False)
ECHO_FAVORITES = Echo("favorites", "Избранные сообщения", False)
ECHO_CARBON = Echo("carbonarea", "Карбонка", False)
ECHO_FIND = Echo("<find-results>", "Результаты поиска", False)


@dataclasses.dataclass
class Node:
    nodename: str = "untitled node"
    echoareas: List[Echo] = dataclasses.field(default_factory=list)
    url: str = ""
    auth: str = ""
    to: List[str] = dataclasses.field(default_factory=list)
    archive: List[Echo] = dataclasses.field(default_factory=list)
    stat: List[Echo] = dataclasses.field(default_factory=list)


@dataclasses.dataclass
class Config:
    nodes: List[Node] = dataclasses.field(default_factory=list)
    browser = webbrowser
    editor = "nano"
    oldquote = False
    splash = True
    themeColors = "default"
    themeWidgets = ""
    db = "ait"
    keys = "default"
    twit: List[str] = dataclasses.field(default_factory=list)

    def load(self):
        self.nodes.clear()
        self.editor = "nano"
        self.oldquote = False
        self.db = "ait"
        #
        node = None  # type: Optional[Node]
        shrink_spaces = re.compile(r"(\s\s+|\t+)")
        with open(CONFIG_FILEPATH) as f:
            lines = f.read().splitlines()
        for line in lines:
            param = shrink_spaces.sub(" ", line.strip()).split(" ", maxsplit=2)
            #
            if param[0] == "nodename":
                if node:
                    node.echoareas.sort()
                    self.nodes.append(node)
                node = Node(nodename=" ".join(param[1:]))
            elif param[0] == "node":
                node.url = param[1]
                if not node.url.endswith("/"):
                    node.url += "/"
            elif param[0] == "auth":
                node.auth = param[1]
            elif param[0] == "to":
                node.to = " ".join(param[1:]).split(",")
            elif param[0] == "echo":
                node.echoareas.append(Echo(sys.intern(param[1]),
                                           "".join(param[2:]), True))
            elif param[0] == "stat":
                node.echoareas.append(Echo(sys.intern(param[1]),
                                           "".join(param[2:]), False))
            elif param[0] == "archive":
                node.archive.append(Echo(sys.intern(param[1]),
                                         "".join(param[2:]), False))
            #
            if param[0] == "editor":
                self.editor = " ".join(param[1:])
            elif param[0] == "theme":
                self.themeColors = param[1]
                self.themeWidgets = ""
                if len(param) > 2 and not param[2].startswith("#"):
                    self.themeWidgets = param[2].split(" ")[0]
            elif param[0] == "nosplash":
                self.splash = False
            elif param[0] == "oldquote":
                self.oldquote = True
            elif param[0] == "db":
                self.db = param[1]
            elif param[0] == "browser":
                self.browser = webbrowser.GenericBrowser(param[1])
            elif param[0] == "twit":
                self.twit = param[1].split(",")
            elif param[0] == "keys":
                self.keys = param[1]
            elif param[0] == "inlinestyle":
                parser.INLINE_STYLE_ENABLED = True

        node.echoareas.sort()
        self.nodes.append(node)
        for n in self.nodes:
            n.echoareas.insert(0, ECHO_FAVORITES)
            n.echoareas.insert(1, ECHO_CARBON)


#
# Theme
#
UI_BORDER = "border"
UI_CURSOR = "cursor"
UI_SCROLL = "scrollbar"
UI_STATUS = "statusline"
UI_TITLES = "titles"
UI_CODE = "code"
UI_COMMENT = "comment"
UI_HEADER = "header"
UI_ORIGIN = "origin"
UI_QUOTE1 = "quote1"
UI_QUOTE2 = "quote2"
UI_TEXT = "text"
UI_URL = "url"

TOKEN2UI = {
    parser.TT.CODE: UI_CODE,
    parser.TT.COMMENT: UI_COMMENT,
    parser.TT.HEADER: UI_HEADER,
    parser.TT.ORIGIN: UI_ORIGIN,
    parser.TT.QUOTE1: UI_QUOTE1,
    parser.TT.QUOTE2: UI_QUOTE2,
    parser.TT.URL: UI_URL,
}

color_pairs = {
    # "ui-element": [color-pair-NUM, bold-attr]
    UI_BORDER: [1, 0],
    UI_CURSOR: [2, 0],
    UI_SCROLL: [3, 0],
    UI_STATUS: [4, 0],
    UI_TITLES: [5, 0],
    # tokens
    UI_CODE: [6, 0],
    UI_COMMENT: [7, 0],
    UI_HEADER: [8, 0],
    UI_ORIGIN: [9, 0],
    UI_QUOTE1: [10, 0],
    UI_QUOTE2: [11, 0],
    UI_TEXT: [12, 0],
    UI_URL: [13, 0],
}


def get_color(theme_part):
    if theme_part not in color_pairs:
        theme_part = UI_TEXT
    cp, bold = color_pairs[theme_part]
    return curses.color_pair(cp) | bold


if sys.version_info >= (3, 10):
    def can_change_color():
        return (curses.has_extended_color_support()
                and curses.can_change_color())
else:
    def can_change_color():
        return ("256" in os.environ.get("TERM", "linux")
                and curses.can_change_color())


def init_hex_color(color, cache, idx):
    if not can_change_color():
        raise ValueError("No extended color support in the terminal "
                         + str(curses.termname()))

    if len(color) == 7 and color[0] == "#":
        r = int("0x" + color[1:3], 16)
        g = int("0x" + color[3:5], 16)
        b = int("0x" + color[5:7], 16)
    elif len(color) == 4 and color[0] == "#":
        r = int("0x" + color[1] * 2, 16)
        g = int("0x" + color[2] * 2, 16)
        b = int("0x" + color[3] * 2, 16)
    else:
        raise ValueError("Invalid color value :: " + color)
    if (r, g, b) in cache:
        return cache[(r, g, b)], False
    curses_r = int(round(r / 255 * 1000))  # to 0..1000
    curses_g = int(round(g / 255 * 1000))
    curses_b = int(round(b / 255 * 1000))
    curses.init_color(idx, curses_r, curses_g, curses_b)
    cache[(r, g, b)] = idx
    return idx, True


def load_colors(theme):
    colors = ["black", "red", "green", "yellow", "blue",
              "magenta", "cyan", "white",
              "brblack", "brred", "brgreen", "bryellow", "brblue",
              "brmagenta", "brcyan", "brwhite"]
    c256cache = {}
    c256idx = curses.COLORS - 1
    shrink_spaces = re.compile(r"(\s\s+|\t+)")
    color3_regex = re.compile(r"#[a-fA-F0-9]{3}")
    color6_regex = re.compile(r"#[a-fA-F0-9]{6}")
    with open("themes/" + theme + ".cfg", "r") as f:
        lines = f.readlines()
    for line in lines:
        # sanitize
        line = shrink_spaces.sub(" ", line.strip())
        nocolor = color3_regex.sub("-" * 4, color6_regex.sub("-" * 7, line))
        if "#" in nocolor:
            line = line[0:nocolor.index("#")].strip()  # skip comments
        if not line:
            continue
        params = line.split(" ")
        if (len(params) not in (3, 4)
                or params[0] not in color_pairs
                or len(params) == 4 and params[3] != "bold"):
            raise ValueError("Invalid theme params :: " + line)
        # foreground
        if params[1].startswith("#"):
            fg, idxChange = init_hex_color(params[1], c256cache, c256idx)
            if idxChange:
                c256idx -= 1
        elif params[1].startswith("color"):
            fg = int(params[1][5:])
        else:
            fg = colors.index(params[1])
        # background
        if params[2] == "default":
            bg = -1
        elif params[2].startswith("#"):
            bg, idxChange = init_hex_color(params[2], c256cache, c256idx)
            if idxChange:
                c256idx -= 1
        elif params[2].startswith("color"):
            bg = int(params[2][5:])
        else:
            bg = colors.index(params[2])
        # bold
        color_pairs[params[0]][1] = curses.A_NORMAL
        if len(params) == 4:
            color_pairs[params[0]][1] = curses.A_BOLD
        #
        curses.init_pair(color_pairs[params[0]][0], fg, bg)
