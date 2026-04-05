#!/usr/bin/env python3
# coding=utf-8
import curses
import locale
import os
import subprocess
import sys

import api.ait
from core import __version__, config, mailer, ui
from core.config import CFG, COLOR_PAIRS, UI_TEXT, CFG_FILEPATH

# TODO: Add http/https/socks proxy support
# import socket
# import socks
# socks.set_default_proxy(socks.SOCKS5, '127.0.0.1', 8081)
# socket.socket = socks.socksocket

splash = ["▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀",
          "████████ ████████ ████████ ████████ ███ ███  ███ ██████████",
          "███           ███ ███  ███ ███          ███  ███ ███ ██ ███",
          "███      ████████ ████████ ████████ ███ ███  ███ ███ ██ ███",
          "███      ███  ███ ███           ███ ███ ███  ███ ███ ██ ███",
          "████████ ████████ ████████ ████████ ███ ████████ ███ ██ ███",
          "▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄",
          "           ncurses ii/idec client        v" + __version__,
          "           Andrew Lobanov             28.03.2026",
          "           Cthulhu Fhtagn"]

if sys.version_info >= (3, 11):
    loc = locale.getlocale()
else:
    # noinspection PyDeprecation
    loc = locale.getdefaultlocale()
locale.setlocale(locale.LC_ALL, loc[0] + "." + loc[1])


# noinspection PyShadowingNames
def loadApi(cfg: config.Config):
    if cfg.db == "txt":
        import api.txt as api
    elif cfg.db == "aio":
        import api.aio as api
    elif cfg.db == "ait":
        import api.ait as api
    elif cfg.db == "sqlite":
        import api.sqlite as api
    else:
        raise Exception("Unsupported DB API :: " + cfg.db)
    api.init()
    global API
    API = api
    ui.API = api
    mailer.API = api


def loadKeys(cfg: config.Config):
    if cfg.keys == "default":
        import keys.default as keys
    elif cfg.keys == "android":
        import keys.android as keys
    elif cfg.keys == "vi":
        import keys.vi as keys
    else:
        raise Exception("Unknown Keys Scheme :: " + CFG.keys)
    if sys.version_info >= (3, 4):
        import importlib
        # noinspection PyTypeChecker
        importlib.reload(keys)
    else:
        # noinspection PyUnresolvedReferences
        reload(keys)
    ui.initKeys()


def editCfg():
    ui.terminateCurses()
    p = subprocess.Popen(CFG.editor + " " + CFG_FILEPATH, shell=True)
    p.wait()
    CFG.resetNode()
    CFG.load()
    ui.initializeCurses()
    ui.loadTheme(CFG)
    loadApi(CFG)
    loadKeys(CFG)
    CFG.resetNode()


API = api.ait
config.ensureExists()
CFG.load()
if not os.path.exists("downloads"):
    os.mkdir("downloads")
mailer.init(CFG)

try:
    ui.initializeCurses()
    ui.loadTheme(CFG)
    loadKeys(CFG)
    loadApi(CFG)
    ui.stdscr.bkgd(" ", curses.color_pair(COLOR_PAIRS[UI_TEXT][0]))  # wo attrs

    if CFG.splash:
        ui.drawSplash(ui.stdscr, splash)
        curses.napms(2000)
        ui.stdscr.clear()
    ui.EchoSelectorScreen(onEditCfg=editCfg).show()
finally:
    ui.terminateCurses()
