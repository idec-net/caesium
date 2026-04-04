#!/usr/bin/env python3
# coding=utf-8
import base64
import codecs
import curses
import itertools
import locale
import os
import pickle
import subprocess
import sys
import traceback
from typing import List, Optional

from core import (
    __version__, parser, client, config, ui, utils, outgoing, keystroke,
    FEAT_X_C, FEAT_U_E
)
from core.cmd import Common, Reader, Selector, Qs
from core.config import (
    CFG, COLOR_PAIRS, getColor, UI_BORDER, UI_TEXT, UI_CURSOR
)

# TODO: Add http/https/socks proxy support
# import socket
# import socks
# socks.set_default_proxy(socks.SOCKS5, '127.0.0.1', 8081)
# socket.socket = socks.socksocket

blacklist = []
if os.path.exists("blacklist.txt"):
    with open("blacklist.txt", "r") as bl:
        blacklist = list(filter(None, map(lambda it: it.strip(),
                                          bl.readlines())))

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


# region Mailer
def makeToss(node):  # type: (config.Node) -> None
    nodeDir = outgoing.directory(node)
    lst = [x for x in os.listdir(nodeDir)
           if x.endswith(".out")]
    for msg in lst:
        with codecs.open(nodeDir + "%s" % msg, "r", "utf-8") as f:
            text_raw = f.read()
        txtB64 = base64.b64encode(text_raw.encode("utf-8")).decode("utf-8")
        with codecs.open(nodeDir + "%s.toss" % msg, "w", "utf-8") as f:
            f.write(txtB64)
        os.rename(nodeDir + "%s" % msg,
                  nodeDir + "%s%s" % (msg, "msg"))


def sendMail(node):  # type: (config.Node) -> None
    nodeDir = outgoing.directory(node)
    lst = [x for x in sorted(os.listdir(nodeDir))
           if x.endswith(".toss")]
    total = str(len(lst))
    try:
        for n, msg in enumerate(lst, start=1):
            print("\rОтправка сообщения: " + str(n) + "/" + total, end="")
            msgToss = nodeDir + msg
            with codecs.open(msgToss, "r", "utf-8") as f:
                text = f.read()
            #
            result = client.sendMsg(node.url, node.auth, text)
            #
            if result.startswith("msg ok"):
                os.remove(msgToss)
            elif result == "msg big!":
                print("\nERROR: very big message (limit 64K)!")
            elif result == "auth error!":
                print("\nERROR: unknown auth!")
            else:
                print("\nERROR: unknown error!")
        if len(lst) > 0:
            print()
    except Exception as ex:
        print("\nОшибка: не удаётся связаться с нодой. " + str(ex))


def debundle(bundle, getList=None):
    messages = []
    for msg in filter(None, bundle):
        m = msg.split(":")
        msgid = m[0]
        if len(msgid) == 20 and m[1]:
            msgbody = base64.b64decode(m[1].encode("ascii")).decode("utf8").split("\n")
            if getList and msgid not in getList:
                print(f"\nWARNING:"
                      f" msgid: {msgid} received but not requested: [{', '.join(getList)}]."
                      f" Skipped. Please report to node sysop.")
            else:
                messages.append([msgid, msgbody])
    if messages:
        api.saveMessage(messages, CFG.node(), CFG.node().to)


def getMail(node_, forceFullIdx=False):  # type: (config.Node, bool) -> None
    features = api.getNodeFeatures(node_.nodename)
    if features is None:
        print("Запрос x/features...")
        features = client.getFeatures(node_.url)
        api.saveNodeFeatures(node_.nodename, features)
        print("  x/features: " + ", ".join(features))
    isNodeSmart = FEAT_X_C in features and FEAT_U_E in features
    #
    echoareas = list(map(lambda e: e.name, filter(lambda e: e.sync,
                                                  node_.echoareas)))
    oldNec = None
    newNec = None
    offsets = None
    if isNodeSmart:
        oldNec = api.getNodeEchoCounts(node_.nodename)
        newNec = client.getEchoCount(node_.url, echoareas)
        offsets = utils.offsetsEchoCount(oldNec or {}, newNec)

    fetchMsgList = []
    if isNodeSmart and oldNec and not forceFullIdx:
        print("Получение свежего индекса от ноды...")
        remoteMsgList = []
        grouped = {offset: [ec[0] for ec in ec]
                   for offset, ec in itertools.groupby(offsets.items(),
                                                       lambda ec: ec[1])}
        for offset, echoareas in grouped.items():
            print("  offset %s: %s" % (str(offset), ", ".join(echoareas)))
            remoteMsgList += client.getMsgList(node_.url, echoareas, offset)
    else:
        print("Получение полного индекса от ноды...")
        remoteMsgList = client.getMsgList(node_.url, echoareas)

    print("Построение разностного индекса...")
    localIndex = None
    for line in remoteMsgList:
        if parser.echoTemplate.match(line):
            localIndex = api.getEchoMsgids(line)
        elif len(line) == 20 and line not in localIndex and line not in blacklist:
            fetchMsgList.append(line)
    if fetchMsgList:
        total = str(len(fetchMsgList))
        count = 0
        for getList in utils.separate(fetchMsgList):
            count += len(getList)
            print("\rПолучение сообщений: " + str(count) + "/" + total, end="")
            debundle(client.getBundle(node_.url, "/".join(getList)), getList)
    else:
        print("Новых сообщений не обнаружено.", end="")
    if isNodeSmart:
        api.saveNodeEchoCounts(node_.nodename, newNec)
    print()


def fetchMail(node_, forceFullIdx=False):  # type: (config.Node, bool) -> None
    print("Работа с " + node_.url)
    try:
        if node_.auth:
            makeToss(node_)
            sendMail(node_)
        getMail(node_, forceFullIdx)
    except KeyboardInterrupt:
        print("\nПрервано пользователем")
    except Exception as ex:
        print("\nОШИБКА: " + str(ex))
        print(traceback.format_exc())
    input("Нажмите Enter для продолжения.")
# endregion Mailer


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

    def getCounts(self, node_, new=False):
        for echo in node_.echoareas:  # type: config.Echo
            if new or echo.name not in self.total:
                self.total[echo.name] = api.getEchoLength(echo.name)
        for echo in node_.archive:  # type: config.Echo
            if echo.name not in self.total:
                self.total[echo.name] = api.getEchoLength(echo.name)
        self.total[config.ECHO_CARBON.name] = len(api.getCarbonarea())
        self.total[config.ECHO_FAVORITES.name] = len(api.getFavoritesList())
        self.total[config.ECHO_DRAFTS.name] = outgoing.getOutLength(node_, True)
        self.total[config.ECHO_OUT.name] = outgoing.getOutLength(node_, False)

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


def editConfig():
    ui.terminateCurses()
    p = subprocess.Popen(CFG.editor + " " + config.CONFIG_FILEPATH, shell=True)
    p.wait()
    CFG.resetNode()
    CFG.load()
    ui.initializeCurses()


class EchoSelectorScreen:
    echoCursor: int = 0
    archiveCursor: int = 0
    nextEcho: bool = False
    echos: ui.EchoModeStack = None
    scroll: ui.ScrollCalc = None
    qs: Optional[ui.QuickSearch] = None
    go: bool = True

    def __init__(self):
        self.counts = Counts()
        self.reloadEchoareas()

    def reloadEchoareas(self):
        self.echoCursor = 0
        self.archiveCursor = 0
        self.echos = ui.EchoModeStack(ui.SelectorMode.ECHO,
                                      CFG.node().echoareas)
        ui.drawMessageBox("Подождите", False)
        self.counts.getCounts(CFG.node(), False)
        ui.stdscr.clear()
        self.updateScroll()

    def updateScroll(self):
        self.scroll = ui.ScrollCalc(len(self.echos.data), ui.HEIGHT - 2)
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
        ui.stdscr.clear()
        self.updateScroll()

    # noinspection PyUnusedLocal
    @staticmethod
    def onSearchItem(sidx, pattern, echo):
        result = []
        p = 0
        while match := pattern.search(echo.name, p):
            if p >= len(echo.name):
                break
            result.append(match)
            p = match.end()
        return [result] if result else None

    def show(self):
        while self.go:
            self.scroll.ensureVisible(self.echos.idx)
            self.draw(ui.stdscr, self.echos.idx, self.scroll, self.qs)
            #
            ks, key, _ = ui.getKeystroke()
            #
            if key == curses.KEY_RESIZE:
                ui.setTermSize()
                self.onResize()
            elif self.qs:
                if ks in Qs.CLOSE or ks in Qs.APPLY:
                    if ks in Qs.APPLY and self.qs.result:
                        self.echos.modeQsOn(self.qs.result)
                        self.updateScroll()
                    self.qs = None
                    curses.curs_set(0)
                else:
                    self.qs.onKeyPressedSearch(key, ks, self.scroll)
                    self.echos.idx = self.qs.ensureCursorVisible(
                        key, self.echos.idx, self.scroll)
            elif ks in Qs.OPEN:
                self.qs = ui.newQuickSearch(self.echos.data, self.onSearchItem)
            elif ks in Reader.QUIT and self.echos.stack:
                self.echos.pop()
                self.updateScroll()
            elif ks in Common.QUIT:
                self.go = False
            else:
                self.onKeyPressed(ks)

    def draw(self, win, cursor, scroll, qs):
        h, w = win.getmaxyx()
        self.drawEchoSelector(win, scroll.pos, cursor, qs, self.counts.counts)
        if scroll.is_scrollable:
            ui.drawScrollBarV(win, 1, w - 1, scroll)
        if qs:
            qs.draw(win)
        win.refresh()

    def drawEchoSelector(self, win, start, cursor, qs, counts):
        # type: (curses.window, int, int, ui.QuickSearch, List[List[str]]) -> None
        h, w = win.getmaxyx()
        color = getColor(UI_BORDER)
        win.addstr(0, 0, "─" * w, color)
        if self.echos.isArch():
            ui.drawTitle(win, 0, 0, "Архив")
        else:
            ui.drawTitle(win, 0, 0, "Конференция")
        #
        m = min(w - 38, max(map(lambda e: len(e.desc), self.echos.data)))
        count = "Сообщений"
        unread = "Не прочитано"
        description = "Описание"
        showDesc = (w >= 80) and m > 0
        if w < 80 or m == 0:
            m = len(unread) - 7
        ui.drawTitle(win, 0, w + 2 - m - len(count) - len(unread) - 1, count)
        ui.drawTitle(win, 0, w - 8 - m - 1, unread)
        if showDesc:
            ui.drawTitle(win, 0, w - len(description) - 2, description)

        for y in range(1, h - 1):
            echoN = y - 1 + start
            if echoN == cursor:
                color = getColor(UI_CURSOR)
            else:
                color = getColor(UI_TEXT)
            win.addstr(y, 0, " " * w, color)
            if echoN >= len(self.echos.data):
                continue  #
            #
            win.attrset(color)
            echo = self.echos.data[echoN]
            total, unread = counts[echoN]
            if int(unread) > 0:
                win.addstr(y, 0, "+")
            win.addstr(y, 2, echo.name)
            win.addstr(y, w - 10 - m - len(total), total)
            win.addstr(y, w - 2 - m - len(unread), unread)
            if showDesc:
                win.addstr(y, max(w - m - 1, w - 1 - len(echo.desc)),
                           echo.desc[0:w - 38])
            #
            if qs and echoN in qs.result:
                idx = qs.result.index(echoN)
                for match in qs.matches[idx]:
                    win.addstr(y, 2 + match.start(),
                               echo.name[match.start():match.end()],
                               color | curses.A_REVERSE)

        ui.drawStatusBar(win, mode=self.echos.mode, text=CFG.node().nodename)

    def onKeyPressed(self, ks):
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
            self.fetchMail(force_full_idx=(ks in Selector.FGET))
        elif ks in Selector.ARCHIVE and len(CFG.node().archive) > 0:
            self.toggleArchive()
        elif ks in Selector.ENTER:
            self.readEcho()
        elif ks in Selector.OUT:
            self.readOutgoing()
        elif ks in Selector.DRAFTS:
            self.readDrafts()
        elif ks in Selector.NNODE:
            CFG.nextNode()
            self.reloadEchoareas()
        elif ks in Selector.PNODE:
            CFG.prevNode()
            self.reloadEchoareas()
        elif ks in Selector.CONFIG:
            editConfig()
            ui.loadTheme(CFG)
            loadKeys()
            CFG.resetNode()
            self.reloadEchoareas()
        elif ks in Selector.FIND:
            win = ui.FindQueryWindow(cfg=CFG)
            findResult = win.show()
            if win.resized:
                self.onResize()
            if findResult:
                findResult = sorted(findResult, key=lambda m: m.time)
                self.showReader(ui.EchoReaderScreen(
                    config.ECHO_FIND, 0, True, self.counts,
                    mode=ui.ReaderMode.FIND, msgids=findResult))

    def fetchMail(self, force_full_idx):
        ui.terminateCurses()
        os.system('cls' if os.name == 'nt' else 'clear')
        fetchMail(CFG.node(), force_full_idx)
        ui.initializeCurses()
        ui.drawMessageBox("Подождите", False)
        self.counts.getCounts(CFG.node(), True)
        self.counts.rescanCounts(self.echos.data)
        ui.stdscr.clear()
        self.echos.idx = self.counts.findNew(0)

    def readEcho(self):
        ui.drawMessageBox("Подождите", False)
        last = 0
        curEcho = self.echos.curItem()
        if curEcho.name in self.counts.lasts:
            last = self.counts.lasts[curEcho.name]
        last = max(0, min(self.counts.total[curEcho.name], last))
        self.showReader(ui.EchoReaderScreen(
            curEcho, last, self.echos.isArch(), self.counts))
        self.counts.rescanCounts(self.echos.data)
        if self.nextEcho and isinstance(self.nextEcho, bool):
            self.echos.idx = self.counts.findNew(self.echos.idx)
            self.nextEcho = False
        elif self.nextEcho and isinstance(self.nextEcho, str):
            cur_node = CFG.node()
            if ((not self.echos.isArch() and self.nextEcho in cur_node.archive)
                    or (self.echos.isArch() and (self.nextEcho in cur_node.echoareas
                                                 or self.nextEcho in cur_node.stat))):
                self.toggleArchive()
            # noinspection PyTypeChecker
            self.echos.idx = self.echos.findItemIdx(self.nextEcho)
            if self.echos.idx == -1:
                self.echos.idx = 0
            self.nextEcho = False

    def readOutgoing(self):
        outLength = outgoing.getOutLength(CFG.node(), drafts=False)
        if outLength:
            self.showReader(ui.EchoReaderScreen(
                config.ECHO_OUT, outLength, self.echos.isArch(), self.counts))

    def readDrafts(self):
        outLength = outgoing.getOutLength(CFG.node(), drafts=True)
        if outLength:
            self.showReader(ui.EchoReaderScreen(
                config.ECHO_DRAFTS, 0, self.echos.isArch(), self.counts))

    def showReader(self, reader):
        self.go, self.nextEcho = reader.show()
        if reader.resized:
            self.onResize()

    def onResize(self):
        self.scroll = ui.ScrollCalc(len(self.echos.data), ui.HEIGHT - 2,
                                    self.echos.idx)
        ui.stdscr.clear()
        if self.qs:
            self.qs.y = ui.HEIGHT - 1
            self.qs.width = ui.WIDTH - len(ui.version) - 13


if sys.version_info >= (3, 11):
    loc = locale.getlocale()
else:
    # noinspection PyDeprecation
    loc = locale.getdefaultlocale()
locale.setlocale(locale.LC_ALL, loc[0] + "." + loc[1])

config.ensureExists()
CFG.load()
if CFG.db == "txt":
    import api.txt as api
elif CFG.db == "aio":
    import api.aio as api
elif CFG.db == "ait":
    import api.ait as api
elif CFG.db == "sqlite":
    import api.sqlite as api
else:
    raise Exception("Unsupported DB API :: " + CFG.db)
# create directories
api.init()
ui.api = api
if not os.path.exists("downloads"):
    os.mkdir("downloads")
outgoing.init(CFG)


def loadKeys():
    if CFG.keys == "default":
        # noinspection PyUnresolvedReferences
        import keys.default as keys
    elif CFG.keys == "android":
        # noinspection PyUnresolvedReferences
        import keys.android as keys
    elif CFG.keys == "vi":
        # noinspection PyUnresolvedReferences
        import keys.vi as keys
    else:
        raise Exception("Unknown Keys Scheme :: " + CFG.keys)
    keystroke.KsSeq.initSequences()


loadKeys()
try:
    ui.initializeCurses()
    ui.loadTheme(CFG)
    ui.stdscr.bkgd(" ", curses.color_pair(COLOR_PAIRS[UI_TEXT][0]))  # wo attrs

    if CFG.splash:
        ui.drawSplash(ui.stdscr, splash)
        curses.napms(2000)
        ui.stdscr.clear()
    EchoSelectorScreen().show()
finally:
    ui.terminateCurses()
