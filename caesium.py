#!/usr/bin/env python3

import curses, os, urllib.request, urllib.parse, base64, codecs, pickle, time, subprocess, re
from datetime import datetime

nodes = []
node = 0
editor = ""
lasts = {}
color_theme = "default"
bold = [False, False, False, False, False, False, False]
counts = []
counts_rescan = True
next_echoarea = False

def check_directories():
    if not os.path.exists("echo"):
        os.mkdir("echo")
    if not os.path.exists("echo/full"):
        os.mkdir("echo/full")
    if not os.path.exists("msg"):
        os.mkdir("msg")
    if not os.path.exists("out"):
        os.mkdir("out")
    if not os.path.exists("echo/favorites"):
        open("echo/favorites", "w")
    if not os.path.exists("echo/carbonarea"):
        open("echo/carbonarea", "w")

#
# Взаимодействие с нодой
#

def separate(l, step=20):
    for x in range(0, len(l), step):
        yield l[x:x+step]

def load_config():
    global nodes, editor, color_theme
    first = True
    node = {}
    echoareas = []
    archive = []
    f = open("caesium.cfg")
    config = f.read().split("\n")
    f.close()
    for line in config:
        param = line.split(" ")
        if param[0] == "nodename":
            if not first:
                node["echoareas"] = echoareas
                node["archive"] = archive
                node["clone"] = []
                nodes.append(node)
            else:
                first = False
            node = {}
            echoareas = []
            archive = []
            node["nodename"] = " ".join(param[1:])
        elif param[0] == "node":
            node["node"] = param[1]
        elif param[0] == "auth":
            node["auth"] = param[1]
        elif param[0] == "echo":
            if len(param) == 2:
                echoareas.append([param[1], ""])
            else:
                echoareas.append([param[1], " ".join(param[2:])])
        elif param[0] == "to":
            node["to"] = " ".join(param[1:])
        elif param[0] == "archive":
            if len(param) == 2:
                archive.append([param[1], ""])
            else:
                archive.append([param[1], " ".join(param[2:])])
        elif param[0] == "editor":
            editor = " ".join(param[1:])
        elif param[0] == "theme":
            color_theme = param[1]
    if not "nodename" in node:
        node["nodename"] = "untitled node"
    if not "to" in node:
        node["to"] = ""
    node["echoareas"] = echoareas
    node["archive"] = archive
    node["clone"] = []
    nodes.append(node)

def load_colors():
    global bold
    colors = ["black", "red", "green", "yellow", "blue", "magenta", "cyan", "white"]

    theme = open("themes/" + color_theme + ".cfg", "r").read().split("\n")
    for line in theme:
        param = line.split(" ")
        if param[0] == "border":
            curses.init_pair(1, colors.index(param[1]), colors.index(param[2]))
            if len(param) == 4:
                bold[0] = True
            else:
                bold[0] = False
        if param[0] == "titles":
            curses.init_pair(2, colors.index(param[1]), colors.index(param[2]))
            if len(param) == 4:
                bold[1] = True
            else:
                bold[1] = False
        if param[0] == "cursor":
            curses.init_pair(3, colors.index(param[1]), colors.index(param[2]))
            if len(param) == 4:
                bold[2] = True
            else:
                bold[2] = False
        if param[0] == "text":
            curses.init_pair(4, colors.index(param[1]), colors.index(param[2]))
            if len(param) == 4:
                bold[3] = True
            else:
                bold[3] = False
        if param[0] == "quote1":
            curses.init_pair(5, colors.index(param[1]), colors.index(param[2]))
            if len(param) == 4:
                bold[4] = True
            else:
                bold[4] = False
        if param[0] == "quote2":
            curses.init_pair(6, colors.index(param[1]), colors.index(param[2]))
            if len(param) == 4:
                bold[5] = True
            else:
                bold[5] = False
        if param[0] == "comment":
            curses.init_pair(7, colors.index(param[1]), colors.index(param[2]))
            if len(param) == 4:
                bold[6] = True
            else:
                bold[6] = False

def get_msg_list(echo):
    msg_list = []
    r = urllib.request.Request(nodes[node]["node"] + "u/e/" + echo[0])
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

def get_local_full_msg_list(echo):
    if not os.path.exists("echo/full/" + echo[0]):
        return []
    else:
        local_msg_list = codecs.open("echo/full/" + echo[0], "r", "utf-8").read().split("\n")
        return local_msg_list

def get_bundle(msgids):
    bundle = []
    r = urllib.request.Request(nodes[node]["node"] + "u/m/" + msgids)
    with urllib.request.urlopen(r) as f:
        bundle = f.read().decode("utf-8").split("\n")
    return bundle

def debundle(echo, bundle, local, carbonarea):
    for msg in bundle:
        if msg:
            m = msg.split(":")
            msgid = m[0]
            if len(msgid) == 20 and m[1]:
                msgbody = base64.b64decode(m[1].encode("ascii")).decode("utf8")
                if msgbody.split("\n")[5] == nodes[node]["to"] and not msgid in carbonarea:
                    codecs.open("echo/carbonarea", "a", "utf-8").write(msgid + "\n")
                codecs.open("msg/" + msgid, "w", "utf-8").write(msgbody)
                codecs.open("echo/" + echo[0], "a", "utf-8").write(msgid + "\n")
                if not msgid in local:
                    codecs.open("echo/full/" + echo[0], "a", "utf-8").write(msgid + "\n")

def fetch_mail():
    global lasts
    stdscr.clear()
    stdscr.attron(curses.color_pair(1))
    if bold[0]:
        stdscr.attron(curses.A_BOLD)
    else:
        stdscr.attroff(curses.A_BOLD)
    stdscr.border()
    draw_title(0, 1, "Получение почты")
    draw_title(0, width - len(nodes[node]["nodename"]) - 3, nodes[node]["nodename"])
    stdscr.refresh()
    log = curses.newwin(height - 2, width - 2, 1, 1)
    log.scrollok(True)
    line = -1
    echoareas = nodes[node]["echoareas"][2:]
    carbonarea = open("echo/carbonarea", "r").read().split("\n")
    for echo in echoareas:
        if line < height - 3:
            line = line + 1
        else:
            log.scroll()
        try:
            remote_msg_list = get_msg_list(echo)
            remote = True
        except:
            remote = False
        if remote and len(remote_msg_list) > 1:
            if echo[0] in nodes[node]["clone"]:
                if os.path.exists("echo/" + echo[0]):
                    os.remove("echo/" + echo[0])
                local_msg_list = get_local_msg_list(echo)
                msg_list = [x for x in remote_msg_list if x not in local_msg_list and x != ""]
                nodes[node]["clone"].remove(echo[0])
                lasts[echo[0]] = -1
            elif os.path.exists("echo/full/" + echo[0]):
                local_msg_list = get_local_full_msg_list(echo)
                msg_list = [x for x in remote_msg_list if x not in local_msg_list and x != ""]
            else:
                local_msg_list = get_local_full_msg_list(echo)
                msg_list = [x for x in remote_msg_list[-51:] if x not in local_msg_list and x != ""]
                if not len(msg_list) == 1:
                    msg_list.append("")
                for msgid in remote_msg_list:
                    if len(msgid) == 20:
                        open("echo/full/" + echo[0], "a").write(msgid + "\n")
            list_len = len (msg_list) - 1
            if list_len > 1 and not echo[0] in lasts:
                lasts[echo[0]] = -1
            n = 0
            if os.path.exists("echo/full/" + echo[0]):
                local_index = open("echo/full/" + echo[0]).read().split("\n")
            else:
                local_index = []
            for get_list in separate(msg_list):
                debundle(echo, get_bundle("/".join(get_list)), local_index, carbonarea)
                n = n + len(get_list)
                current_time()
                stdscr.refresh()
                if bold[3]:
                    color = curses.color_pair(4) + curses.A_BOLD
                else:
                    color = curses.color_pair(4)
                log.addstr(line, 1, "Загрузка " + echo[0] + ": " + str(n - 1) + "/" + str(list_len), color)
                log.refresh()
    if remote and line >= height - 5:
        for i in range(abs(height - 6 - line)):
            log.scroll()
            line = line - 1
    if not remote:
        line = -1
    if bold[3]:
        color = curses.color_pair(4) + curses.A_BOLD
    else:
        color = curses.color_pair(4)
    if remote:
        log.addstr(line + 2, 1, "Загрузка завершена.", color)
    else:
        log.addstr(line + 2, 1, "Ошибка: не удаётся связаться с нодой.", color)
    if bold[1]:
        color = curses.color_pair(2) + curses.A_BOLD
    else:
        color = curses.color_pair(2)
    log.addstr(line + 3, 1, "Нажмите любую клавишу.", color)
    log.getch()
    stdscr.clear()

def outcount():
    if not os.path.exists("out/" + nodes[node]["nodename"]):
        os.mkdir("out/" + nodes[node]["nodename"])
    if not os.path.exists("out/" + nodes[node]["nodename"] + "/.outcount"):
        codecs.open("out/" + nodes[node]["nodename"] + "/.outcount", "w", "utf-8").write("0")
    i = str(int(codecs.open("out/" + nodes[node]["nodename"] + "/.outcount", "r", "utf-8").read()) + 1)
    codecs.open("out/" + nodes[node]["nodename"] + "/.outcount", "w", "utf-8").write(i)
    return "out/" + nodes[node]["nodename"] + "/%s.out" % i.zfill(5)

def save_out():
    new = codecs.open("temp", "r", "utf-8").read().split("\n")
    if len(new) <= 1:
        os.remove("temp")
    else:
        header = new.index("")
        if header == 3:
            buf = new
        elif header == 4:
            buf = new[1:5] + ["@repto:%s" % new[0]] + new[5:]
        codecs.open(outcount(), "w", "utf-8").write("\n".join(buf))
        os.remove("temp")

def make_toss():
    if not os.path.exists("out/" + nodes[node]["nodename"]):
        os.mkdir("out/" + nodes[node]["nodename"])
    lst = [x for x in os.listdir("out/" + nodes[node]["nodename"]) if x.endswith(".out")]
    for msg in lst:
        text = codecs.open("out/" + nodes[node]["nodename"] + "/%s" % msg, "r", "utf-8").read()
        coded_text = base64.b64encode(text.encode("utf-8"))
        codecs.open("out/" + nodes[node]["nodename"] + "/%s.toss" % msg, "w", "utf-8").write(coded_text.decode("utf-8"))
        os.rename("out/" + nodes[node]["nodename"] + "/%s" % msg, "out/" + nodes[node]["nodename"] + "/%s%s" % (msg, "msg"))

def send_mail():
    stdscr.clear()
    if bold[0]:
        stdscr.attron(curses.color_pair(1))
        stdscr.attron(curses.A_BOLD)
    else:
        stdscr.attron(curses.color_pair(1))
    stdscr.border()
    draw_title(0, 1, "Отправка почты")
    stdscr.refresh()
    lst = [x for x in sorted(os.listdir("out/" + nodes[node]["nodename"])) if x.endswith(".toss")]
    max = len(lst)
    n = 1
    try:
        if bold[3]:
            color = curses.color_pair(4) + curses.A_BOLD
        else:
            color = curses.color_pair(4)
        for msg in lst:
            stdscr.addstr(1, 1, "Отправка сообщения: " + str(n) + "/" + str(max), color)
            text = codecs.open("out/" + nodes[node]["nodename"] + "/%s" % msg, "r", "utf-8").read()
            data = urllib.parse.urlencode({"tmsg": text,"pauth": nodes[node]["auth"]}).encode("utf-8")
            request = urllib.request.Request(nodes[node]["node"] + "u/point")
            result = urllib.request.urlopen(request, data).read().decode("utf-8")
            if result.startswith("msg ok"):
                os.remove("out/" + nodes[node]["nodename"] + "/%s" % msg)
                n = n + 1
            elif result == "msg big!":
                print ("ERROR: very big message (limit 64K)!")
            elif result == "auth error!":
                print ("ERROR: unknown auth!")
            else:
                print ("ERROR: unknown error!")
        stdscr.addstr(3, 1, "Отправка завершена.", color)
    except:
        stdscr.addstr(2, 1, "Ошибка: не удаётся связаться с нодой.", color)
    if bold[1]:
        color = curses.color_pair(2) + curses.A_BOLD
    else:
        curses.color_pair(2)
    stdscr.addstr(3, 1, "Нажмите любую клавишу.", color)
    stdscr.getch()
    stdscr.clear()

#
# Пользовательский интерфейс
#

echo_cursor = 0
archive_cursor = 0
width = 0
height = 0

def get_term_size():
    global width, height
    height, width = stdscr.getmaxyx()

def draw_title(y, x, title):
    if bold[0]:
        color = curses.color_pair(1) + curses.A_BOLD
    else:
        color = curses.color_pair(1)
    stdscr.addstr(y, x, "[", color)
    stdscr.addstr(y, x + 1 + len(title), "]", color)
    if bold[1]:
        color = curses.color_pair(2) + curses.A_BOLD
    else:
        color = curses.color_pair(2)
    stdscr.addstr(y, x + 1, title, curses.color_pair(2) + curses.A_BOLD)

def draw_cursor(y, color):
    for i in range (1, width - 1):
        stdscr.addstr(y + 1, i, " ", color)

def current_time():
    draw_title (height - 1, width - 8, datetime.now().strftime("%H:%M"))

def get_echo_length(echo):
    if os.path.exists("echo/" + echo):
        f = open ("echo/" + echo, "r")
        echo_length = len(f.read().split("\n")) - 2
        f.close()
    else:
        echo_length = 0
    return echo_length

def rescan_counts(echoareas):
    counts = []
    for echo in echoareas:
        try:
            echocount = len(open("echo/" + echo[0], "r").read().split("\n")) - 1
            if echo[0] in lasts: 
                last = echocount - lasts[echo[0]]
                if echocount == 0 and lasts[echo[0]] == 0:
                    last = 1
            else:
                last = echocount + 1
        except:
            echocount = 0
            last = 1
        counts.append([str(echocount), str(last - 1)])
    return counts

def draw_echo_selector(start, cursor, archive):
    global counts, counts_rescan
    dsc_lens = []
    m = 0
    if bold[0]:
        stdscr.attron(curses.color_pair(1))
        stdscr.attron(curses.A_BOLD)
    else:
        stdscr.attron(curses.color_pair(1))
    stdscr.border()
    if archive:
        echoareas = nodes[node]["archive"]
        draw_title(0, 1, "Архив эхоконференций")
    else:
        echoareas = nodes[node]["echoareas"]
        draw_title(0, 1, "Список эхоконференций")
        draw_title(0, width - len(nodes[node]["nodename"]) - 3, nodes[node]["nodename"])
    for echo in echoareas:
        l = len(echo[1])
        if l > m:
            m = l
        if m > width - 38:
            m = width - 38
        dsc_lens.append(l)
    y = 0
    for echo in echoareas:
        if y - start < height - 2:
            if y == cursor:
                if y >= start:
                    if bold[2]:
                        color = curses.color_pair(3) + curses.A_BOLD
                    else:
                        color = curses.color_pair(3)
                    draw_cursor(y - start, color)
                stdscr.attron (color)
            else:
                if y >= start:
                    if bold[3]:
                        color = curses.color_pair(4) + curses.A_BOLD
                    else:
                        color = curses.color_pair(4)
                    draw_cursor(y - start, color)
                if bold[3]:
                    stdscr.attron (curses.color_pair(4))
                    stdscr.attron (curses.A_BOLD)
                else:
                    stdscr.attron (curses.color_pair(4))
                    stdscr.attroff (curses.A_BOLD)
            if y + 1 >= start + 1:
                echo_length = get_echo_length(echo[0])
                if echo[0] in lasts:
                    last = lasts[echo[0]]
                else:
                    last = 0
                if last < echo_length:
                    stdscr.addstr(y + 1 - start, 1, "+")
                if echo[0] in nodes[node]["clone"]:
                    stdscr.addstr(y + 1 - start, 2, "*")
                stdscr.addstr(y + 1 - start, 3, echo[0])
                if counts_rescan:
                    counts = rescan_counts(echoareas)
                    counts_rescan = False
                if width - 38 >= len(echo[1]):
                    stdscr.addstr(y + 1 - start, width - 2 - dsc_lens[y], echo[1])
                else:
                    cut_index = width - 38 - len(echo[1])
                    stdscr.addstr(y + 1 - start, width - 2 - len(echo[1][:cut_index]), echo[1][:cut_index])
                stdscr.addstr(y + 1 - start, width - 10 - m - len(counts[y][0]), counts[y][0])
                stdscr.addstr(y + 1 - start, width - 4 - m - len(counts[y][1]), counts[y][1])
        y = y + 1
    current_time()
    stdscr.refresh()

def find_new(cursor):
    ret = cursor
    n = 0
    lock = False
    for i in counts:
        n = n + 1
        if n > cursor and not lock and int(i[1]) > 0:
            ret = n - 1
            lock = True
    return ret

def echo_selector():
    global echo_cursor, archive_cursor, counts, counts_rescan, next_echoarea, node
    archive = False
    echoareas = nodes[node]["echoareas"]
    key = 0
    go = True
    start = 0
    if archive:
        cursor = echo_cursor
    else:
        cursor = archive_cursor
    while go:
        draw_echo_selector(start, cursor, archive)
        key = stdscr.getch()
        if key == curses.KEY_RESIZE:
            get_term_size()
            stdscr.clear()
        elif key == curses.KEY_UP and cursor > 0:
            cursor = cursor - 1
            if cursor - start < 0 and start > 0:
                start = start - 1
        elif key == curses.KEY_DOWN and cursor < len(echoareas) - 1:
            cursor = cursor + 1
            if cursor - start > height - 3 and start < len(echoareas) - height + 2:
                start = start + 1
        elif key == curses.KEY_PPAGE:
            cursor = cursor - height + 2
            if cursor < 0:
                cursor = 0
            if cursor - start < 0 and start > 0:
                start = start - height + 2
            if start < 0:
                start = 0
        elif key == curses.KEY_NPAGE:
            cursor = cursor + height - 2
            if cursor >= len(echoareas):
                cursor = len(echoareas) - 1
            if cursor - start > height - 3:
                start = start + height - 2
                if start > len(echoareas) - height + 2:
                    start = len(echoareas) - height + 2
        elif key == curses.KEY_HOME:
            cursor = 0
            start = 0
        elif key == curses.KEY_END:
            cursor = len(echoareas) - 1
            if len(echoareas) >= height - 2:
                start = len(echoareas) - height + 2
        elif key == ord("g") or key == ord("G"):
            fetch_mail()
            counts = rescan_counts(echoareas)
            cursor = find_new(0)
        elif key == ord("s") or key == ord("S"):
            make_toss()
            send_mail()
        elif key == 9:
            if archive:
                archive = False
                archive_cursor = cursor
                cursor = echo_cursor
                echoareas = nodes[node]["echoareas"]
                stdscr.clear()
                counts_rescan = True
            else:
                archive = True
                echo_cursor = cursor
                cursor = archive_cursor
                echoareas = nodes[node]["archive"]
                stdscr.clear()
                counts_rescan = True
        elif key == 10 or key == curses.KEY_RIGHT or key == ord(" "):
            if echoareas[cursor][0] in lasts:
                last = lasts[echoareas[cursor][0]]
            else:
                last = 0
            echo_length = get_echo_length(echoareas[cursor][0])
            if last < echo_length:
                last = last + 1
            if cursor == 0:
                go = not echo_reader(echoareas[cursor][0], last, archive, True)
            else:
                go = not echo_reader(echoareas[cursor][0], last, archive, False)
            counts_rescan = True
            if next_echoarea:
                counts = rescan_counts(echoareas)
                cursor = find_new(cursor)
                if cursor - start > height - 3:
                    start = cursor - height + 3
                next_echoarea = False
        elif key == ord("."):
            node = node + 1
            if node == len(nodes):
                node = 0
            echoareas = nodes[node]["echoareas"]
            stdscr.clear()
            counts_rescan = True
            cursor = 0
        elif key == ord(","):
            node = node - 1
            if node == -1:
                node = len(nodes) - 1
            echoareas = nodes[node]["echoareas"]
            stdscr.clear()
            counts_rescan = True
            cursor = 0
        elif key == ord("c") or key == ord("C"):
            if cursor > 1:
                if echoareas[cursor][0] in nodes[node]["clone"]:
                    nodes[node]["clone"].remove(echoareas[cursor][0])
                else:
                    nodes[node]["clone"].append(echoareas[cursor][0])
        elif key == curses.KEY_F10:
            go = False
    if archive:
        archive_cursor = cursor
    else:
        echo_cursor = cursor

def read_msg(msgid):
    size = "0b"
    if os.path.exists("msg/" + msgid) and msgid != "":
        f = open("msg/" + msgid, "r")
        msg = f.read().split("\n")
        f.close
        size = os.stat("msg/" + msgid).st_size
        if size < 1024:
            size = str(size) + " B"
        else:
            size = str(int(size / 1024 * 10) / 10) + " KB"
    else:
        msg = ["", "", "", "", "", "", "", "", "Сообщение отсутствует в базе"]
    return msg, size

def body_render(tbody):
    body = ""
    code = ""
    for line in tbody:
        n = 0
        rr = re.compile(r"^[a-zA-Zа-яА-Я0-9_-]{0,20}>{1,20}")
        cc = re.compile(r"(^\s*)(PS|P.S|ps|ЗЫ|З.Ы|\/\/|#)")
        try:
            count = line[0:rr.match(line).span()[1]].count(">")
        except:
            count = 0
        if count > 0:
            if count % 2 == 1:
                code = chr(15)
            elif count % 2 == 0:
                code = chr(16)
        elif cc.match(line):
            code = chr(17)
        else:
            code = " "
        if code != " " and code != chr(17):
            line = " " + line
        body = body + code
        for word in line.split(" "):
            if n + len(word) + 1 <= width:
                n = n + len(word)
                body = body + word
                if not word[-1:] == "\n":
                    n = n + 1
                    body = body + " "
            else:
                body = body[:-1]
                if len(word) < width:
                    body = body + "\n" + code + word
                    n = len (word)
                else:
                    chunks, chunksize = len(word), width
                    chunk_list = [ word[i:i+chunksize] for i in range(0, chunks, chunksize) ]
                    for line in chunk_list:
                        body = body + "\n" + code + line
                    n = len(chunk_list[-1])
                if not word[-1:] == "\n":
                    n = n + 1
                    body = body + " "
        if body.endswith(" "):
            body = body[:-1]
        body = body + "\n"
    return body.split("\n")

def draw_reader(echo, msgid):
    for i in range(0, width):
        if bold[0]:
            color = curses.color_pair(1) + curses.A_BOLD
        else:
            color = curses.color_pair(1)
        stdscr.insstr(0, i, "─", color)
        stdscr.insstr(4, i, "─", color)
        stdscr.insstr(height - 1, i, "─", color)
    draw_title(0, 1, echo + " / " + msgid)
    current_time()
    for i in range(0, 3):
        draw_cursor(i, 1)
    if bold[1]:
        color = curses.color_pair(2) + curses.A_BOLD
    else:
        color = curses.color_pair(2)
    stdscr.addstr(1, 1, "От:   ", color)
    stdscr.addstr(2, 1, "Кому: ", color)
    stdscr.addstr(3, 1, "Тема: ", color)


def call_editor():
    curses.echo()
    curses.curs_set(True)
    curses.endwin()
    p = subprocess.Popen(editor + " ./temp", shell=True)
    p.wait()
    save_out()
    stdscr = curses.initscr()
    curses.start_color()
    curses.noecho()
    curses.curs_set(False)
    stdscr.keypad(True)
    get_term_size()

def message_box(smsg):
    maxlen = 0
    msg = smsg.split("\n")
    for line in msg:
        if len(line) > maxlen:
            maxlen = len(line)
    msgwin = curses.newwin(len(msg) + 4, maxlen + 2, int(height / 2 - 2) , int(width / 2 - maxlen / 2))
    if bold[0]:
        msgwin.attron(curses.color_pair(1))
        msgwin.attron(curses.A_BOLD)
    else:
        msgwin.attron(curses.color_pair(1))
    msgwin.border()
    i = 1
    if bold[3]:
        color = curses.color_pair(4) + curses.A_BOLD
    else:
        color = curses.color_pair(4)
    for line in msg:
        msgwin.addstr(i, 1, line, color)
        i = i + 1
    if bold[1]:
        color = curses.color_pair(2) + curses.A_BOLD
    else:
        color = curses.color_pair(2)
    msgwin.addstr(len(msg) + 2, int((maxlen + 2 - 21) / 2), "Нажмите любую клавишу", color)
    msgwin.refresh()
    msgwin.getch()
    msgwin.clear()

def save_message(msgid):
    msg, size = read_msg(msgid)
    f = open(msgid + ".txt", "w")
    f.write("== " + msg[1] + " ==================== " + str(msgid) + "\n")
    f.write("От:   " + msg[3] + " (" + msg[4] + ")\n")
    f.write("Кому: " + msg[5] + "\n")
    f.write("Тема: " + msg[6] + "\n")
    f.write("\n".join(msg[7:]))
    f.close
    message_box("Сообщение сохранено в файл\n" + str(msgid) + ".txt")

def save_to_favorites(msgid):
    if os.path.exists("echo/favorites"):
        favorites = open("echo/favorites", "r").read().split("\n")
    else:
        favorites = []
    if not msgid in favorites:
        open("echo/favorites", "a").write(msgid + "\n")
        message_box("Собщение добавлено в избранные")
    else:
        message_box("Собщение уже есть в избранных")

def get_echo_msgids(echo):
    if os.path.exists("echo/" + echo):
        f = open("echo/" + echo, "r")
        msgids = f.read().split("\n")[:-1]
        f.close()
    else:
        msgids = []
    return msgids

def echo_reader(echo, last, archive, favorites):
    global lasts, next_echoarea
    stdscr.clear()
    if bold[0]:
        stdscr.attron(curses.color_pair(1))
        stdscr.attron(curses.A_BOLD)
    else:
        stdscr.attron(curses.color_pair(1))
    y = 0
    msgn = last
    key = 0
    msgids = get_echo_msgids(echo)
    if len(msgids) > 0:
        msg, size = read_msg(msgids[msgn])
        msgbody = body_render(msg[8:])
    go = True
    while go:
        if len(msgids) > 0:
            draw_reader(msg[1], msgids[msgn])
            msg_string = str(msgn + 1) + " / " + str(len(msgids)) + " [" + str(len(msgids) - msgn - 1) + "]"
            draw_title (0, width - len(msg_string) - 3, msg_string)
            msgtime = time.strftime("%Y.%m.%d %H:%M UTC", time.gmtime(int(msg[2])))
            if bold[3]:
                color = curses.color_pair(4) + curses.A_BOLD
            else:
                color = curses.color_pair(4)
            stdscr.addstr(1, 7, msg[3] + " (" + msg[4] + ")", color)
            stdscr.addstr(1, width - len(msgtime) - 1, msgtime, color)
            stdscr.addstr(2, 7, msg[5], color)
            stdscr.addstr(3, 7, msg[6][:width - 8], color)
            draw_title(4, 1, size)
            for i in range (0, height - 6):
                for x in range (0, width):
                    stdscr.addstr(i + 5, x, " ", 1)
                if i < len(msgbody) - 1:
                    if y + i < len(msgbody) and len(msgbody[y+i]) > 0:
                        if msgbody[y + i][0] == chr(15):
                            stdscr.attron(curses.color_pair(5))
                            if bold[4]:
                                stdscr.attron(curses.A_BOLD)
                            else:
                                stdscr.attroff(curses.A_BOLD)
                        elif msgbody[y + i][0] == chr(16):
                            stdscr.attron(curses.color_pair(6))
                            if bold[5]:
                                stdscr.attron(curses.A_BOLD)
                            else:
                                stdscr.attroff(curses.A_BOLD)
                        elif msgbody[y + i][0] == chr(17):
                            stdscr.attron(curses.color_pair(7))
                            if bold[6]:
                                stdscr.attron(curses.A_BOLD)
                            else:
                                stdscr.attroff(curses.A_BOLD)
                        else:
                            stdscr.attron(curses.color_pair(4))
                            if bold[3]:
                                stdscr.attron(curses.A_BOLD)
                            else:
                                stdscr.attroff(curses.A_BOLD)
                        stdscr.addstr(i + 5, 0, msgbody[y + i][1:])
        else:
            draw_reader(echo, "")
        stdscr.attron(curses.color_pair(1))
        if bold[0]:
            stdscr.attron(curses.A_BOLD)
        else:
            stdscr.attroff(curses.A_BOLD)
        stdscr.refresh()
        key = stdscr.getch()
        if key == curses.KEY_RESIZE:
            y = 0
            get_term_size()
            if len(msgids) > 0:
                msgbody = body_render(msg[8:])
            stdscr.clear()
        elif key == curses.KEY_LEFT and msgn > 0:
            y = 0
            if len(msgids) > 0:
                msgn = msgn - 1
                msg, size = read_msg(msgids[msgn])
                msgbody = body_render(msg[8:])
        elif key == curses.KEY_RIGHT and msgn < len(msgids) - 1:
            y = 0
            if len(msgids) > 0:
                msgn = msgn +1
                msg, size = read_msg(msgids[msgn])
                msgbody = body_render(msg[8:])
        elif key == curses.KEY_RIGHT and (msgn == len(msgids) - 1 or len(msgids) == 0):
            go = False
            quit = False
            next_echoarea = True
        elif key == curses.KEY_UP and y > 0:
            if len(msgids) > 0:
                y = y - 1
        elif key == curses.KEY_PPAGE:
            if len(msgids) > 0:
                y = y - height + 6
                if y < 0:
                    y = 0
        elif key == curses.KEY_NPAGE:
            if len(msgids) > 0 and len(msgbody) > height - 5:
                y = y + height - 5
                if y + height - 5 >= len(msgbody):
                    y = len(msgbody) - height + 5
        elif key == 10 or key == ord(" "):
            if len(msgids) == 0 or y >= len(msgbody) - height + 6:
                y = 0
                if msgn == len(msgids) - 1 or len(msgids) == 0:
                    next_echoarea = True
                    go = False
                    quit = False
                else:
                    msgn = msgn +1
                    msg, size = read_msg(msgids[msgn])
                    msgbody = body_render(msg[8:])
            else:
                if len(msgids) > 0 and len(msgbody) > height - 6:
                    y = y + height - 6
        elif key == curses.KEY_DOWN:
            if len(msgids) > 0:
                if y + height - 5 < len(msgbody):
                    y = y + 1
        elif key == curses.KEY_HOME:
            if len(msgids) > 0:
                y = 0
                msgn = 0
                msg, size = read_msg(msgids[msgn])
                msgbody = body_render(msg[8:])
        elif key == curses.KEY_END:
            if len(msgids) > 0:
                y = 0
                msgn = len(msgids) - 1
                msg, size = read_msg(msgids[msgn])
                msgbody = body_render(msg[8:])
        elif not archive and (key == ord ("i") or key == ord("I")):
            if not favorites:
                f = open("temp", "w")
                f.write(echo + "\n")
                f.write("All\n")
                f.write("No subject\n\n")
                f.close()
                call_editor()
        elif key == ord("w") or key == ord("W"):
            save_message(msgids[msgn])
        elif key == ord("f") or key == ord("F"):
            save_to_favorites(msgids[msgn])
        elif not archive and (key == ord ("q") or key == ord("Q")):
            if len(msgids) > 0:
                f = open("temp", "w")
                f.write(msgids[msgn] + "\n")
                f.write(msg[1] + "\n")
                f.write(msg[3] + "\n")
                to = msg[3].split(" ")
                if len(to) == 1:
                    q = to[0]
                else:
                    q = ""
                    for word in to:
                        q = q + word[0]
                if not msg[6].startswith("Re:"):
                    f.write("Re: " + msg[6] + "\n")
                else:
                    f.write(msg[6] + "\n")
                rr = re.compile(r"^[a-zA-Zа-яА-Я0-9_-]{0,20}>{1,20}")
                for line in msg[8:]:
                    if line.strip() != "":
                        if rr.match(line):
                            if line[rr.match(line).span()[1]] == " ":
                                quoter = ">"
                            else:
                                quoter = "> "
                            f.write("\n" + line[:rr.match(line).span()[1]] + quoter + line[rr.match(line).span()[1]:])
                        else:
                            f.write("\n" + q + "> " + line)
                    else:
                        f.write("\n" + line)
                f.close()
                call_editor()
        elif favorites and key == curses.KEY_DC:
            if len(msgids) > 0:
                favorites_list = open("echo/favorites", "r").read().split("\n")
                favorites_list.remove(msgids[msgn])
                open("echo/favorites", "w").write("\n".join(favorites_list))
                msgids = get_echo_msgids(echo)
                if msgn >= len(msgids):
                    msgn = len(msgids) - 1
                stdscr.clear()
        elif key == 27:
            go = False
            quit = False
            next_echoarea = False
        elif key == curses.KEY_F10:
            go = False
            quit = True
    lasts[echo] = msgn
    f = open("lasts.lst", "wb")
    pickle.dump(lasts, f)
    f.close()
    stdscr.clear()
    return quit

check_directories()
load_config()
for i in range(0, len(nodes)):
    nodes[i]["echoareas"].insert(0, ["favorites", "Избранные сообщения"])
    nodes[i]["echoareas"].insert(1, ["carbonarea", "Карбонка"])
if os.path.exists("lasts.lst"):
    f = open("lasts.lst", "rb")
    lasts = pickle.load(f)
    f.close()
stdscr = curses.initscr()
curses.start_color()
load_colors()
curses.noecho()
curses.curs_set(False)
stdscr.keypad(True)

stdscr.bkgd(" ", curses.color_pair(1))
get_term_size()
echo_selector()
curses.echo()
curses.curs_set(True)
curses.endwin()
