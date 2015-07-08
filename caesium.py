#!/usr/bin/env python3

import curses, os, urllib.request, base64, codecs
from datetime import datetime

node = ""
auth = ""
echoes = []

def check_directories():
    if not os.path.exists("echo"):
        os.mkdir("echo")
    if not os.path.exists("msg"):
        os.mkdir("msg")
    if not os.path.exists("out"):
        os.mkdir("out")

#
# Взаимодействие с нодой
#

def separate(l, step=20):
    for x in range(0, len(l), step):
        yield l[x:x+step]
        
def load_config():
    global node, auth, echoes
    f = open("caesium.cfg", "r")
    config = f.read().split("\n")
    f.close()
    for line in config:
        param = line.split(" ")
        if param[0] == "node":
            node = param[1]
        elif param[0] == "auth":
            auth = param[1]
        elif param[0] == "echo":
            if len(param) > 2:
                echoes.append([param[1], " ".join(param[2:])])
            else:
                echoes.append([param[1], ""])

def get_msg_list(echo):
    msg_list = []
    r = urllib.request.Request(node + "u/e/" + echo[0])
    with urllib.request.urlopen(r) as f:
        lines = f.read().decode("utf-8").split("\n")
        for line in lines:
            if line != echo:
                msg_list.append(line)
    return msg_list

def get_local_msg_list(echo):
    if not os.path.exists("echo/" + echo[0]):
        return []
    else:
        local_msg_list = codecs.open("echo/" + echo[0], "r", "utf-8").read().split("\n")
        return local_msg_list

def get_bundle(msgids):
    bundle = []
    r = urllib.request.Request(node + "u/m/" + msgids)
    with urllib.request.urlopen(r) as f:
        bundle = f.read().decode("utf-8").split("\n")
    return bundle

def debundle(echo, bundle):
    for msg in bundle:
        if msg:
            m = msg.split(":")
            msgid = m[0]
            if len(msgid) == 20 and m[1]:
                codecs.open("msg/" + msgid, "w", "utf-8").write(base64.b64decode(m[1]).decode("utf-8"))
                codecs.open("echo/" + echo[0], "a", "utf-8").write(msgid + "\n")

def fetch_mail():
    stdscr.clear()
    stdscr.attron(curses.color_pair(1))
    stdscr.attron(curses.A_BOLD)
    stdscr.border()
    draw_title(0, 1, "Получение почты")
    log = curses.newwin(height - 2, width - 2, 1, 1)
    log.scrollok(True)
    line = -1
    for echo in echoes:
        if line < height - 3:
            line = line + 1
        else:
            log.scroll()
        remote_msg_list = get_msg_list(echo)
        if len(remote_msg_list) > 1:
            local_msg_list = get_local_msg_list(echo)
            msg_list = [x for x in remote_msg_list if x not in local_msg_list]
            list_len = len (msg_list)
            n = 0
            for get_list in separate(msg_list):
                debundle(echo, get_bundle("/".join(get_list)))
                n = n + len(get_list)
                time()
                log.addstr(line, 1, "Загрузка " + echo[0] + ": " + str(n) + "/" + str(list_len), curses.color_pair(4))
                log.refresh()
        else:
            codecs.open("echo/" + echo, "a", "utf-8").close()
    stdscr.clear()

#
# Пользовательский интерфейс
#

echo_cursor = 0

def get_term_size():
    global width, height
    height, width = stdscr.getmaxyx()

def draw_title(y, x, title):
    stdscr.addstr(y, x, "[", curses.color_pair(1) + curses.A_BOLD)
    stdscr.addstr(y, x + 1, " " + title + " ", curses.color_pair(2) + curses.A_BOLD)
    stdscr.addstr(y, x + 3 + len(title), "]", curses.color_pair(1) + curses.A_BOLD)

def draw_cursor(y, color):
    for i in range (1, width - 1):
        stdscr.addstr(y + 1, i, " ", color)

def time():
    draw_title (height - 1, width - 10, datetime.now().strftime("%H:%M"))

def draw_echo_selector(start):
    stdscr.attron(curses.color_pair(1))
    stdscr.attron(curses.A_BOLD)
    stdscr.border()
    draw_title(0, 1, "Выбор эхоконференции")
    y = 0
    for echo in echoes:
        if y - start < height - 2:
            if y == echo_cursor:
                if y >= start:
                    draw_cursor(y - start, curses.color_pair(3))
                stdscr.attron (curses.color_pair(3) + curses.A_BOLD)
            else:
                if y >= start:
                    draw_cursor(y - start, curses.color_pair(4))
                stdscr.attron (curses.color_pair(4))
                stdscr.attroff (curses.A_BOLD)
            if y + 1 >= start + 1:
                stdscr.addstr(y + 1 - start, 2, echo[0])
                if width - 26 >= len(echo[1]):
                    stdscr.addstr(y + 1 - start, 25, echo[1])
                else:
                    cut_index = width - 26 - len(echo[1])
                    stdscr.addstr(y + 1 - start, 25, echo[1][:cut_index])
        y = y + 1
    time()
    stdscr.refresh()

def echo_selector():
    global echo_cursor
    key = 0
    start = 0
    while not key == curses.KEY_F10:
        draw_echo_selector(start)
        key = stdscr.getch()
        if key == curses.KEY_RESIZE:
            get_term_size()
            stdscr.clear()
        elif key == curses.KEY_UP and echo_cursor > 0:
            echo_cursor = echo_cursor - 1
            if echo_cursor - start < 0 and start > 0:
                start = start - 1
        elif key == curses.KEY_DOWN and echo_cursor < len(echoes) - 1:
            echo_cursor = echo_cursor + 1
            if echo_cursor - start > height - 3 and start < len(echoes) - height + 2:
                start = start + 1
        elif key == ord("g"):
            fetch_mail()

check_directories()
load_config()
stdscr = curses.initscr()
curses.start_color()
curses.noecho()
curses.curs_set(False)
stdscr.keypad(True)
curses.init_pair(1, 4, 0)
curses.init_pair(2, 3, 0)
curses.init_pair(3, 7, 4)
curses.init_pair(4, 7, 0)
get_term_size()
echo_selector()
curses.echo()
curses.curs_set(True)
curses.endwin()
