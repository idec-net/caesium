#!/usr/bin/env python3
# coding=utf-8
import base64
import codecs
import curses
import hashlib
import itertools
import json
import locale
import os
import pickle
import re
import subprocess
import sys
import textwrap
import traceback
from shutil import copyfile
from typing import List, Optional, Union

from core import (
    __version__, parser, client, config, ui, utils, outgoing, keystroke,
    FEAT_X_C, FEAT_U_E
)
from core.cmd import Common, Out, Reader, Selector, Qs
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
                self.showReader(EchoReader(
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
        self.showReader(EchoReader(
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
            self.showReader(EchoReader(
                config.ECHO_OUT, outLength, self.echos.isArch(), self.counts))

    def readDrafts(self):
        outLength = outgoing.getOutLength(CFG.node(), drafts=True)
        if outLength:
            self.showReader(EchoReader(
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


def callEditor(node, out=''):
    ui.terminateCurses()
    h = hashlib.sha1(str.encode(open("temp", "r", ).read())).hexdigest()
    p = subprocess.Popen(CFG.editor + " ./temp", shell=True)
    p.wait()
    ui.initializeCurses()
    if h != hashlib.sha1(str.encode(open("temp", "r", ).read())).hexdigest():
        if not out:
            filepath = outgoing.outcount(node) + ".draft"
        else:
            filepath = outgoing.directory(node) + out
        outgoing.saveOut(filepath)
    else:
        os.remove("temp")


def signMsg(node, out, keyId):
    nodeDir = outgoing.directory(node)
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
        ui.showMessageBox(result.stderr)


def saveMessageToFile(msgid, echoarea):
    msg, size = api.readMsg(msgid, echoarea)
    filepath = "downloads/" + msgid + ".txt"
    with open(filepath, "w") as f:
        f.write("== " + msg[1] + " ==================== " + msgid + "\n")
        f.write("От:   " + msg[3] + " (" + msg[4] + ")\n")
        f.write("Кому: " + msg[5] + "\n")
        f.write("Тема: " + msg[6] + "\n")
        f.write("\n".join(msg[7:]))
    ui.showMessageBox("Сообщение сохранено в файл\n" + filepath)


def getMsg(msgid):
    node = CFG.node()
    bundle = client.getBundle(node.url, msgid)
    for msg in filter(None, bundle):
        m = msg.split(":")
        msgid = m[0]
        if len(msgid) == 20 and m[1]:
            msgbody = base64.b64decode(m[1].encode("ascii")).decode("utf8").split("\n")
            if node.to:
                carbonarea = api.getCarbonarea()
                if msgbody[5] in node.to and msgid not in carbonarea:
                    api.addToCarbonarea(msgid, msgbody)
            api.saveMessage([(msgid, msgbody)], node, node.to)


def saveAttachment(token):  # type: (parser.Token) -> None
    filepath = "downloads/" + token.filename
    with open(filepath, "wb") as attachment:
        attachment.write(token.filedata)
    ui.drawMessageBox("Файл сохранён '%s'" % filepath, True)
    ui.stdscr.getch()
    if token.pgpKey and parser.gpg:
        option = ui.SelectWindow("PGP Ключ '%s'" % token.filename,
                                 ["Отмена",
                                  "Открыть файл",
                                  "Добавить в хранилище"]).show()
        if option == 2:
            utils.openFile(filepath)
        elif option == 3:
            result = parser.gpg.import_keys_file(filepath)
            smsg = "\n".join(map(lambda rd: json.dumps(rd, sort_keys=True, indent=2),
                                 filter(lambda r: r['fingerprint'], result.results)))
            ui.showMessageBox(smsg)
    else:
        if ui.SelectWindow("Открыть '%s'?" % token.filename,
                           ["Нет", "Да"]).show() == 2:
            utils.openFile(filepath)


class EchoReader:
    _msgid: Optional[str] = None  # non-current-echo message id, navigated by ii-link
    qs: Optional[ui.QuickSearch] = None  # quick search helper
    reader: ui.ReaderWidget = None
    #
    go: bool = True  # show reader
    done: bool = False  # close app
    nextEcho: Union[str, bool] = False  # jump to next echo after reader closed
    resized: bool = False

    def __init__(self, echo: config.Echo, msgn, archive, counts,
                 mode=ui.ReaderMode.ECHO, msgids=None):
        self.echo = echo
        self.msgs = ui.MsgModeStack(mode, msgids, msgn)
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
        self.reader = ui.ReaderWidget()
        self.reader.setRect(x=0, y=5, w=ui.WIDTH, h=ui.HEIGHT - 5 - 1)
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
            return outgoing.getOutMsgsMetadata(CFG.node(), self.drafts)
        elif self.echo == config.ECHO_FIND:
            return self.msgs.data  #
        else:
            return api.getEchoMsgsMetadata(self.echo.name)

    def readCurMsg(self):  # type: () -> (List[str], int)
        self._msgid = None
        if self.out and "." in self.msgid():  # .out, .outmsg, .draft
            self.reader.setMsg(*outgoing.readOutMsg(self.msgid(), CFG.node()))
        else:
            m = self.msgs.curItem()
            if not m and self.msgs.data:
                self.msgs.idx = 0
                m = self.msgs.curItem()
            if m:
                self.reader.setMsg(*api.readMsg(self._msgid or m.msgid, m.echo))
            else:
                self.reader.setMsg(*api.readMsg("unknown", "unknown"))

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
            win = ui.SelectWindow("Выберите ссылку", list(map(
                lambda it: (it.url + " " + (it.title or "")).strip(),
                links)))
            i = win.show()
            if win.resized:
                self.reader.setRect(x=0, y=5, w=ui.WIDTH, h=ui.HEIGHT - 5 - 1)
                self.reader.prerender(self.reader.scroll.pos)
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
                self.reader.scroll.pos = pos
        elif not link.startswith("ii://"):
            if not CFG.browser.open(link):
                ui.showMessageBox("Не удалось запустить Интернет-браузер")
        else:  # ii://
            link = link[5:]
            link = link.rstrip("/")
            if "/" in link:  # support ii://echo.area/msgid123
                link = link[link.rindex("/"):]
            if parser.echoTemplate.match(link):  # echoarea
                if self.echo.name == link:
                    ui.showMessageBox("Конференция уже открыта")
                elif (link in CFG.node().echoareas
                      or link in CFG.node().archive
                      or link in CFG.node().stat):
                    self.nextEcho = link
                    self.go = False
                else:
                    ui.showMessageBox("Конференция отсутствует в БД ноды")
            elif link:
                idx = self.msgs.findMsgidIdx(link)
                if idx > -1:  # msgid in same echoarea
                    if not self.stack or self.stack[-1] != self.msgs.idx:
                        self.stack.append(self.msgs.idx)
                    self.msgs.idx = idx
                    self.readCurMsg()
                else:
                    self.reader.setMsg(*api.findMsg(link))
                    self._msgid = link
                    if not self.stack or self.stack[-1] != self.msgs.idx:
                        self.stack.append(self.msgs.idx)
                self.reader.prerender()

    @staticmethod
    def onSearchItem(sidx, p, token):
        # type: (int, re.Pattern, parser.Token) -> List
        matches = []
        for offset, line in enumerate(token.render):
            pos = 0
            while match := p.search(line, pos):
                if pos >= len(line) or match.start() == match.end():
                    break
                matches.append((offset, match))
                pos = match.end()
        if matches:
            token.searchIdx = sidx
            token.searchMatches = matches
        else:
            token.searchIdx = None
            token.searchMatches = None
        return matches

    def show(self):
        try:
            while self.go:
                self._show(self.msgs, self.reader)
        except SystemExit:
            self.go = False
            self.done = True

        if self.msgs.mode == ui.ReaderMode.ECHO:
            self.counts.lasts[self.echo.name] = self.msgs.idx
            with open("lasts.lst", "wb") as f:
                pickle.dump(self.counts.lasts, f)
        ui.stdscr.clear()
        return not self.done, self.nextEcho

    def _show(self, msgs: ui.MsgModeStack, reader: ui.ReaderWidget):
        ui.stdscr.clear()
        status = None
        if msgs.data:
            self.draw(ui.stdscr, reader)
            status = utils.msgnStatus(len(msgs.data), msgs.idx, ui.WIDTH)
        else:
            ui.drawReader(ui.stdscr, self.echo.name, "", self.out)
        ui.drawStatusBar(ui.stdscr, mode=msgs.mode, text=status)
        if self.qs:
            self.qs.draw(ui.stdscr)
        #
        ks, key, _ = ui.getKeystroke()
        #
        if key == curses.KEY_RESIZE:
            ui.setTermSize()
            self.resized = True
            reader.setRect(x=0, y=5, w=ui.WIDTH, h=ui.HEIGHT - 5 - 1)
            reader.prerender(reader.scroll.pos)
            ui.stdscr.clear()
            if self.qs:
                self.qs.items = reader.tokens
                self.qs.y = ui.HEIGHT - 1
                self.qs.width = ui.WIDTH - len(ui.version) - 13
                tnum, _ = parser.findVisibleToken(reader.tokens,
                                                  reader.scroll.pos)
                self.qs.search(self.qs.txt, tnum)
        elif self.qs:
            self.onKeyPressedQs(ks, key)
        elif ks in Qs.OPEN:
            self.qs = ui.newQuickSearch(reader.tokens, self.onSearchItem)
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
            self.onKeyPressed(ks, msgs, reader)

    def draw(self, scr, reader: ui.ReaderWidget):
        h, w = scr.getmaxyx()
        ui.drawReader(scr, reader.msg[1], self.msgid(), self.out)
        if w >= 80 and self.echo == config.ECHO_FIND:
            title = f"Найденные сообщения '{ui.FindQueryWindow.query}'"
            ui.drawTitle(scr, 0, w - 2 - len(title), title)
        elif w >= 80 and self.echo.desc:
            ui.drawTitle(scr, 0, w - 2 - len(self.echo.desc), self.echo.desc)

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
        ui.drawTitle(scr, 4, 0, strSize)
        tags = reader.msg[0].split("/")
        if "repto" in tags and 36 + len(strSize) < w:
            self.repto = tags[tags.index("repto") + 1].strip()
            ui.drawTitle(scr, 4, len(strSize) + 3, "Ответ на " + self.repto)
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

    def onKeyPressed(self, ks: str, msgs: ui.MsgModeStack, reader: ui.ReaderWidget):
        if ks in Reader.MSUBJ:
            if msgs.mode != ui.ReaderMode.SUBJ:
                data = api.findSubjMsgids(reader.msg[1], reader.msg[6])
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
                if msgs.mode == ui.ReaderMode.ECHO:
                    self.go = False
                    self.nextEcho = True
                else:
                    msgs.idx = len(msgs.data) - 1
            reader.prerender()

        elif ks in Reader.NEXT and not msgs.hasNext():
            if msgs.mode == ui.ReaderMode.ECHO:
                self.go = False
                self.nextEcho = True

        elif ks in Reader.PREP and not any((self.favorites, self.carbonarea, self.out)) and self.repto:
            idx = msgs.findMsgidIdx(self.repto)
            if idx > -1:
                self.stack.append(msgs.idx)
                msgs.idx = idx
                self.readCurMsg()
            else:
                reader.setMsg(*api.findMsg(self.repto))
                self._msgid = self.repto
                if not self.stack or self.stack[-1] != msgs.idx:
                    self.stack.append(msgs.idx)
            reader.prerender()

        elif ks in Reader.NREP and len(self.stack) > 0:
            msgs.idx = self.stack.pop()
            self.readCurMsg()
            reader.prerender()

        elif ks in Reader.UKEYS:
            if not msgs.data or reader.scroll.pos >= reader.scroll.content - reader.scroll.view:
                if not msgs.hasNext():
                    if msgs.mode == ui.ReaderMode.ECHO:
                        self.nextEcho = True
                        self.go = False
                else:
                    msgs.idx += 1
                    self.stack.clear()
                    self.readCurMsg()
                    reader.prerender()
            else:
                reader.scroll.pos += reader.scroll.view

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
            outgoing.newMsg(self.echo.name)
            callEditor(CFG.node())
            self.counts.getCounts(CFG.node(), False)

        elif ks in Reader.SAVE and not self.out:
            saveMessageToFile(self.msgid(), reader.msg[1])

        elif ks in Reader.FAVORITES and not self.out:
            saved = api.saveToFavorites(self.msgid(), reader.msg)
            ui.drawMessageBox("Подождите", False)
            self.counts.getCounts(CFG.node(), False)
            ui.showMessageBox("Сообщение добавлено в избранные" if saved else
                              "Сообщение уже есть в избранных")

        elif ks in Reader.QUOTE and not any((self.archive, self.out)) and msgs.data:
            outgoing.quoteMsg(self.msgid(), reader.msg, CFG.oldquote)
            callEditor(CFG.node())
            self.counts.getCounts(CFG.node(), False)

        elif ks in Reader.INFO:
            subj = textwrap.fill(reader.msg[6], int(ui.WIDTH * 0.75) - 8,
                                 subsequent_indent="      ")
            ui.showMessageBox("id:   %s\naddr: %s\nsubj: %s"
                              % (self.msgid(), reader.msg[4], subj))

        elif ks in Out.EDIT and self.out:
            if self.msgid().endswith(".out") or self.msgid().endswith(".draft"):
                copyfile(outgoing.directory(CFG.node()) + self.msgid(), "temp")
                callEditor(CFG.node(), self.msgid())
                self.reloadMsgsOrQuit()
            else:
                ui.showMessageBox("Сообщение уже отправлено")

        elif ks in Out.SIGN and self.out:
            self.signMsg()

        elif ks in Out.DEL and self.favorites and msgs.data:
            ui.drawMessageBox("Подождите", False)
            api.removeFromFavorites(self.msgid())
            self.counts.getCounts(CFG.node(), False)
            self.reloadMsgsOrQuit()

        elif ks in Out.DEL and self.drafts and msgs.data:
            if ui.SelectWindow("Удалить черновик '%s'?" % self.msgid(),
                               ["Нет", "Да"]).show() == 2:
                os.remove(outgoing.directory(CFG.node()) + self.msgid())
                self.counts.getCounts(CFG.node(), False)
                self.reloadMsgsOrQuit()

        elif ks in Reader.GETMSG and reader.size == 0 and self._msgid:
            try:
                ui.drawMessageBox("Подождите", False)
                getMsg(self._msgid)
                self.counts.getCounts(CFG.node(), True)
                reader.setMsg(*api.findMsg(self._msgid))
                reader.prerender()
            except Exception as ex:
                ui.showMessageBox("Не удалось определить msgid.\n" + str(ex))

        elif ks in Reader.LINKS:
            self.showOpenLinkDialog(reader.tokens)

        elif ks in Reader.TO_OUT and self.drafts:
            draft = outgoing.directory(CFG.node()) + self.msgid()
            os.rename(draft, draft.replace(".draft", ".out"))
            self.counts.getCounts(CFG.node(), False)
            self.reloadMsgsOrQuit()

        elif ks in Reader.TO_DRAFTS and self.out and not self.drafts:
            if self.msgid().endswith(".out"):
                out = outgoing.directory(CFG.node()) + self.msgid()
                os.rename(out, out.replace(".out", ".draft"))
                self.counts.getCounts(CFG.node(), False)
                self.reloadMsgsOrQuit()
            else:
                ui.showMessageBox("Сообщение уже отправлено")

        elif ks in Reader.LIST and msgs.data:
            mode = msgs.mode
            msgid = msgs.curItem().msgid
            win = ui.MsgListScreen(self.echo.name, self.msgs)
            selectedMsgn = win.show()
            msgs = win.msgs
            self.msgs = win.msgs
            if selectedMsgn == -1:
                msgs.idx = msgs.findMsgidIdx(msgid)
            if mode != msgs.mode or selectedMsgn > -1:
                self.stack.clear()
                self.readCurMsg()
                reader.prerender()
            elif win.resized:
                reader.setRect(x=0, y=5, w=ui.WIDTH, h=ui.HEIGHT - 5 - 1)
                reader.prerender(reader.scroll.pos)

        elif ks in Reader.INLINES:
            parser.INLINE_STYLE_ENABLED = not parser.INLINE_STYLE_ENABLED
            reader.prerender(reader.scroll.pos)

    def signMsg(self):
        if (not self.msgid().endswith(".out")
                and not self.msgid().endswith(".draft")):
            ui.showMessageBox("Подпись невозможна."
                              " Сообщение уже отправлено")
            return  #

        if not parser.gpg:
            ui.showMessageBox("Подпись невозможна."
                              " Не установлен пакет python-gnupg")
            return  #

        privateKeys = parser.gpg.list_keys(secret=True)
        if not privateKeys:
            ui.showMessageBox("Не удалось подписать сообщение.\n"
                              "Нет приватных ключей в хранилище:\n%s"
                              % os.path.abspath(parser.gpg.gnupghome))
            return  #

        items = []
        for k in privateKeys:
            user = k['uids'][0]
            items.append((k['keyid'], "%s (%s)" % (user, k['keyid'])))
        selected = ui.SelectWindow("Подписать ключом",
                                   [it[1] for it in items]).show()
        if selected > 0:
            signMsg(CFG.node(), self.msgid(), items[selected - 1][0])
            self.readCurMsg()
            self.reader.prerender()


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
