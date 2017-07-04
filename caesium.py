#!/usr/bin/env python3

import curses, os, urllib.request, urllib.parse, base64, codecs, pickle, time, subprocess, re, hashlib, webbrowser
from datetime import datetime
from shutil import copyfile
from keys import *

lasts = {}
color_theme = "default"
bold = [False, False, False, False, False, False, False, False, False, False, False]
counts = []
counts_rescan = True
echo_counts = {}
next_echoarea = False
depth = 50
messages = []

version = "Caesium/0.4 RC1 │"

splash = [ "▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀",
           "████████ ████████ ████████ ████████ ███ ███  ███ ██████████",
           "███           ███ ███  ███ ███          ███  ███ ███ ██ ███",
           "███      ████████ ████████ ████████ ███ ███  ███ ███ ██ ███",
           "███      ███  ███ ███           ███ ███ ███  ███ ███ ██ ███",
           "████████ ████████ ████████ ████████ ███ ████████ ███ ██ ███",
           "▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄",
           "           ncurses ii/idec client      v.0.4 RC1",
           "           Andrew Lobanov             04.07.2017"]

urltemplate=re.compile("((https?|ftp|file)://?[-A-Za-z0-9+&@#/%?=~_|!:,.;]+[-A-Za-z0-9+&@#/%=~_|])")

def reset_config():
    global nodes, node, editor, oldquote, db
    nodes = []
    node = 0
    editor = ""
    oldquote = False
    db = 2

def check_directories():
    if not os.path.exists("out"):
        os.mkdir("out")
    if not os.path.exists("fecho"):
        os.mkdir("fecho")
    for n in nodes:
        if not os.path.exists("out/" + n["nodename"]):
            os.mkdir("out/" + n["nodename"])
    if db == 0:
        if not os.path.exists("echo"):
            os.mkdir("echo")
        if not os.path.exists("msg"):
            os.mkdir("msg")
        if not os.path.exists("echo/favorites"):
            open("echo/favorites", "w")
        if not os.path.exists("echo/carbonarea"):
            open("echo/carbonarea", "w")
    elif db == 1:
        if not os.path.exists("aio"):
            os.mkdir("aio")
    elif db == 2:
        if not os.path.exists("ait"):
            os.mkdir("ait")

def check_config():
    if not os.path.exists("caesium.cfg"):
        default_config = open("caesium.def.cfg", "r").read()
        open("caesium.cfg","w").write(default_config)

#
# Взаимодействие с нодой
#

def separate(l, step=20):
    for x in range(0, len(l), step):
        yield l[x:x+step]

def load_config():
    global nodes, editor, color_theme, show_splash, oldquote, db, browser, depth
    nodes = []
    first = True
    node = {}
    echoareas = []
    fechoareas = []
    archive = []
    browser = webbrowser

    config = open("caesium.cfg").read().split("\n")
    for line in config:
        param = line.split(" ")
        if param[0] == "nodename":
            if not first:
                node["echoareas"] = echoareas
                node["fechoareas"] = fechoareas
                node["archive"] = archive
                node["clone"] = []
                if not "to" in node:
                    node["to"] = []
                nodes.append(node)
            else:
                first = False
            node = {}
            echoareas = []
            fechoareas = []
            archive = []
            node["nodename"] = " ".join(param[1:])
        elif param[0] == "node":
            node["node"] = param[1]
            if not node["node"].endswith("/"):
                node["node"] = node["node"] + "/"
        elif param[0] == "auth":
            node["auth"] = param[1]
        elif param[0] == "echo":
            if len(param) == 2:
                echoareas.append([param[1], "", False])
            else:
                echoareas.append([param[1], " ".join(param[2:]), False])
        elif param[0] == "stat":
            if len(param) == 2:
                echoareas.append([param[1], "", True])
            else:
                echoareas.append([param[1], " ".join(param[2:]), True])
        elif param[0] == "fecho":
            fechoareas.append(param[1])
        elif param[0] == "to":
            node["to"] = " ".join(param[1:]).split(",")
        elif param[0] == "archive":
            if len(param) == 2:
                archive.append([param[1], "", True])
            else:
                archive.append([param[1], " ".join(param[2:]), True])
        elif param[0] == "editor":
            editor = " ".join(param[1:])
        elif param[0] == "theme":
            color_theme = param[1]
        elif param[0] == "nosplash":
            show_splash = False
        elif param[0] == "oldquote":
            oldquote = True
        elif param[0] == "depth":
            try:
                depth = int(param[1])
            except:
                None
        elif param[0] == "db":
            if param[1] == "txt":
                db = 0
            elif param[1] == "aio":
                db = 1
            elif param[1] == "ait":
                db = 2
            elif param[1] == "sqlite":
                db = 3
        elif param[0] == "browser":
            browser = webbrowser.GenericBrowser(param[1])

    if not "nodename" in node:
        node["nodename"] = "untitled node"
    if not "to" in node:
        node["to"] = []
    node["echoareas"] = echoareas
    node["fechoareas"] = fechoareas
    node["archive"] = archive
    node["clone"] = []
    nodes.append(node)
    for i in range(0, len(nodes)):
        nodes[i]["echoareas"].insert(0, ["favorites", "Избранные сообщения", True])
        nodes[i]["echoareas"].insert(1, ["carbonarea", "Карбонка", True])

def load_colors():
    global bold
    colors = ["black", "red", "green", "yellow", "blue", "magenta", "cyan", "white", "gray"]

    try:
        theme = open("themes/" + color_theme + ".cfg", "r").read().split("\n")
    except:
        theme = open("themes/default.cfg", "r").read().split("\n")
    for line in theme:
        param = line.split(" ")
        if len(param) > 1:
            if param[1] == "grey":
                param[1] = "gray"
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
        if param[0] == "url":
            curses.init_pair(8, colors.index(param[1]), colors.index(param[2]))
            if len(param) == 4:
                bold[7] = True
            else:
                bold[7] = False
        if param[0] == "statusline":
            curses.init_pair(9, colors.index(param[1]), colors.index(param[2]))
            if len(param) == 4:
                bold[8] = True
            else:
                bold[8] = False
        if param[0] == "header":
            curses.init_pair(10, colors.index(param[1]), colors.index(param[2]))
            if len(param) == 4:
                bold[9] = True
            else:
                bold[9] = False
        if param[0] == "scrollbar":
            curses.init_pair(11, colors.index(param[1]), colors.index(param[2]))
            if len(param) == 4:
                bold[10] = True
            else:
                bold[10] = False

def save_out(draft = False):
    new = codecs.open("temp", "r", "utf-8").read().strip().split("\n")
    if len(new) <= 1:
        os.remove("temp")
    else:
        header = new.index("")
        if header == 3:
            buf = new
        elif header == 4:
            buf = new[1:5] + ["@repto:%s" % new[0]] + new[5:]
        if draft:
            codecs.open(outcount() + ".draft", "w", "utf-8").write("\n".join(buf))
        else:
            codecs.open(outcount() + ".out", "w", "utf-8").write("\n".join(buf))
        os.remove("temp")

def resave_out(filename, draft = False):
    new = codecs.open("temp", "r", "utf-8").read().strip().split("\n")
    if len(new) <= 1:
        os.remove("temp")
    else:
        if draft:
            codecs.open("out/" + nodes[node]["nodename"] + "/" + filename.replace(".out", ".draft"), "w", "utf-8").write("\n".join(new))
        else:
            codecs.open("out/" + nodes[node]["nodename"] + "/" + filename, "w", "utf-8").write("\n".join(new))
        os.remove("temp")

def outcount():
    outpath = "out/" + nodes[node]["nodename"]
    i = str(len([x for x in os.listdir(outpath) if not x.endswith(".toss")]) + 1)
    return outpath + "/%s" % i.zfill(5)

def get_out_length(drafts = False):
    try:
        if drafts:
            return len([f for f in sorted(os.listdir("out/" + nodes[node]["nodename"])) if f.endswith(".draft")]) - 1
        else:
            return len([f for f in sorted(os.listdir("out/" + nodes[node]["nodename"])) if f.endswith(".out") or f.endswith(".outmsg")]) - 1
    except:
        return 0

def make_toss():
    lst = [x for x in os.listdir("out/" + nodes[node]["nodename"]) if x.endswith(".out")]
    for msg in lst:
        text = codecs.open("out/" + nodes[node]["nodename"] + "/%s" % msg, "r", "utf-8").read()
        coded_text = base64.b64encode(text.encode("utf-8"))
        codecs.open("out/" + nodes[node]["nodename"] + "/%s.toss" % msg, "w", "utf-8").write(coded_text.decode("utf-8"))
        os.rename("out/" + nodes[node]["nodename"] + "/%s" % msg, "out/" + nodes[node]["nodename"] + "/%s%s" % (msg, "msg"))

def send_mail():
    lst = [x for x in sorted(os.listdir("out/" + nodes[node]["nodename"])) if x.endswith(".toss")]
    max = len(lst)
    n = 1
    try:
        for msg in lst:
            print("\rОтправка сообщения: " + str(n) + "/" + str(max), end="")
            text = codecs.open("out/" + nodes[node]["nodename"] + "/%s" % msg, "r", "utf-8").read()
            data = urllib.parse.urlencode({"tmsg": text,"pauth": nodes[node]["auth"]}).encode("utf-8")
            request = urllib.request.Request(nodes[node]["node"] + "u/point")
            result = urllib.request.urlopen(request, data).read().decode("utf-8")
            if result.startswith("msg ok"):
                os.remove("out/" + nodes[node]["nodename"] + "/%s" % msg)
                n = n + 1
            elif result == "msg big!":
                print("\nERROR: very big message (limit 64K)!")
            elif result == "auth error!":
                print("\nERROR: unknown auth!")
            else:
                print("\nERROR: unknown error!")
        if len(lst) > 0:
            print()
    except:
        print("\nОшибка: не удаётся связаться с нодой.")

def separate(l, step=40):
    for x in range(0, len(l), step):
        yield l[x:x+step]

def get_features():
    try:
        r = urllib.request.Request(nodes[node]["node"] + "x/features")
        with urllib.request.urlopen(r) as f:
            features = f.read().decode("utf-8").split("\n")
    except:
        features = []
    return features

def check_features(features):
    ue = "u/e" in features
    xc = "x/c" in features
    f = "f/" in features
    return ue, xc, f

def load_counts():
    counts = {}
    if os.path.exists("counts.lst"):
        f = open("counts.lst", "rb")
        counts = pickle.load(f)
        f.close()
    else:
        counts[node] = {}
    if not node in counts:
        counts[node] = {}
    return counts[node]

def save_counts(counts, remote_counts):
    counts[node] = remote_counts
    f = open("counts.lst", "wb")
    pickle.dump(counts, f)
    f.close()

def get_remote_counts():
    counts = {}
    echoareas = []
    for echoarea in nodes[node]["echoareas"]:
        if echoarea[0] not in ["favorites", "carbonarea"]:
            echoareas.append(echoarea[0])
    r = urllib.request.Request(nodes[node]["node"] + "x/c/" + "/".join(echoareas))
    with urllib.request.urlopen(r) as f:
        c = f.read().decode("utf-8").split("\n")
    for count in c:
        echoarea = count.split(":")
        if len(echoarea) > 1:
            counts[echoarea[0]] = int(echoarea[1])
    return counts

def calculate_offset(depth):
    n = False
    offset = 0
    echoareas = []
    for echoarea in nodes[node]["echoareas"]:
        if not echoarea in ["favorites", "carbonarea"]:
            echoareas.append(echoarea[0])
    for echoarea in echoareas:
        if not echoarea in counts[node]:
            n = True
        else:
            if not echoarea in clone and int(remote_counts[echoarea]) - int(counts[node][echoarea]) > offset:
                offset = int(remote_counts[echoarea]) - int(counts[node][echoarea])
    if not n:
        depth = offset
    return depth

def get_msg_list(clone, ue, depth):
    msg_list = []
    fetch_echoareas = []
    echoareas = []
    for echoarea in nodes[node]["echoareas"]:
        if not echoarea[0] in ["favorites", "carbonarea"]:
            echoareas.append(echoarea[0])
    if ue:
        for echoarea in echoareas:
            if not echoarea in clone and (not echoarea in counts[node] or int(counts[node][echoarea]) < int(remote_counts[echoarea])):
                fetch_echoareas.append(echoarea)
    else:
        clone = echoareas
    if len(clone) > 0:
        r = urllib.request.Request(nodes[node]["node"] + "u/e/" + "/".join(clone))
        with urllib.request.urlopen(r) as f:
            lines = f.read().decode("utf-8").split("\n")
            for line in lines:
                if len(line) > 0:
                    msg_list.append(line)
    if len(fetch_echoareas) > 0 and int(depth) > 0:
        r = urllib.request.Request(nodes[node]["node"] + "u/e/" + "/".join(fetch_echoareas) + "/-%s:%s" %(depth, depth))
        with urllib.request.urlopen(r) as f:
            lines = f.read().decode("utf-8").split("\n")
            for line in lines:
                if len(line) > 0:
                    msg_list.append(line)
    return msg_list

def get_bundle(node, msgids):
    bundle = []
    try:
        r = urllib.request.Request(node + "u/m/" + msgids)
        with urllib.request.urlopen(r) as f:
            bundle = f.read().decode("utf-8").split("\n")
    except:
        None
    return bundle

def debundle(bundle):
    global messages
    for msg in bundle:
        if msg:
            m = msg.split(":")
            msgid = m[0]
            if len(msgid) == 20 and m[1]:
                msgbody = base64.b64decode(m[1].encode("ascii")).decode("utf8").split("\n")
                messages.append([msgid, msgbody])
                
    if len(messages) >= 1000:
        save_message(messages, nodes[node]["node"], nodes[node]["to"])
        messages = []

def echo_filter(ea):
    rr = re.compile(r'^[a-z0-9_!.-]{1,60}\.[a-z0-9_!.-]{1,60}$')
    if rr.match(ea): return True

def get_mail(clone, ue, depth):
    fetch_msg_list = []
    print("Получение индекса от ноды...")
    remote_msg_list = get_msg_list(clone, ue, depth)
    print("Построение разностного индекса...")
    for line in remote_msg_list:
        if echo_filter(line):
            if line in clone and ue:
                remove_echoarea(line)
            local_index = get_echo_msgids(line)
        else:
            if not line in local_index:
                fetch_msg_list.append(line)
    msg_list_len = str(len(fetch_msg_list))
    if len(fetch_msg_list) > 0:
        count = 0
        for get_list in separate(fetch_msg_list):
            count = count + len(get_list)
            print("\rПолучение сообщений: " + str(count) + "/"  + msg_list_len, end="")
            debundle(get_bundle(nodes[node]["node"], "/".join(get_list)))
        save_message(messages, node, nodes[node]["to"])
    else:
        print("Новых сообщений не обнаружено.", end="")
    print()

def get_local_fecho(fecho):
    index = []
    try:
        for f in open("fecho/%s.txt" % fecho, "r").read().split("\n"):
            if len(f) > 0:
                index.append(f)
    except:
        None
    return index

def get_remote_fecho():
    index = []
    try:
        r = urllib.request.Request(nodes[node]["node"] + "f/e/" + "/".join(nodes[node]["fechoareas"]))
        with urllib.request.urlopen(r) as f:
            for row in f.read().decode("utf8").split("\n"):
                if len(row) > 0: # and not row in nodes[node]["fechoareas"]:
                    index.append(row)
    except:
        None
    return index

def download_file(fi):
    r = urllib.request.Request("%sf/f/%s/%s" % (nodes[node]["node"], fi[0], fi[1].split(":")[0]))
    out = urllib.request.urlopen(r)
    file_size=0
    block_size=8192

    if not os.path.exists("fecho/%s" % fi[0]):
        os.mkdir("fecho/%s" % fi[0])
    f = open("fecho/%s/%s" % (fi[0], fi[1].split(":")[1]), "wb")
    while True:
        buffer = out.read(block_size)
        if not buffer:
            break
        file_size += len(buffer)
        f.write(buffer)
    f.close()
    codecs.open("fecho/%s.txt" % fi[0], "a", "utf8").write(fi[1] + "\n")

def get_fecho():
    print("Получение индекса файлэх.")
    remote_index = get_remote_fecho()
    print("Построение разностного индекса.")
    local_index = []
    index = []
    for fecho in nodes[node]["fechoareas"]:
        local_fecho = get_local_fecho(fecho)
        for fid in local_fecho:
            local_index.append(fid)
    for fi in remote_index:
        if not ":" in fi:
            fecho = fi
        elif not fi in local_index:
            index.append([fecho, fi])
    if len(index) == 0:
        print("Новых файлов не обнаружено.")
        return False
    else:
        ret = []
        for fi in index:
            row = fi[1].split(":")
            print("Получение файла %s" % row[1], end=" ")
            try:
                download_file(fi)
                print("OK")
                ret.append([fi[0], row[1], row[2], row[4]])
            except:
                print("ERROR")
        return ret

def mailer(clone):
    global depth, messages
    messages = []
    print("Работа с " + nodes[node]["node"])
    if nodes[node]["auth"]:
        make_toss()
        send_mail()
        print("Получение списка возможностей ноды...")
        features = get_features()
        ue, xc, f = check_features(features)
        if xc:
            counts = load_counts()
            print("Получение количества сообщений в конференциях...")
            remote_counts = get_remote_counts()
            depth = calculate_offset(depth)
    get_mail(clone, ue, depth)
    if f:
        fecho = get_fecho()
        if fecho:
            s = []
            fe = ""
            for f in fecho:
                if fe != f[0]:
                    if not fe == "":
                        s.append("----\n")
                    fe = f[0]
                    s.append("== Файлэха %s:" % fe)
                if int(f[2]) < 1024:
                    size = str(f[2]) + " B"
                elif int(f[2]) >= 1024 and int(f[2]) < 1048576:
                    size = str(int(int(f[2]) / 1024 * 10) / 10) + " KB"
                else:
                    size = str(int(int(f[2]) / 1048576 * 10) / 10) + " MB"
                s.append("Файл:     " + f[1])
                s.append("Размер:   " + size)
                s.append("Описание: " + f[3])
                s.append("")
                codecs.open("fecho/%s/%s.txt" % (fe, ".".join(f[1].split(".")[:-1])), "w", "utf-8").write(f[3])
            save_to_carbonarea("fetcher", "Новые файлы", "\n".join(s))
    if xc:
        save_counts(counts, remote_counts)
    input("Нажмите Enter для продолжения.")

#
# Пользовательский интерфейс
#

echo_cursor = 0
archive_cursor = 0
width = 0
height = 0
show_splash = True

def splash_screen():
    stdscr.clear()
    x = int((width - len(splash[1])) / 2) - 1
    y = int((height - len(splash)) / 2)
    i = 0
    for line in splash:
        stdscr.addstr(y + i, x, line, curses.color_pair(4))
        i = i + 1
    stdscr.refresh()
    curses.napms(2000)
    stdscr.clear()

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

def draw_status(x, title):
    if bold[8]:
        color = curses.color_pair(9) + curses.A_BOLD
    else:
        color = curses.color_pair(9)
    stdscr.addstr(height - 1, x, title, color)

def draw_cursor(y, color):
    for i in range (0, width):
        stdscr.insstr(y + 1, i, " ", color)

def current_time():
    draw_status(width - 8, "│ " + datetime.now().strftime("%H:%M"))

def get_counts(new = False, favorites = False):
    global echo_counts
    for echoarea in nodes[node]["echoareas"]:
        if not new:
            if not echoarea[0] in echo_counts:
                echo_counts[echoarea[0]] = get_echo_length(echoarea[0])
        else:
            echo_counts[echoarea[0]] = get_echo_length(echoarea[0])
    for echoarea in nodes[node]["archive"]:
        if not echoarea[0] in echo_counts:
            echo_counts[echoarea[0]] = get_echo_length(echoarea[0])
    echo_counts["carbonarea"] = len(get_carbonarea())
    echo_counts["favorites"] = len(get_favorites_list())

def rescan_counts(echoareas):
    counts = []
    for echo in echoareas:
        try:
            echocount = echo_counts[echo[0]]
            if echo[0] in lasts: 
                last = echocount - lasts[echo[0]]
                if echocount == 0 and lasts[echo[0]] == 0:
                    last = 1
            else:
                last = echocount + 1
        except:
            echocount = 0
            last = 1
        if last - 1 < 0:
            last = 1
        counts.append([str(echocount), str(last - 1)])
    return counts

def draw_echo_selector(start, cursor, archive):
    global counts, counts_rescan
    dsc_lens = []
    hidedsc = False
    m = 0
    if bold[0]:
        stdscr.attron(curses.color_pair(1))
        stdscr.attron(curses.A_BOLD)
    else:
        stdscr.attron(curses.color_pair(1))
    for i in range(0, width):
        if bold[0]:
            color = curses.color_pair(1) + curses.A_BOLD
        else:
            color = curses.color_pair(1)
        stdscr.insstr(0, i, "─", color)
        if bold[2]:
            color = curses.color_pair(9) + curses.A_BOLD
        else:
            color = curses.color_pair(9)
        stdscr.insstr(height - 1, i, " ", color)
    if archive:
        echoareas = nodes[node]["archive"]
        draw_title(0, 0, "Архив")
    else:
        echoareas = nodes[node]["echoareas"]
        draw_title(0, 0, "Конференция")
    draw_status(1, version)
    draw_status(len(version) + 2, nodes[node]["nodename"])
    for echo in echoareas:
        l = len(echo[1])
        if l > m:
            m = l
        if m > width - 38:
            m = width - 38
        dsc_lens.append(l)
    y = 0
    count = "Сообщений"
    unread = "Не прочитано"
    description = "Описание"
    if width < 80 or m == 0:
        m = len(unread) - 7
        hidedsc = True
    draw_title(0, width + 2 - m - len(count) - len(unread) - 1, count)
    draw_title(0, width - 8 - m - 1, unread)
    if not hidedsc:
        draw_title(0, width - len(description) - 2, description)
    for echo in echoareas:
        if y - start < height - 2:
            if y == cursor:
                if y >= start:
                    if bold[2]:
                        color = curses.color_pair(3) + curses.A_BOLD
                        stdscr.attron (curses.color_pair(3))
                        stdscr.attron (curses.A_BOLD)
                    else:
                        color = curses.color_pair(3)
                        stdscr.attron (curses.color_pair(3))
                        stdscr.attroff (curses.A_BOLD)
                    draw_cursor(y - start, color)
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
                if counts_rescan:
                    counts = rescan_counts(echoareas)
                    counts_rescan = False
                echo_length = int(counts[y][0])
                if echo[0] in lasts:
                    last = lasts[echo[0]]
                else:
                    last = -1
                if last < echo_length - 1 or last == -1 and echo_length == 1:
                    stdscr.addstr(y + 1 - start, 0, "+")
                if last < 0:
                    last = 0
                if echo[0] in nodes[node]["clone"]:
                    stdscr.addstr(y + 1 - start, 1, "*")
                stdscr.addstr(y + 1 - start, 2, echo[0])
                if width >= 80:
                    if width - 38 >= len(echo[1]):
                        stdscr.addstr(y + 1 - start, width - 1 - dsc_lens[y], echo[1], color)
                    else:
                        cut_index = width - 38 - len(echo[1])
                        stdscr.addstr(y + 1 - start, width - 1 - len(echo[1][:cut_index]), echo[1][:cut_index])
                stdscr.addstr(y + 1 - start, width - 10 - m - len(counts[y][0]), counts[y][0])
                stdscr.addstr(y + 1 - start, width - 2 - m - len(counts[y][1]), counts[y][1])
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

def fetch_mail():
    curses.echo()
    curses.curs_set(True)
    curses.endwin()
    os.system('cls' if os.name == 'nt' else 'clear')
    echoareas = []
    to = ""
    if len(nodes[node]["to"]) > 0:
        to = "\"" + ",".join(nodes[node]["to"]) + "\""
    else:
        to = False
    d = "txt"
    if db == 1:
        d = "aio"
    elif db == 2:
        d = "ait"
    elif db == 3:
        d = "sqlite"
    for echoarea in nodes[node]["echoareas"][2:]:
        if not echoarea[2]:
            echoareas.append(echoarea[0])
    mailer(nodes[node]["clone"])
    nodes[node]["clone"] = []
    stdscr = curses.initscr()
    curses.start_color()
    curses.noecho()
    curses.curs_set(False)
    stdscr.keypad(True)
    get_term_size()

def load_lasts():
    global lasts
    if os.path.exists("lasts.lst"):
        f = open("lasts.lst", "rb")
        lasts = pickle.load(f)
        f.close()

def edit_config(out = False):
    curses.echo()
    curses.curs_set(True)
    curses.endwin()
    p = subprocess.Popen(editor + " ./caesium.cfg", shell=True)
    p.wait()
    reset_config()
    load_config()
    stdscr = curses.initscr()
    curses.start_color()
    curses.noecho()
    curses.curs_set(False)
    stdscr.keypad(True)
    get_term_size()

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
        elif key in s_up and cursor > 0:
            cursor = cursor - 1
            if cursor - start < 0 and start > 0:
                start = start - 1
        elif key in s_down and cursor < len(echoareas) - 1:
            cursor = cursor + 1
            if cursor - start > height - 3 and start < len(echoareas) - height + 2:
                start = start + 1
        elif key in s_ppage:
            cursor = cursor - height + 2
            if cursor < 0:
                cursor = 0
            if cursor - start < 0 and start > 0:
                start = start - height + 2
            if start < 0:
                start = 0
        elif key in s_npage:
            cursor = cursor + height - 2
            if cursor >= len(echoareas):
                cursor = len(echoareas) - 1
            if cursor - start > height - 3:
                start = start + height - 2
                if start > len(echoareas) - height + 2:
                    start = len(echoareas) - height + 2
        elif key in s_home:
            cursor = 0
            start = 0
        elif key in s_end:
            cursor = len(echoareas) - 1
            if len(echoareas) >= height - 2:
                start = len(echoareas) - height + 2
        elif key in s_get:
            fetch_mail()
            draw_message_box("Подождите", False)
            get_counts(True)
            stdscr.clear()
            counts = rescan_counts(echoareas)
            cursor = find_new(0)
            if cursor >= height - 2:
                start = cursor - height + 3
        elif key in s_archive and len(nodes[node]["archive"]) > 0:
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
        elif key in s_enter:
            draw_message_box("Подождите", False)
            if echoareas[cursor][0] in lasts:
                last = lasts[echoareas[cursor][0]]
            else:
                last = 0
            if cursor == 0:
                echo_length = len(get_favorites_list())
            elif cursor == 1:
                echo_length = len(get_carbonarea())
            else:
                echo_length = get_echo_length(echoareas[cursor][0])
            if last > 0 and last < echo_length:
                last = last + 1
            if last >= echo_length:
                last = echo_length
            if cursor == 1:
                go = not echo_reader(echoareas[cursor], last, archive, True, False, True)
            elif cursor == 0 or echoareas[cursor][2]:
                go = not echo_reader(echoareas[cursor], last, archive, True, False, False)
            else:
                go = not echo_reader(echoareas[cursor], last, archive, False, False, False)
            counts_rescan = True
            if next_echoarea:
                counts = rescan_counts(echoareas)
                cursor = find_new(cursor)
                if cursor - start > height - 3:
                    start = cursor - height + 3
                next_echoarea = False
        elif key in s_out:
            out_length = get_out_length()
            if out_length > -1:
                go = not echo_reader("out", out_length, archive, False, True, False)
        elif key in s_drafts:
            out_length = get_out_length(True)
            if out_length > -1:
                go = not echo_reader("out", out_length, archive, False, True, False, True)
        elif key in s_nnode:
            archive = False
            node = node + 1
            if node == len(nodes):
                node = 0
            echoareas = nodes[node]["echoareas"]
            draw_message_box("Подождите", False)
            get_counts()
            stdscr.clear()
            counts_rescan = True
            cursor = 0
            start = 0
        elif key in s_pnode:
            archive = False
            node = node - 1
            if node == -1:
                node = len(nodes) - 1
            echoareas = nodes[node]["echoareas"]
            draw_message_box("Подождите", False)
            get_counts()
            stdscr.clear()
            counts_rescan = True
            cursor = 0
            start = 0
        elif key in s_clone:
            if cursor > 1 and not echoareas[cursor][2]:
                if echoareas[cursor][0] in nodes[node]["clone"]:
                    nodes[node]["clone"].remove(echoareas[cursor][0])
                else:
                    nodes[node]["clone"].append(echoareas[cursor][0])
        elif key in s_config:
            edit_config()
            reset_config()
            load_config()
            load_colors()
            get_counts()
            stdscr.clear()
            counts_rescan = True
            node = 0
            archive = False
            echoareas = nodes[node]["echoareas"]
            cursor = 0
        elif key in g_quit:
            go = False
    if archive:
        archive_cursor = cursor
    else:
        echo_cursor = cursor

def read_out_msg(msgid):
    size = "0b"
    temp = open("out/" + nodes[node]["nodename"] + "/" + msgid, "r").read().split("\n")
    msg = []
    msg.append("")
    msg.append(temp[0])
    msg.append("")
    msg.append("")
    msg.append("")
    msg.append(temp[1])
    msg.append(temp[2])
    for line in temp[3:]:
        if not(line.startswith("@repto:")):
               msg.append(line)
    size = os.stat("out/" + nodes[node]["nodename"] + "/" + msgid).st_size
    if size < 1024:
        size = str(size) + " B"
    else:
        size = str(int(size / 1024 * 10) / 10) + " KB"
    return msg, size

def body_render(tbody):
    body = ""
    code = ""
    sep = ""
    for i in range(0, width - 1):
        sep += "─"
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
        elif line.startswith("== "):
            code = chr(18)
        else:
            code = " "
        if line == "----":
            code = chr(17)
            line = sep 
        if code != " " and code != chr(17) and code != chr(18):
            line = " " + line
        body = body + code
        for word in line.split(" "):
            if n + len(word) < width:
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
                    chunks, chunksize = len(word), width - 1
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

def draw_reader(echo, msgid, out):
    for i in range(0, width):
        if bold[0]:
            color = curses.color_pair(1) + curses.A_BOLD
        else:
            color = curses.color_pair(1)
        stdscr.insstr(0, i, "─", color)
        stdscr.insstr(4, i, "─", color)
        if bold[2]:
            color = curses.color_pair(9) + curses.A_BOLD
        else:
            color = curses.color_pair(9)
        stdscr.insstr(height - 1, i, " ", color)
    if out:
        draw_title(0, 0, echo)
        if msgid.endswith(".out"):
            ns = "не отправлено"
            draw_title(4, width - len(ns) - 2, ns)
    else:
        if width >= 80:
            draw_title(0, 0, echo + " / " + msgid)
        else:
            draw_title(0, 0, echo)
    draw_status(1, version)
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


def call_editor(out = False, draft = False):
    curses.echo()
    curses.curs_set(True)
    curses.endwin()
    h = hashlib.sha1(str.encode(open("temp", "r",).read())).hexdigest()
    p = subprocess.Popen(editor + " ./temp", shell=True)
    p.wait()
    stdscr = curses.initscr()
    curses.start_color()
    curses.noecho()
    curses.curs_set(False)
    stdscr.keypad(True)
    get_term_size()
    if h != hashlib.sha1(str.encode(open("temp", "r",).read())).hexdigest():
        d = menu("Куда сохранить?", ["Сохранить в исходящие", "Сохранить как черновик"])
        if d:
            if d == 2:
                if not out:
                    save_out(True)
                else:
                    if out.endswith(".out"):
                        try:
                            os.remove("out/" + nodes[node]["nodename"] + "/" + out)
                        except:
                            None
                    resave_out(out, True)
            elif d == 1:
                if not out:
                    save_out()
                else:
                    if out.endswith(".draft"):
                        try:
                            os.remove("out/" + nodes[node]["nodename"] + "/" + out)
                        except:
                            None
                    resave_out(out.replace(".draft", ".out"))
    else:
        os.remove("temp")

def draw_message_box(smsg, wait):
    maxlen = 0
    msg = smsg.split("\n")
    for line in msg:
        if len(line) > maxlen:
            maxlen = len(line)
    if wait:
        msgwin = curses.newwin(len(msg) + 4, maxlen + 2, int(height / 2 - 2) , int(width / 2 - maxlen / 2 - 2))
    else:
        msgwin = curses.newwin(len(msg) + 2, maxlen + 2, int(height / 2 - 2) , int(width / 2 - maxlen / 2 - 2))
    if bold[0]:
        msgwin.attron(curses.color_pair(1))
        msgwin.attron(curses.A_BOLD)
    else:
        msgwin.attron(curses.color_pair(1))
    msgwin.bkgd(' ', curses.color_pair(1))
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
    if wait:
        msgwin.addstr(len(msg) + 2, int((maxlen + 2 - 21) / 2), "Нажмите любую клавишу", color)
    msgwin.refresh()

def message_box(smsg):
    draw_message_box(smsg, True)
    stdscr.getch()
    stdscr.clear()

def save_message_to_file(msgid, echoarea):
    msg, size = read_msg(msgid, echoarea)
    f = open(msgid + ".txt", "w")
    f.write("== " + msg[1] + " ==================== " + str(msgid) + "\n")
    f.write("От:   " + msg[3] + " (" + msg[4] + ")\n")
    f.write("Кому: " + msg[5] + "\n")
    f.write("Тема: " + msg[6] + "\n")
    f.write("\n".join(msg[7:]))
    f.close
    message_box("Сообщение сохранено в файл\n" + str(msgid) + ".txt")

def get_out_msgids(drafts = False):
    msgids = []
    not_sended = []
    if os.path.exists("out/" + nodes[node]["nodename"]):
        if drafts:
            msgids = [f for f in sorted(os.listdir("out/" + nodes[node]["nodename"])) if f.endswith(".draft")]
        else:
            msgids = [f for f in sorted(os.listdir("out/" + nodes[node]["nodename"])) if f.endswith(".out") or f.endswith(".outmsg")]
    return msgids

def quote(to):
    if oldquote == True:
        return ""
    else:
        if len(to) == 1:
            q = to[0]
        else:
            q = ""
            for word in to:
                q = q + word[0]
        return q

def show_subject(subject):
    if len(subject) > width - 8:
        msg = ""
        line = ""
        for word in subject.split(" "):
            if len(line + word) <= width - 4:
                line = line + word + " "
            else:
                msg = msg + line + "\n"
                line = word + " "
        msg = msg + line
        message_box(msg)

def calc_scrollbar_size(length):
    if length > 0:
        scrollbar_size = round((height - 6) * (height - 6) / length + 0.49)
        if scrollbar_size < 1:
            scrollbar_size = 1
    else:
        scrollbar_size = 1
    return scrollbar_size

def set_attr(str):
    if str == chr(15):
        stdscr.attron(curses.color_pair(5))
        if bold[4]:
            stdscr.attron(curses.A_BOLD)
        else:
            stdscr.attroff(curses.A_BOLD)
    elif str == chr(16):
        stdscr.attron(curses.color_pair(6))
        if bold[5]:
            stdscr.attron(curses.A_BOLD)
        else:
            stdscr.attroff(curses.A_BOLD)
    elif str == chr(17):
        stdscr.attron(curses.color_pair(7))
        if bold[6]:
            stdscr.attron(curses.A_BOLD)
        else:
            stdscr.attroff(curses.A_BOLD)
    elif str == chr(18):
        stdscr.attron(curses.color_pair(10))
        if bold[9]:
            stdscr.attron(curses.A_BOLD)
        else:
            stdscr.attroff(curses.A_BOLD)
    else:
        stdscr.attron(curses.color_pair(4))
        if bold[3]:
            stdscr.attron(curses.A_BOLD)
        else:
            stdscr.attroff(curses.A_BOLD)

def get_msg(msgid):
    r = urllib.request.Request(nodes[node]["node"] + "u/m/" + msgid)
    with urllib.request.urlopen(r) as f:
        bundle = f.read().decode("utf-8").split("\n")
    for msg in bundle:
        if msg:
            m = msg.split(":")
            msgid = m[0]
            if len(msgid) == 20 and m[1]:
                msgbody = base64.b64decode(m[1].encode("ascii")).decode("utf8")
                if len(nodes[node]["to"]) > 0:
                    carbonarea = get_carbonarea()
                    if msgbody.split("\n")[5] in nodes[node]["to"] and not msgid in carbonarea:
                        add_to_carbonarea(msgid, msbbody)
                save_message(msgid, msgbody)

def menu(title, items):
    h = len(items)
    w = 0
    for item in items:
        if len(item) > w:
            w = len(item)
        if len(item) > width - 2:
            item = item[:width - 1]
    if w >= width - 3:
        w = width - 3
    e = "Esc - отмена"
    if w < len(title):
        w = len(title) + 2
    menu_win = curses.newwin(h + 2, w + 2, int(height / 2 - h / 2 - 2) , int(width / 2 - w / 2 - 2))
    if bold[0]:
        menu_win.attron(curses.color_pair(1))
        menu_win.attron(curses.A_BOLD)
    else:
        menu_win.attron(curses.color_pair(1))
    menu_win.border()
    if bold[0]:
        color = curses.color_pair(1) + curses.A_BOLD
    else:
        color = curses.color_pair(1)
    menu_win.addstr(0, 1, "[", color)
    menu_win.addstr(0, 2 + len(title), "]", color)
    menu_win.addstr(h + 1, 1, "[", color)
    menu_win.addstr(h + 1, 2 + len(e), "]", color)
    if bold[1]:
        color = curses.color_pair(2) + curses.A_BOLD
    else:
        color = curses.color_pair(2)
    menu_win.addstr(0, 2, title, curses.color_pair(2) + curses.A_BOLD)
    menu_win.addstr(h + 1, 2, e, curses.color_pair(2) + curses.A_BOLD)
    if bold[0]:
        color = curses.color_pair(1) + curses.A_BOLD
    else:
        color = curses.color_pair(1)
    y = 1
    quit = False
    cancel = False
    while not quit:
        i = 1
        for item in items:
            if i == y :
                if bold[2]:
                    color = curses.color_pair(3) + curses.A_BOLD
                else:
                    color = curses.color_pair(3)
                for x in range(1, w + 1):
                    menu_win.addstr(i, x, " ", color)
            else:
                if bold[3]:
                    color = curses.color_pair(4) + curses.A_BOLD
                else:
                    color = curses.color_pair(4)
                for x in range(1, w + 1):
                    menu_win.addstr(i, x, " ", color)
            if len(item) < w - 2:
                menu_win.addstr(i, 1, item, color)
            else:
                menu_win.addstr(i, 1, item[:w], color)
            i = i + 1
        menu_win.refresh()
        key = stdscr.getch()
        if key in r_up:
            if y > 1:
                y -= 1
            else:
                y = h
        elif key in r_down:
            if y < h:
                y += 1
            else:
                y = 1
        elif key in s_enter:
            quit = True
        elif key in r_quit:
            cancel = True
            quit = True
    if cancel:
        return False
    else:
        return y

def open_link(link):
    global browser
    browser.open(link)

def get_out(drafts=False):
    if drafts:
        return get_out_msgids(True)
    else:
        return get_out_msgids()

def echo_reader(echo, last, archive, favorites, out, carbonarea, drafts = False):
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
    if drafts:
        msgids = get_out_msgids(True)
    elif out:
        msgids = get_out_msgids()
    elif favorites and not carbonarea:
        msgids = get_favorites_list()
    elif carbonarea:
        msgids = get_carbonarea()
    else:
        msgids = get_echo_msgids(echo[0])
    if msgn > len(msgids) - 1:
        msgn = len(msgids) - 1
    if len(msgids) > 0:
        if drafts:
            msg, size = read_out_msg(msgids[msgn])
        elif out:
            msg, size = read_out_msg(msgids[msgn])
        else:
            msg, size = read_msg(msgids[msgn], echo[0])
    else:
        msg = ["", "", "", "", "", "", "", "", "Сообщение отсутствует в базе"]
        size = "0b"
    msgbody = body_render(msg[8:])
    scrollbar_size = calc_scrollbar_size(len(msgbody))
    go = True
    stack = []
    while go:
        if len(msgids) > 0:
            draw_reader(msg[1], msgids[msgn], out)
            if width >= 80:
                msg_string = "Сообщение " + str(msgn + 1) + " из " + str(len(msgids)) + " (" + str(len(msgids) - msgn - 1) + " осталось)"
            else:
                msg_string = str(msgn + 1) + "/" + str(len(msgids)) + " [" + str(len(msgids) - msgn - 1) + "]"
            draw_status(len(version) + 2, msg_string)
            if drafts:
                dsc = "Черновики"
            elif out:
                dsc = "Исходящие"
            else:
                dsc = echo[1]
            if len(dsc) > 0 and width >= 80:
                draw_title(0, width - 2 - len(dsc), dsc)
            if not(out):
                try:
                    if width >= 80:
                        msgtime = time.strftime("%Y.%m.%d %H:%M UTC", time.gmtime(int(msg[2])))
                    else:
                        msgtime = time.strftime("%Y.%m.%d %H:%M", time.gmtime(int(msg[2])))
                except:
                    msgtime = ""
            if bold[3]:
                color = curses.color_pair(4) + curses.A_BOLD
            else:
                color = curses.color_pair(4)
            if not(out):
                if width >= 80:
                    stdscr.addstr(1, 7, msg[3] + " (" + msg[4] + ")", color)
                else:
                    stdscr.addstr(1, 7, msg[3], color)
                stdscr.addstr(1, width  - len(msgtime) - 1, msgtime, color)
            else:
                if len(nodes[node]["to"]) > 0:
                    stdscr.addstr(1, 7, nodes[node]["to"][0], color)
            stdscr.addstr(2, 7, msg[5], color)
            stdscr.addstr(3, 7, msg[6][:width - 8], color)
            draw_title(4, 0, size) 
            tags = msg[0].split("/")
            if "repto" in tags and 36 + len(size) < width:
                repto = tags[tags.index("repto") + 1]
                draw_title(4, len(size) + 3, "Ответ на " + repto)
            else:
                repto = False
            for i in range (0, height - 6):
                for x in range (0, width):
                    stdscr.addstr(i + 5, x, " ", 1)
                if i < len(msgbody) - 1:
                    if y + i < len(msgbody) and len(msgbody[y+i]) > 0:
                        set_attr(msgbody[y + i][0])
                        x = 0
                        for word in msgbody[y + i][1:].split(" "):
                            if word.startswith("http://") or word.startswith("https://") or word.startswith("ftp://"):
                                stdscr.attron(curses.color_pair(8))
                                if bold[7]:
                                    stdscr.attron(curses.A_BOLD)
                                else:
                                    stdscr.attroff(curses.A_BOLD)
                                stdscr.addstr(i + 5, x, word)
                                set_attr(msgbody[y + i][0])
                            else:
                                stdscr.addstr(i + 5, x, word)
                            x += len(word) + 1
            stdscr.attron(curses.color_pair(11))
            if bold[10]:
                stdscr.attron(curses.A_BOLD)
            else:
                stdscr.attroff(curses.A_BOLD)
            if len(msgbody) > height - 5:
                for i in range(5, height - 1):
                    stdscr.addstr(i, width - 1, "░")
                scrollbar_y = round(y * (height - 6) / len(msgbody) + 0.49)
                if scrollbar_y < 0:
                    scrollbar_y = 0
                elif scrollbar_y > height - 6 - scrollbar_size or y >= len(msgbody) - (height - 6):
                    scrollbar_y = height - 6 - scrollbar_size
                for i in range(scrollbar_y + 5, scrollbar_y + 5 + scrollbar_size):
                    if i < height - 1:
                        stdscr.addstr(i, width - 1, "█")
        else:
            draw_reader(echo[0], "", out)
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
                scrollbar_size = calc_scrollbar_size(len(msgbody))
            stdscr.clear()
        elif key in r_prev and msgn > 0:
            y = 0
            if len(msgids) > 0:
                msgn = msgn - 1
                if len(stack) > 0:
                    stack = []
                if out:
                    msg, size = read_out_msg(msgids[msgn])
                else:
                    msg, size = read_msg(msgids[msgn], echo[0])
                msgbody = body_render(msg[8:])
                scrollbar_size = calc_scrollbar_size(len(msgbody))
        elif key in r_next and msgn < len(msgids) - 1:
            y = 0
            if len(msgids) > 0:
                msgn = msgn +1
                if len(stack) > 0:
                    stack = []
                if out:
                    msg, size = read_out_msg(msgids[msgn])
                else:
                    msg, size = read_msg(msgids[msgn], echo[0])
                msgbody = body_render(msg[8:])
                scrollbar_size = calc_scrollbar_size(len(msgbody))
        elif key in r_next and (msgn == len(msgids) - 1 or len(msgids) == 0):
            go = False
            quit = False
            next_echoarea = True
        elif key in r_prep and not echo[0] == "carbonarea" and not echo[0] == "favorites" and not out and repto:
            if repto in msgids:
                stack.append(msgn)
                msgn = msgids.index(repto)
                msg, size = read_msg(msgids[msgn], echo[0])
                msgbody = body_render(msg[8:])
                scrollbar_size = calc_scrollbar_size(len(msgbody))
        elif key in r_nrep and not out and len(stack) > 0:
            msgn = stack.pop()
            msg, size = read_msg(msgids[msgn], echo[0])
            msgbody = body_render(msg[8:])
            scrollbar_size = calc_scrollbar_size(len(msgbody))
        elif key in r_up and y > 0:
            if len(msgids) > 0:
                y = y - 1
        elif key in r_ppage:
            if len(msgids) > 0:
                y = y - height + 6
                if y < 0:
                    y = 0
        elif key in r_npage:
            if y < len(msgbody) - height + 5:
                if len(msgids) > 0 and len(msgbody) > height - 5:
                    y = y + height - 6
        elif key in r_home:
            if len(msgids) > 0:
                y = 0
        elif key in r_mend:
            if len(msgids) > 0 and len(msgbody) > height - 5:
                y = len(msgbody) - height + 5
        elif key in r_ukeys:
            if len(msgids) == 0 or y >= len(msgbody) - height + 5:
                y = 0
                if msgn == len(msgids) - 1 or len(msgids) == 0:
                    next_echoarea = True
                    go = False
                    quit = False
                else:
                    msgn = msgn +1
                    if len(stack) > 0:
                        stack = []
                    if out:
                        msg, size = read_out_msg(msgids[msgn])
                    else:
                        msg, size = read_msg(msgids[msgn], echo[0])
                    msgbody = body_render(msg[8:])
                    scrollbar_size = calc_scrollbar_size(len(msgbody))
            else:
                if len(msgids) > 0 and len(msgbody) > height - 5:
                    y = y + height - 6
        elif key in r_down:
            if len(msgids) > 0:
                if y + height - 5 < len(msgbody):
                    y = y + 1
        elif key in r_begin:
            if len(msgids) > 0:
                y = 0
                msgn = 0
                if len(stack) > 0:
                    stack = []
                if out:
                    msg, size = read_out_msg(msgids[msgn])
                else:
                    msg, size = read_msg(msgids[msgn], echo[0])
                msgbody = body_render(msg[8:])
                scrollbar_size = calc_scrollbar_size(len(msgbody))
        elif key in r_end:
            if len(msgids) > 0:
                y = 0
                msgn = len(msgids) - 1
                if len(stack) > 0:
                    stack = []
                if out:
                    msg, size = read_out_msg(msgids[msgn])
                else:
                    msg, size = read_msg(msgids[msgn], echo[0])
                msgbody = body_render(msg[8:])
                scrollbar_size = calc_scrollbar_size(len(msgbody))
        elif (key in r_ins) and not archive and not out:
            if not favorites:
                f = open("temp", "w")
                f.write(echo[0] + "\n")
                f.write("All\n")
                f.write("No subject\n\n")
                f.close()
                call_editor()
                stdscr.clear()
        elif key in r_save and not out:
            save_message_to_file(msgids[msgn], echo[0])
        elif key in r_favorites and not out:
            saved = save_to_favorites(msgids[msgn], msg)
            draw_message_box("Подождите", False)
            get_counts(False, True)
            if saved:
                message_box("Собщение добавлено в избранные")
            else:
                message_box("Собщение уже есть в избранных")
        elif (key in r_quote) and not archive and not out:
            if len(msgids) > 0:
                f = open("temp", "w")
                f.write(msgids[msgn] + "\n")
                f.write(msg[1] + "\n")
                f.write(msg[3] + "\n")
                to = msg[3].split(" ")
                q = quote(to)
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
        elif key in r_subj:
            show_subject(msg[6])
        elif key in r_info and not out and width < 80:
            message_box("id  : " + msgids[msgn] + "\naddr: " + msg[4])
        elif key in o_edit and out:
            if msgids[msgn].endswith(".out") or msgids[msgn].endswith(".draft"):
                copyfile("out/" + nodes[node]["nodename"] + "/" + msgids[msgn], "temp")
                if drafts:
                    call_editor(msgids[msgn], drafts)
                    msgids = get_out(True)
                else:
                    call_editor(msgids[msgn])
                    msgids = get_out()
                if msgn > len(msgids) - 1:
                    msgn = len(msgids) -1
                if len(msgids) > 0:
                    msg, size = read_out_msg(msgids[msgn])
                    msgbody = body_render(msg[8:])
                else:
                    go = False
                    quit = False
                scrollbar_size = calc_scrollbar_size(len(msgbody))
                stdscr.clear()
            else:
                message_box("Сообщение уже отправлено")
                stdscr.clear()
        elif key in f_delete and favorites and not carbonarea:
            if len(msgids) > 0:
                remove_from_favorites(msgids[msgn])
                draw_message_box("Подождите", False)
                get_counts(False, True)
                msgids = get_echo_msgids(echo[0])
                if len(msgids) > 0:
                    if msgn >= len(msgids):
                        msgn = len(msgids) - 1
                    msg, size = read_msg(msgids[msgn], echo[0])
                    msgbody = body_render(msg[8:])
                    scrollbar_size = calc_scrollbar_size(len(msgbody))
                else:
                    msgbody = []
                stdscr.clear()
        elif key in r_getmsg and size == "0b":
            try:
                get_msg(msgids[msgn])
                draw_message_box("Подождите", False)
                get_counts(True, False)
                stdscr.clear()
                msg, size = read_msg(msgids[msgn], echo[0])
                msgbody = body_render(msg[8:])
                scrollbar_size = calc_scrollbar_size(len(msgbody))
            except:
                message_box("Не удалось определить msgid.")
                stdscr.clear()
        elif key in r_links:
            results = urltemplate.findall("\n".join(msg[8:]))
            links = []
            for item in results:
                links.append(item[0])
            if len(links) == 1:
                open_link(links[0])
            else:
                i = menu("Выберите ссылку", links)
                if i:
                    open_link(links[i - 1])
            stdscr.clear()
        elif key in r_to_out and drafts:
            copyfile("out/" + nodes[node]["nodename"] + "/" + msgids[msgn], "out/" + nodes[node]["nodename"] + "/" + msgids[msgn].replace(".draft", ".out"))
            os.remove("out/" + nodes[node]["nodename"] + "/" + msgids[msgn])
            if drafts:
                msgids = get_out(True)
            else:
                msgids = get_out()
            if msgn > len(msgids) - 1:
                msgn = len(msgids) -1
            if len(msgids) > 0:
                msg, size = read_out_msg(msgids[msgn])
                msgbody = body_render(msg[8:])
            else:
                go = False
                quit = False
        elif key in r_to_drafts and out and not drafts and msgids[msgn].endswith(".out"):
            copyfile("out/" + nodes[node]["nodename"] + "/" + msgids[msgn], "out/" + nodes[node]["nodename"] + "/" + msgids[msgn].replace(".out", ".draft"))
            os.remove("out/" + nodes[node]["nodename"] + "/" + msgids[msgn])
            if drafts:
                msgids = get_out(True)
            else:
                msgids = get_out()
            if msgn > len(msgids) - 1:
                msgn = len(msgids) -1
            if len(msgids) > 0:
                msg, size = read_out_msg(msgids[msgn])
                msgbody = body_render(msg[8:])
            else:
                go = False
                quit = False
        elif key in r_list and not out and not drafts:
            if db == 0:
                message_box("Функция не поддерживается текстовой базой.")
            else:
                l = msg_list(echo, msgids, msgn)
                if l > -1:
                    y = 0
                    msgn = l
                    if len(stack) > 0:
                        stack = []
                    msg, size = read_msg(msgids[msgn], echo[0])
                    msgbody = body_render(msg[8:])
                    scrollbar_size = calc_scrollbar_size(len(msgbody))
        elif key in r_quit:
            go = False
            quit = False
            next_echoarea = False
        elif key in g_quit:
            go = False
            quit = True
    lasts[echo[0]] = msgn
    f = open("lasts.lst", "wb")
    pickle.dump(lasts, f)
    f.close()
    stdscr.clear()
    return quit

def draw_msg_list(echo, lst, msgn):
    stdscr.clear()
    for i in range(0, width):
        if bold[0]:
            color = curses.color_pair(1) + curses.A_BOLD
        else:
            color = curses.color_pair(1)
        stdscr.insstr(0, i, "─", color)
    if width >= 80:
        draw_title(0, 0, "Список сообщений в конференции " + echo)
    else:
        draw_title(0, 0, echo)

def msg_list(echoarea, msgids, msgn):
    lst = []
    lst = get_msg_list_data(echoarea[0])
    draw_msg_list(echoarea[0], lst, msgn)
    echo_length = len(lst)
    if echo_length <= height - 1:
        start = 0
        end = echo_length - 1
    elif msgn + height - 1 < echo_length:
        start = msgn
        end = msgn + height - 1
    else:
        start = echo_length - height + 1
        end = start + height - 1
    quit = False
    cancel = False
    y = msgn - start
    while not quit:
        n = 1
        for i in range(start, end):
            if i == y + start:
                if bold[2]:
                    color = curses.color_pair(3) + curses.A_BOLD
                else:
                    color = curses.color_pair(3)
            else:
                if bold[3]:
                    color = curses.color_pair(4) + curses.A_BOLD
                else:
                    color = curses.color_pair(4)
            draw_cursor(n - 1, color)
            stdscr.addstr(n, 0, lst[i][1], color)
            stdscr.addstr(n, 16, lst[i][2][:width-26], color)
            stdscr.insstr(n, width - 10, lst[i][3], color)
            n += 1
        key = stdscr.getch()
        if key in s_up:
            y = y - 1
            if start > 0 and y + start < start:
                start -= 1
                end -= 1
            if y == -1:
                y = 0
        elif key in s_down:
            y = y + 1
            if y + start + 1 > end and y + start < echo_length:
                start += 1
                end += 1
            if y > height - 2:
                y = height - 2
        elif key in s_ppage:
            if y == 0:
                start = start - height + 1
                if start < 0:
                    start = 0
                end = start + height - 1
            if y > 0:
                y = 0
        elif key in s_npage:
            if y == height - 2:
                start = start + height - 1
                if start > echo_length - height + 1:
                    start = echo_length - height + 1
                end = start + height - 1
            if y < height - 2:
                y = height - 2
        elif key in s_home:
            y = 0
            start = 0
            end = height - 1
        elif key in s_end:
            y = height - 2
            start = echo_length - height + 1
            end = start + height - 1
        elif key in s_enter:
            quit = True
        elif key in r_quit:
            quit = True
            cancel = True
    if cancel:
        return -1
    else:
        return y + start

check_config()
reset_config()
load_config()
if db == 0:
    from api.txt import *
elif db == 1:
    from api.aio import *
elif db == 2:
    from api.ait import *
elif db == 3:
    from api.sqlite import *
check_directories()
load_lasts()
stdscr = curses.initscr()
curses.start_color()
load_colors()
curses.noecho()
curses.curs_set(False)
stdscr.keypad(True)

stdscr.bkgd(" ", curses.color_pair(1))
get_term_size()
if show_splash:
    splash_screen()
draw_message_box("Подождите", False)
get_counts()
stdscr.clear()
echo_selector()
curses.echo()
curses.curs_set(True)
curses.endwin()
