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
    color_pairs, get_color, UI_BORDER, UI_TEXT, UI_CURSOR
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
node = 0
cfg = config.Config()

splash = ["▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀",
          "████████ ████████ ████████ ████████ ███ ███  ███ ██████████",
          "███           ███ ███  ███ ███          ███  ███ ███ ██ ███",
          "███      ████████ ████████ ████████ ███ ███  ███ ███ ██ ███",
          "███      ███  ███ ███           ███ ███ ███  ███ ███ ██ ███",
          "████████ ████████ ████████ ████████ ███ ████████ ███ ██ ███",
          "▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄",
          "           ncurses ii/idec client        v" + __version__,
          "           Andrew Lobanov             13.02.2026",
          "           Cthulhu Fhtagn"]


#
# Взаимодействие с нодой
#
def make_toss(node_):  # type: (config.Node) -> None
    node_dir = outgoing.directory(node_)
    lst = [x for x in os.listdir(node_dir)
           if x.endswith(".out")]
    for msg in lst:
        with codecs.open(node_dir + "%s" % msg, "r", "utf-8") as f:
            text_raw = f.read()
        text_b64 = base64.b64encode(text_raw.encode("utf-8")).decode("utf-8")
        with codecs.open(node_dir + "%s.toss" % msg, "w", "utf-8") as f:
            f.write(text_b64)
        os.rename(node_dir + "%s" % msg,
                  node_dir + "%s%s" % (msg, "msg"))


def send_mail(node_):  # type: (config.Node) -> None
    node_dir = outgoing.directory(node_)
    lst = [x for x in sorted(os.listdir(node_dir))
           if x.endswith(".toss")]
    total = str(len(lst))
    try:
        for n, msg in enumerate(lst, start=1):
            print("\rОтправка сообщения: " + str(n) + "/" + total, end="")
            msg_toss = node_dir + msg
            with codecs.open(msg_toss, "r", "utf-8") as f:
                text = f.read()
            #
            result = client.send_msg(node_.url, node_.auth, text)
            #
            if result.startswith("msg ok"):
                os.remove(msg_toss)
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


def debundle(bundle, get_list=None):
    messages = []
    for msg in filter(None, bundle):
        m = msg.split(":")
        msgid = m[0]
        if len(msgid) == 20 and m[1]:
            msgbody = base64.b64decode(m[1].encode("ascii")).decode("utf8").split("\n")
            if get_list and msgid not in get_list:
                print(f"\nWARNING:"
                      f" msgid: {msgid} received but not requested: [{', '.join(get_list)}]."
                      f" Skipped. Please report to node sysop.")
            else:
                messages.append([msgid, msgbody])
    if messages:
        api.save_message(messages, node, cfg.nodes[node].to)


def get_mail(node_, force_full_idx=False):  # type: (config.Node, bool) -> None
    features = api.get_node_features(node_.nodename)
    if features is None:
        print("Запрос x/features...")
        features = client.get_features(node_.url)
        api.save_node_features(node_.nodename, features)
        print("  x/features: " + ", ".join(features))
    is_node_smart = FEAT_X_C in features and FEAT_U_E in features
    #
    echoareas = list(map(lambda e: e.name, filter(lambda e: e.sync,
                                                  node_.echoareas)))
    old_nec = None
    new_nec = None
    offsets = None
    if is_node_smart:
        old_nec = api.get_node_echo_counts(node_.nodename)
        new_nec = client.get_echo_count(node_.url, echoareas)
        offsets = utils.offsets_echo_count(old_nec or {}, new_nec)

    fetch_msg_list = []
    if is_node_smart and old_nec and not force_full_idx:
        print("Получение свежего индекса от ноды...")
        remote_msg_list = []
        grouped = {offset: [ec[0] for ec in ec]
                   for offset, ec in itertools.groupby(offsets.items(),
                                                       lambda ec: ec[1])}
        for offset, echoareas in grouped.items():
            print("  offset %s: %s" % (str(offset), ", ".join(echoareas)))
            remote_msg_list += client.get_msg_list(node_.url, echoareas, offset)
    else:
        print("Получение полного индекса от ноды...")
        remote_msg_list = client.get_msg_list(node_.url, echoareas)

    print("Построение разностного индекса...")
    local_index = None
    for line in remote_msg_list:
        if parser.echo_template.match(line):
            local_index = api.get_echo_msgids(line)
        elif len(line) == 20 and line not in local_index and line not in blacklist:
            fetch_msg_list.append(line)
    if fetch_msg_list:
        total = str(len(fetch_msg_list))
        count = 0
        for get_list in utils.separate(fetch_msg_list):
            count += len(get_list)
            print("\rПолучение сообщений: " + str(count) + "/" + total, end="")
            debundle(client.get_bundle(node_.url, "/".join(get_list)), get_list)
    else:
        print("Новых сообщений не обнаружено.", end="")
    if is_node_smart:
        api.save_node_echo_counts(node_.nodename, new_nec)
    print()


def fetch_mail(node_, force_full_idx=False):  # type: (config.Node, bool) -> None
    print("Работа с " + node_.url)
    try:
        if node_.auth:
            make_toss(node_)
            send_mail(node_)
        get_mail(node_, force_full_idx)
    except KeyboardInterrupt:
        print("\nПрервано пользователем")
    except Exception as ex:
        print("\nОШИБКА: " + str(ex))
        print(traceback.format_exc())
    input("Нажмите Enter для продолжения.")


#
# Пользовательский интерфейс
#
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

    def get_counts(self, node_, new=False):
        for echo in node_.echoareas:  # type: config.Echo
            if new or echo.name not in self.total:
                self.total[echo.name] = api.get_echo_length(echo.name)
        for echo in node_.archive:  # type: config.Echo
            if echo.name not in self.total:
                self.total[echo.name] = api.get_echo_length(echo.name)
        self.total[config.ECHO_CARBON.name] = len(api.get_carbonarea())
        self.total[config.ECHO_FAVORITES.name] = len(api.get_favorites_list())

    def rescan_counts(self, echoareas):
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

    def find_new(self, cursor):
        for n, (_, unread) in enumerate(self.counts):
            if n >= cursor and int(unread) > 0:
                return n
        return cursor


def edit_config():
    ui.terminate_curses()
    p = subprocess.Popen(cfg.editor + " " + config.CONFIG_FILEPATH, shell=True)
    p.wait()
    global node
    node = 0
    cfg.load()
    ui.initialize_curses()


class EchoSelectorScreen:
    echo_cursor: int = 0
    archive_cursor: int = 0
    next_echo: bool = False
    echos: ui.EchoModeStack = None
    scroll: ui.ScrollCalc = None
    qs: Optional[ui.QuickSearch] = None
    go: bool = True

    def __init__(self):
        self.counts = Counts()
        self.reload_echoareas()

    def reload_echoareas(self):
        self.echo_cursor = 0
        self.archive_cursor = 0
        self.echos = ui.EchoModeStack(ui.SelectorMode.ECHO,
                                      cfg.nodes[node].echoareas)
        ui.draw_message_box("Подождите", False)
        self.counts.get_counts(cfg.nodes[node], False)
        ui.stdscr.clear()
        self.updateScroll()

    def updateScroll(self):
        self.scroll = ui.ScrollCalc(len(self.echos.data), ui.HEIGHT - 2)
        self.scroll.ensure_visible(self.echos.idx, center=True)
        self.counts.rescan_counts(self.echos.data)

    def toggle_archive(self):
        if not self.echos.isArch() and cfg.nodes[node].archive:
            self.echo_cursor = self.echos.idx
            self.echos.modeArchOn(cfg.nodes[node].archive)
            self.echos.idx = self.archive_cursor
        elif self.echos.isArch():
            self.archive_cursor = self.echos.idx
            self.echos.modeArchOff()
            self.echos.idx = self.echo_cursor
        ui.stdscr.clear()
        self.updateScroll()

    # noinspection PyUnusedLocal
    @staticmethod
    def on_search_item(sidx, pattern, echo):
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
            self.scroll.ensure_visible(self.echos.idx)
            self.draw(ui.stdscr, self.echos.idx, self.scroll, self.qs)
            #
            ks, key, _ = ui.get_keystroke()
            #
            if key == curses.KEY_RESIZE:
                ui.set_term_size()
                self.onResize()
            elif self.qs:
                if ks in Qs.CLOSE or ks in Qs.APPLY:
                    if ks in Qs.APPLY and self.qs.result:
                        self.echos.modeQsOn(self.qs.result)
                        self.updateScroll()
                    self.qs = None
                    curses.curs_set(0)
                else:
                    self.qs.on_key_pressed_search(key, ks, self.scroll)
                    self.echos.idx = self.qs.ensure_cursor_visible(
                        key, self.echos.idx, self.scroll)
            elif ks in Qs.OPEN:
                self.qs = ui.newQuickSearch(self.echos.data, self.on_search_item)
            elif ks in Reader.QUIT and self.echos.stack:
                self.echos.pop()
                self.updateScroll()
            elif ks in Common.QUIT:
                self.go = False
            else:
                self.on_key_pressed(ks)

    def draw(self, win, cursor, scroll, qs):
        h, w = win.getmaxyx()
        self.draw_echo_selector(win, scroll.pos, cursor, qs, self.counts.counts)
        if scroll.is_scrollable:
            ui.draw_scrollbarV(win, 1, w - 1, scroll)
        if qs:
            qs.draw(win)
        win.refresh()

    def draw_echo_selector(self, win, start, cursor, qs, counts):
        # type: (curses.window, int, int, ui.QuickSearch, List[List[str]]) -> None
        h, w = win.getmaxyx()
        color = get_color(UI_BORDER)
        win.addstr(0, 0, "─" * w, color)
        if self.echos.isArch():
            ui.draw_title(win, 0, 0, "Архив")
        else:
            ui.draw_title(win, 0, 0, "Конференция")
        #
        m = min(w - 38, max(map(lambda e: len(e.desc), self.echos.data)))
        count = "Сообщений"
        unread = "Не прочитано"
        description = "Описание"
        show_desc = (w >= 80) and m > 0
        if w < 80 or m == 0:
            m = len(unread) - 7
        ui.draw_title(win, 0, w + 2 - m - len(count) - len(unread) - 1, count)
        ui.draw_title(win, 0, w - 8 - m - 1, unread)
        if show_desc:
            ui.draw_title(win, 0, w - len(description) - 2, description)

        for y in range(1, h - 1):
            echoN = y - 1 + start
            if echoN == cursor:
                color = get_color(UI_CURSOR)
            else:
                color = get_color(UI_TEXT)
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
            if show_desc:
                win.addstr(y, max(w - m - 1, w - 1 - len(echo.desc)),
                           echo.desc[0:w - 38])
            #
            if qs and echoN in qs.result:
                idx = qs.result.index(echoN)
                for match in qs.matches[idx]:
                    win.addstr(y, 2 + match.start(),
                               echo.name[match.start():match.end()],
                               color | curses.A_REVERSE)

        ui.draw_status_bar(win, mode=self.echos.mode, text=cfg.nodes[node].nodename)

    def on_key_pressed(self, ks):
        global node
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
            page_bottom = self.scroll.pos_bottom()
            if self.echos.idx < page_bottom:
                self.echos.idx = page_bottom
            else:
                self.echos.idx = min(self.scroll.content - 1,
                                     page_bottom + self.scroll.view)
        elif ks in Selector.HOME:
            self.echos.idx = 0
        elif ks in Selector.END:
            self.echos.idx = self.scroll.content - 1
        elif ks in Selector.GET or ks in Selector.FGET:
            self.fetch_mail(force_full_idx=(ks in Selector.FGET))
        elif ks in Selector.ARCHIVE and len(cfg.nodes[node].archive) > 0:
            self.toggle_archive()
        elif ks in Selector.ENTER:
            self.read_echo()
        elif ks in Selector.OUT:
            self.read_outgoing()
        elif ks in Selector.DRAFTS:
            self.read_drafts()
        elif ks in Selector.NNODE:
            node = node + 1
            if node == len(cfg.nodes):
                node = 0
            self.reload_echoareas()
        elif ks in Selector.PNODE:
            node = node - 1
            if node == -1:
                node = len(cfg.nodes) - 1
            self.reload_echoareas()
        elif ks in Selector.CONFIG:
            edit_config()
            ui.load_theme(cfg)
            load_keys()
            node = 0
            self.reload_echoareas()
        elif ks in Selector.FIND:
            win = ui.FindQueryWindow(cfg=cfg)
            find_result = win.show()
            if win.resized:
                self.onResize()
            if find_result:
                find_result = sorted(find_result, key=lambda m: m.time)
                self.showReader(EchoReader(
                    config.ECHO_FIND, 0, True, self.counts,
                    mode=ui.ReaderMode.FIND, msgids=find_result))

    def fetch_mail(self, force_full_idx):
        ui.terminate_curses()
        os.system('cls' if os.name == 'nt' else 'clear')
        fetch_mail(cfg.nodes[node], force_full_idx)
        ui.initialize_curses()
        ui.draw_message_box("Подождите", False)
        self.counts.get_counts(cfg.nodes[node], True)
        self.counts.rescan_counts(self.echos.data)
        ui.stdscr.clear()
        self.echos.idx = self.counts.find_new(0)

    def read_echo(self):
        ui.draw_message_box("Подождите", False)
        last = 0
        cur_echo = self.echos.curItem()
        if cur_echo.name in self.counts.lasts:
            last = self.counts.lasts[cur_echo.name]
        last = min(self.counts.total[cur_echo.name], last + 1)
        self.showReader(EchoReader(
            cur_echo, last, self.echos.isArch(), self.counts))
        self.counts.rescan_counts(self.echos.data)
        if self.next_echo and isinstance(self.next_echo, bool):
            self.echos.idx = self.counts.find_new(self.echos.idx)
            self.next_echo = False
        elif self.next_echo and isinstance(self.next_echo, str):
            cur_node = cfg.nodes[node]
            if ((not self.echos.isArch() and self.next_echo in cur_node.archive)
                    or (self.echos.isArch() and (self.next_echo in cur_node.echoareas
                                                 or self.next_echo in cur_node.stat))):
                self.toggle_archive()
            # noinspection PyTypeChecker
            self.echos.idx = self.echos.findItemIdx(self.next_echo)
            if self.echos.idx == -1:
                self.echos.idx = 0
            self.next_echo = False

    def read_outgoing(self):
        out_length = outgoing.get_out_length(cfg.nodes[node], drafts=False)
        if out_length:
            self.showReader(EchoReader(
                config.ECHO_OUT, out_length, self.echos.isArch(), self.counts))

    def read_drafts(self):
        out_length = outgoing.get_out_length(cfg.nodes[node], drafts=True)
        if out_length:
            self.showReader(EchoReader(
                config.ECHO_DRAFTS, 0, self.echos.isArch(), self.counts))

    def showReader(self, reader):
        self.go, self.next_echo = reader.show()
        if reader.resized:
            self.onResize()

    def onResize(self):
        self.scroll = ui.ScrollCalc(len(self.echos.data), ui.HEIGHT - 2,
                                    self.echos.idx)
        ui.stdscr.clear()
        if self.qs:
            self.qs.y = ui.HEIGHT - 1
            self.qs.width = ui.WIDTH - len(ui.version) - 13


def call_editor(node_, out=''):
    ui.terminate_curses()
    h = hashlib.sha1(str.encode(open("temp", "r", ).read())).hexdigest()
    p = subprocess.Popen(cfg.editor + " ./temp", shell=True)
    p.wait()
    ui.initialize_curses()
    if h != hashlib.sha1(str.encode(open("temp", "r", ).read())).hexdigest():
        if not out:
            filepath = outgoing.outcount(node_) + ".draft"
        else:
            filepath = outgoing.directory(node_) + out
        outgoing.save_out(filepath)
    else:
        os.remove("temp")


def sign_msg(node_, out, key_id):
    node_dir = outgoing.directory(node_)
    with open(node_dir + out, "r") as f:
        msg = f.read().split("\n")
    if msg[4].startswith("@repto"):
        header = "\n".join(msg[0:5])
        body = "\n".join(msg[5:])
    else:
        header = "\n".join(msg[0:4])
        body = "\n".join(msg[4:])
    result = parser.gpg.sign(body.encode("utf-8"), keyid=key_id, clearsign=True)
    if result.returncode == 0:
        signed_body = str(result.data, encoding="utf-8")
        if len(signed_body) > len(body):
            with open(node_dir + out, "w") as f:
                f.write(header)
                f.write("\n")
                f.write(signed_body)
    else:
        ui.show_message_box(result.stderr)


def save_message_to_file(msgid, echoarea):
    msg, size = api.read_msg(msgid, echoarea)
    filepath = "downloads/" + msgid + ".txt"
    with open(filepath, "w") as f:
        f.write("== " + msg[1] + " ==================== " + msgid + "\n")
        f.write("От:   " + msg[3] + " (" + msg[4] + ")\n")
        f.write("Кому: " + msg[5] + "\n")
        f.write("Тема: " + msg[6] + "\n")
        f.write("\n".join(msg[7:]))
    ui.show_message_box("Сообщение сохранено в файл\n" + filepath)


def get_msg(msgid):
    node_ = cfg.nodes[node]
    bundle = client.get_bundle(node_.url, msgid)
    for msg in filter(None, bundle):
        m = msg.split(":")
        msgid = m[0]
        if len(msgid) == 20 and m[1]:
            msgbody = base64.b64decode(m[1].encode("ascii")).decode("utf8").split("\n")
            if node_.to:
                carbonarea = api.get_carbonarea()
                if msgbody[5] in node_.to and msgid not in carbonarea:
                    api.add_to_carbonarea(msgid, msgbody)
            api.save_message([(msgid, msgbody)], node_, node_.to)


def save_attachment(token):  # type: (parser.Token) -> None
    filepath = "downloads/" + token.filename
    with open(filepath, "wb") as attachment:
        attachment.write(token.filedata)
    ui.draw_message_box("Файл сохранён '%s'" % filepath, True)
    ui.stdscr.getch()
    if token.pgp_key and parser.gpg:
        option = ui.SelectWindow("PGP Ключ '%s'" % token.filename,
                                 ["Отмена",
                                  "Открыть файл",
                                  "Добавить в хранилище"]).show()
        if option == 2:
            utils.open_file(filepath)
        elif option == 3:
            result = parser.gpg.import_keys_file(filepath)
            smsg = "\n".join(map(lambda rd: json.dumps(rd, sort_keys=True, indent=2),
                                 filter(lambda r: r['fingerprint'], result.results)))
            ui.show_message_box(smsg)
    else:
        if ui.SelectWindow("Открыть '%s'?" % token.filename,
                           ["Нет", "Да"]).show() == 2:
            utils.open_file(filepath)


class EchoReader:
    _msgid: Optional[str] = None  # non-current-echo message id, navigated by ii-link
    qs: Optional[ui.QuickSearch] = None  # quick search helper
    reader: ui.ReaderWidget = None
    #
    go: bool = True  # show reader
    done: bool = False  # close app
    next_echo: Union[str, bool] = False  # jump to next echo after reader closed
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
        self.cur_node = cfg.nodes[node]  # type: config.Node
        self.repto = ""
        self.stack = []
        if not msgids:
            self.msgs.data = self.get_msgs_metadata()
        else:
            self.msgs.data = msgids
        #
        self.reader = ui.ReaderWidget()
        self.reader.setRect(x=0, y=5, w=ui.WIDTH, h=ui.HEIGHT - 5 - 1)
        #
        self.msgs.idx = min(msgn, len(self.msgs.data) - 1)
        if self.msgs.data:
            self.read_msg_skip_twit(-1)
            if self.msgs.idx < 0:
                self.next_echo = True
        self.reader.prerender()

    def msgid(self):
        m = self.msgs.curItem()
        return self._msgid or (m.msgid if m else "")

    def get_msgs_metadata(self):
        if self.out:
            return outgoing.get_out_msgs_metadata(self.cur_node, self.drafts)
        elif self.echo == config.ECHO_FIND:
            return self.msgs.data  #
        else:
            return api.get_echo_msgs_metadata(self.echo.name)

    def read_cur_msg(self):  # type: () -> (List[str], int)
        self._msgid = None
        if self.out and "." in self.msgid():  # .out, .outmsg, .draft
            self.reader.setMsg(*outgoing.read_out_msg(self.msgid(), self.cur_node))
        else:
            m = self.msgs.curItem()
            if not m and self.msgs.data:
                self.msgs.idx = 0
                m = self.msgs.curItem()
            if m:
                self.reader.setMsg(*api.read_msg(self._msgid or m.msgid, m.echo))
            else:
                self.reader.setMsg(*api.read_msg("unknown", "unknown"))

    def read_msg_skip_twit(self, increment):
        self.read_cur_msg()
        while self.reader.msg[3] in cfg.twit or self.reader.msg[5] in cfg.twit:
            self.msgs.idx += increment
            if self.msgs.idx < 0 or len(self.msgs.data) <= self.msgs.idx:
                break
            self.read_cur_msg()

    def reload_msgs_or_quit(self):
        self.msgs.data = self.get_msgs_metadata()
        if self.msgs.data:
            if self.msgs.stack:
                self.msgs.mode = self.msgs.stack[0][0]
                self.msgs.stack.clear()
            self.msgs.idx = min(self.msgs.idx, len(self.msgs.data) - 1)
            self.read_cur_msg()
            self.reader.prerender()
        else:
            self.go = False

    def show_open_link_dialog(self, tokens):
        links = list(filter(lambda it: it.type == parser.TT.URL, tokens))
        if len(links) == 1:
            self.open_link(links[0])
        elif links:
            win = ui.SelectWindow("Выберите ссылку", list(map(
                lambda it: (it.url + " " + (it.title or "")).strip(),
                links)))
            i = win.show()
            if win.resized:
                self.reader.setRect(x=0, y=5, w=ui.WIDTH, h=ui.HEIGHT - 5 - 1)
                self.reader.prerender(self.reader.scroll.pos)
            if i:
                self.open_link(links[i - 1])

    def open_link(self, token):  # type: (parser.Token) -> None
        link = token.url
        if token.filename:
            if token.filedata:
                save_attachment(token)
        elif link.startswith("#"):  # markdown anchor?
            pos = parser.find_pos_by_anchor(self.reader.tokens, token)
            if pos != -1:
                self.reader.scroll.pos = pos
        elif not link.startswith("ii://"):
            if not cfg.browser.open(link):
                ui.show_message_box("Не удалось запустить Интернет-браузер")
        else:  # ii://
            link = link[5:]
            link = link.rstrip("/")
            if "/" in link:  # support ii://echo.area/msgid123
                link = link[link.rindex("/"):]
            if parser.echo_template.match(link):  # echoarea
                if self.echo.name == link:
                    ui.show_message_box("Конференция уже открыта")
                elif (link in self.cur_node.echoareas
                      or link in self.cur_node.archive
                      or link in self.cur_node.stat):
                    self.next_echo = link
                    self.go = False
                else:
                    ui.show_message_box("Конференция отсутствует в БД ноды")
            elif link:
                idx = self.msgs.findMsgidIdx(link)
                if idx > -1:  # msgid in same echoarea
                    if not self.stack or self.stack[-1] != self.msgs.idx:
                        self.stack.append(self.msgs.idx)
                    self.msgs.idx = idx
                    self.read_cur_msg()
                else:
                    self.reader.setMsg(*api.find_msg(link))
                    self._msgid = link
                    if not self.stack or self.stack[-1] != self.msgs.idx:
                        self.stack.append(self.msgs.idx)
                self.reader.prerender()

    @staticmethod
    def on_search_item(sidx, p, token):
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
            token.search_idx = sidx
            token.search_matches = matches
        else:
            token.search_idx = None
            token.search_matches = None
        return matches

    def show(self):
        try:
            while self.go:
                self._show()
        except SystemExit:
            self.go = False
            self.done = True

        if self.msgs.mode == ui.ReaderMode.ECHO:
            self.counts.lasts[self.echo.name] = self.msgs.idx
            with open("lasts.lst", "wb") as f:
                pickle.dump(self.counts.lasts, f)
        ui.stdscr.clear()
        return not self.done, self.next_echo

    def _show(self):
        ui.stdscr.clear()
        status = None
        if self.msgs.data:
            self.draw(ui.stdscr)
            status = utils.msgn_status(len(self.msgs.data), self.msgs.idx, ui.WIDTH)
        else:
            ui.draw_reader(ui.stdscr, self.echo.name, "", self.out)
        ui.draw_status_bar(ui.stdscr, mode=self.msgs.mode, text=status)
        if self.qs:
            self.qs.draw(ui.stdscr)
        #
        ks, key, _ = ui.get_keystroke()
        #
        if key == curses.KEY_RESIZE:
            ui.set_term_size()
            self.resized = True
            self.reader.setRect(x=0, y=5, w=ui.WIDTH, h=ui.HEIGHT - 5 - 1)
            self.reader.prerender(self.reader.scroll.pos)
            ui.stdscr.clear()
            if self.qs:
                self.qs.items = self.reader.tokens
                self.qs.y = ui.HEIGHT - 1
                self.qs.width = ui.WIDTH - len(ui.version) - 13
                tnum, _ = parser.find_visible_token(self.reader.tokens,
                                                    self.reader.scroll.pos)
                self.qs.search(self.qs.txt, tnum)
        elif self.qs:
            self.on_key_pressed_qs(ks, key)
        elif ks in Qs.OPEN:
            self.qs = ui.newQuickSearch(self.reader.tokens, self.on_search_item)
        elif ks in Reader.QUIT:
            if self.msgs.stack:
                self.mode_restore()
            else:
                self.go = False
                self.next_echo = False
        elif ks in Common.QUIT:
            self.go = False
            self.done = True
        elif self.reader.on_key_pressed(ks, key):
            return  #
        else:
            self.on_key_pressed(ks, key)

    def draw(self, scr):
        h, w = scr.getmaxyx()
        ui.draw_reader(scr, self.reader.msg[1], self.msgid(), self.out)
        if w >= 80 and self.echo == config.ECHO_FIND:
            title = f"Найденные сообщения '{ui.FindQueryWindow.query}'"
            ui.draw_title(scr, 0, w - 2 - len(title), title)
        elif w >= 80 and self.echo.desc:
            ui.draw_title(scr, 0, w - 2 - len(self.echo.desc), self.echo.desc)

        color = get_color(UI_TEXT)
        if not self.out:
            if w >= 80:
                scr.addstr(1, 7, self.reader.msg[3] + " (" + self.reader.msg[4] + ")", color)
            else:
                scr.addstr(1, 7, self.reader.msg[3], color)
            msgtime = utils.msg_strftime(self.reader.msg[2], w)
            scr.addstr(1, w - len(msgtime) - 1, msgtime, color)
        elif self.cur_node.to:
            scr.addstr(1, 7, self.cur_node.to[0], color)
        scr.addstr(2, 7, self.reader.msg[5], color)
        scr.addstr(3, 7, self.reader.msg[6][:w - 8], color)
        s_size = utils.msg_strfsize(self.reader.size)
        ui.draw_title(scr, 4, 0, s_size)
        tags = self.reader.msg[0].split("/")
        if "repto" in tags and 36 + len(s_size) < w:
            self.repto = tags[tags.index("repto") + 1].strip()
            ui.draw_title(scr, 4, len(s_size) + 3, "Ответ на " + self.repto)
        else:
            self.repto = ""
        self.reader.draw(scr, self.qs)

    def on_key_pressed_qs(self, ks, key):
        if ks in Qs.CLOSE or ks in Qs.APPLY:
            self.qs = None
            curses.curs_set(0)
            return
        #
        self.qs.on_key_pressed_search(key, ks, self.reader.qsPager())
        if self.qs.result:
            tidx = self.qs.result[self.qs.idx]
            off, _ = self.qs.matches[self.qs.idx]
            self.reader.ensureVisibleOnQsKey(ks, tidx, off)

    def mode_restore(self):
        m = self.msgs.curItem()
        msgid = m.msgid if m else ""
        self.msgs.pop()
        if msgid != self.msgs.curItem().msgid:
            self.stack.clear()
            self.read_cur_msg()
            self.reader.prerender()

    # noinspection PyUnusedLocal
    def on_key_pressed(self, ks, key):
        if ks in Reader.MSUBJ:
            if self.msgs.mode != ui.ReaderMode.SUBJ:
                data = api.find_subj_msgids(self.reader.msg[1], self.reader.msg[6])
                self.msgs.modeSubjOn(data)
                if self.msgs.data and self.msgs.idx == -1:
                    self.msgs.idx = 0
            else:
                self.msgs.modeSubjOff()
            self.stack.clear()
            self.read_cur_msg()
            self.reader.prerender()
        elif ks in Reader.PREV and self.msgs.idx > 0 and self.msgs.data:
            self.msgs.idx -= 1
            self.stack.clear()
            tmp = self.msgs.idx
            self.read_msg_skip_twit(-1)
            if self.msgs.idx < 0:
                self.msgs.idx = tmp + 1
            self.reader.prerender()
        elif ks in Reader.NEXT and self.msgs.hasNext():
            self.msgs.idx += 1
            self.stack.clear()
            self.read_msg_skip_twit(+1)
            if self.msgs.idx >= len(self.msgs.data):
                if self.msgs.mode == ui.ReaderMode.ECHO:
                    self.go = False
                    self.next_echo = True
                else:
                    self.msgs.idx = len(self.msgs.data) - 1
            self.reader.prerender()
        elif ks in Reader.NEXT and not self.msgs.hasNext():
            if self.msgs.mode == ui.ReaderMode.ECHO:
                self.go = False
                self.next_echo = True
        elif ks in Reader.PREP and not any((self.favorites, self.carbonarea, self.out)) and self.repto:
            idx = self.msgs.findMsgidIdx(self.repto)
            if idx > -1:
                self.stack.append(self.msgs.idx)
                self.msgs.idx = idx
                self.read_cur_msg()
            else:
                self.reader.setMsg(*api.find_msg(self.repto))
                self._msgid = self.repto
                if not self.stack or self.stack[-1] != self.msgs.idx:
                    self.stack.append(self.msgs.idx)
            self.reader.prerender()
        elif ks in Reader.NREP and len(self.stack) > 0:
            self.msgs.idx = self.stack.pop()
            self.read_cur_msg()
            self.reader.prerender()
        elif ks in Reader.UKEYS:
            if not self.msgs.data or self.reader.scroll.pos >= self.reader.scroll.content - self.reader.scroll.view:
                if not self.msgs.hasNext():
                    if self.msgs.mode == ui.ReaderMode.ECHO:
                        self.next_echo = True
                        self.go = False
                else:
                    self.msgs.idx += 1
                    self.stack.clear()
                    self.read_cur_msg()
                    self.reader.prerender()
            else:
                self.reader.scroll.pos += self.reader.scroll.view
        elif ks in Reader.BEGIN and self.msgs.data:
            self.msgs.idx = 0
            self.stack.clear()
            self.read_cur_msg()
            self.reader.prerender()
        elif ks in Reader.END and self.msgs.data:
            self.msgs.idx = len(self.msgs.data) - 1
            self.stack.clear()
            self.read_cur_msg()
            self.reader.prerender()
        elif ks in Reader.INS and not any((self.archive, self.out, self.favorites, self.carbonarea)):
            outgoing.new_msg(self.echo.name)
            call_editor(self.cur_node)
        elif ks in Reader.SAVE and not self.out:
            save_message_to_file(self.msgid(), self.reader.msg[1])
        elif ks in Reader.FAVORITES and not self.out:
            saved = api.save_to_favorites(self.msgid(), self.reader.msg)
            ui.draw_message_box("Подождите", False)
            self.counts.get_counts(self.cur_node, False)
            ui.show_message_box("Сообщение добавлено в избранные" if saved else
                                "Сообщение уже есть в избранных")
        elif ks in Reader.QUOTE and not any((self.archive, self.out)) and self.msgs.data:
            outgoing.quote_msg(self.msgid(), self.reader.msg, cfg.oldquote)
            call_editor(self.cur_node)
        elif ks in Reader.INFO:
            subj = textwrap.fill(self.reader.msg[6], int(ui.WIDTH * 0.75) - 8,
                                 subsequent_indent="      ")
            ui.show_message_box("id:   %s\naddr: %s\nsubj: %s"
                                % (self.msgid(), self.reader.msg[4], subj))
        elif ks in Out.EDIT and self.out:
            if self.msgid().endswith(".out") or self.msgid().endswith(".draft"):
                copyfile(outgoing.directory(self.cur_node) + self.msgid(), "temp")
                call_editor(self.cur_node, self.msgid())
                self.reload_msgs_or_quit()
            else:
                ui.show_message_box("Сообщение уже отправлено")
        elif ks in Out.SIGN and self.out:
            self.sign_msg()
        elif ks in Out.DEL and self.favorites and self.msgs.data:
            ui.draw_message_box("Подождите", False)
            api.remove_from_favorites(self.msgid())
            self.counts.get_counts(self.cur_node, False)
            self.reload_msgs_or_quit()
        elif ks in Out.DEL and self.drafts and self.msgs.data:
            if ui.SelectWindow("Удалить черновик '%s'?" % self.msgid(),
                               ["Нет", "Да"]).show() == 2:
                os.remove(outgoing.directory(self.cur_node) + self.msgid())
                self.reload_msgs_or_quit()
        elif ks in Reader.GETMSG and self.reader.size == 0 and self._msgid:
            try:
                ui.draw_message_box("Подождите", False)
                get_msg(self._msgid)
                self.counts.get_counts(self.cur_node, True)
                self.reader.setMsg(*api.find_msg(self._msgid))
                self.reader.prerender()
            except Exception as ex:
                ui.show_message_box("Не удалось определить msgid.\n" + str(ex))
        elif ks in Reader.LINKS:
            self.show_open_link_dialog(self.reader.tokens)
        elif ks in Reader.TO_OUT and self.drafts:
            draft_msg = outgoing.directory(self.cur_node) + self.msgid()
            os.rename(draft_msg, draft_msg.replace(".draft", ".out"))
            self.reload_msgs_or_quit()
        elif ks in Reader.TO_DRAFTS and self.out and not self.drafts:
            if not self.msgid().endswith(".out"):
                out_msg = outgoing.directory(self.cur_node) + self.msgid()
                os.rename(out_msg, out_msg.replace(".out", ".draft"))
                self.reload_msgs_or_quit()
            else:
                ui.show_message_box("Сообщение уже отправлено")
        elif ks in Reader.LIST and self.msgs.data:
            mode = self.msgs.mode
            msgid = self.msgs.curItem().msgid
            win = ui.MsgListScreen(self.echo.name, self.msgs)
            selected_msgn = win.show()
            self.msgs = win.msgs
            if selected_msgn == -1:
                self.msgs.idx = self.msgs.findMsgidIdx(msgid)
            if mode != self.msgs.mode or selected_msgn > -1:
                self.stack.clear()
                self.read_cur_msg()
                self.reader.prerender()
            elif win.resized:
                self.reader.setRect(x=0, y=5, w=ui.WIDTH, h=ui.HEIGHT - 5 - 1)
                self.reader.prerender(self.reader.scroll.pos)
        elif ks in Reader.INLINES:
            parser.INLINE_STYLE_ENABLED = not parser.INLINE_STYLE_ENABLED
            self.reader.prerender(self.reader.scroll.pos)

    def sign_msg(self):
        if (not self.msgid().endswith(".out")
                and not self.msgid().endswith(".draft")):
            ui.show_message_box("Сообщение уже отправлено")
            return  #

        private_keys = parser.gpg.list_keys(secret=True)
        if private_keys:
            items = []
            for k in private_keys:
                user = k['uids'][0]
                items.append((k['keyid'], "%s (%s)" % (user, k['keyid'])))
            selected = ui.SelectWindow("Подписать ключом",
                                       [it[1] for it in items]).show()
            if selected > 0:
                sign_msg(self.cur_node, self.msgid(), items[selected - 1][0])
                self.read_cur_msg()
                self.reader.prerender()
        else:
            ui.show_message_box("Не удалось подписать сообщение.\n"
                                "Нет приватных ключей в хранилище:\n%s"
                                % os.path.abspath(parser.gpg.gnupghome))


if sys.version_info >= (3, 11):
    loc = locale.getlocale()
else:
    # noinspection PyDeprecation
    loc = locale.getdefaultlocale()
locale.setlocale(locale.LC_ALL, loc[0] + "." + loc[1])

config.ensure_exists()
cfg.load()
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
# create directories
api.init()
ui.api = api
if not os.path.exists("downloads"):
    os.mkdir("downloads")
outgoing.init(cfg)


def load_keys():
    if cfg.keys == "default":
        # noinspection PyUnresolvedReferences
        import keys.default as keys
    elif cfg.keys == "android":
        # noinspection PyUnresolvedReferences
        import keys.android as keys
    elif cfg.keys == "vi":
        # noinspection PyUnresolvedReferences
        import keys.vi as keys
    else:
        raise Exception("Unknown Keys Scheme :: " + cfg.keys)
    keystroke.KsSeq.init_sequences()


load_keys()
try:
    ui.initialize_curses()
    ui.load_theme(cfg)
    ui.stdscr.bkgd(" ", curses.color_pair(color_pairs[UI_TEXT][0]))  # wo attrs

    if cfg.splash:
        ui.draw_splash(ui.stdscr, splash)
        curses.napms(2000)
        ui.stdscr.clear()
    EchoSelectorScreen().show()
finally:
    ui.terminate_curses()
