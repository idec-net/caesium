#!/usr/bin/env python3

import curses, os, urllib.request, urllib.parse, base64, codecs, pickle, time, subprocess
from datetime import datetime

node = ""
auth = ""
echoes = []
archives = []
editor = ""
lasts = []

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
    global node, auth, echoes, editor
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
        elif param[0] == "archive":
            if len(param) > 2:
                archives.append([param[1], " ".join(param[2:])])
            else:
                archives.append([param[1], ""])
        elif param[0] == "editor":
            if len(param) > 2:
                editor = " ".join(param[1:])
            else:
                editor = param[1]

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
                codecs.open("msg/" + msgid, "w", "utf-8").write(base64.b64decode(m[1].encode("ascii")).decode("utf8"))
                codecs.open("echo/" + echo[0], "a", "utf-8").write(msgid + "\n")

def fetch_mail():
    global lasts
    stdscr.clear()
    stdscr.attron(curses.color_pair(1))
    stdscr.attron(curses.A_BOLD)
    stdscr.border()
    draw_title(0, 1, "Получение почты")
    stdscr.refresh()
    log = curses.newwin(height - 2, width - 2, 1, 1)
    log.scrollok(True)
    line = -1
    echoareas = echoes[1:]
    for echo in echoareas:
        find = False
        for i in lasts:
            if echo[0] in i:
                find = True
        if not find:
            lasts.append([echo[0], 0])
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
            local_msg_list = get_local_msg_list(echo)
            msg_list = [x for x in remote_msg_list if x not in local_msg_list and x != ""]
            list_len = len (msg_list) - 1
            n = 0
            for get_list in separate(msg_list):
                debundle(echo, get_bundle("/".join(get_list)))
                n = n + len(get_list)
                current_time()
                stdscr.refresh()
                log.addstr(line, 1, "Загрузка " + echo[0] + ": " + str(n - 1) + "/" + str(list_len), curses.color_pair(4))
                log.refresh()
    if remote and line >= height - 4:
        for i in range(abs(height - 6 - line)):
            log.scroll()
            line = line - 1
    if not remote:
        line = -1
    if remote:
        log.addstr(line + 2, 1, "Загрузка завершена.", curses.color_pair(4))
    else:
        log.addstr(line + 2, 1, "Ошибка: не удаётся связаться с нодой.", curses.color_pair(4))
    log.addstr(line + 3, 1, "Нажмите любую клавишу.", curses.color_pair(2) + curses.A_BOLD)
    log.getch()
    stdscr.clear()

def outcount():
    if not os.path.exists("out/.outcount"):
        codecs.open("out/.outcount", "w", "utf-8").write("0")
    i = str(int(codecs.open("out/.outcount", "r", "utf-8").read()) + 1)
    codecs.open("out/.outcount", "w", "utf-8").write(i)
    return "out/%s.out" % i.zfill(5)

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
    lst = [x for x in os.listdir("out") if x.endswith(".out")]
    for msg in lst:
        text = codecs.open("out/%s" % msg, "r", "utf-8").read()
        coded_text = base64.b64encode(text.encode("utf-8"))
        codecs.open("out/%s.toss" % msg, "w", "utf-8").write(coded_text.decode("utf-8"))
        os.rename("out/%s" % msg, "out/%s%s" % (msg, "msg"))

def send_mail():
    stdscr.clear()
    stdscr.attron(curses.color_pair(1))
    stdscr.attron(curses.A_BOLD)
    stdscr.border()
    draw_title(0, 1, "Отправка почты")
    stdscr.refresh()
    lst = [x for x in sorted(os.listdir("out")) if x.endswith(".toss")]
    max = len(lst)
    n = 1
    try:
        for msg in lst:
            stdscr.addstr(1, 1, "Отправка сообщения: " + str(n) + "/" + str(max), curses.color_pair(4))
            text = codecs.open("out/%s" % msg, "r", "utf-8").read()
            data = urllib.parse.urlencode({"tmsg": text,"pauth": auth}).encode("utf-8")
            request = urllib.request.Request(node + "u/point")
            result = urllib.request.urlopen(request, data).read().decode("utf-8")
            if result.startswith("msg ok"):
                os.remove("out/%s" % msg)
                n = n + 1
            elif result == "msg big!":
                print ("ERROR: very big message (limit 64K)!")
            elif result == "auth error!":
                print ("ERROR: unknown auth!")
            else:
                print ("ERROR: unknown error!")
        stdscr.addstr(3, 1, "Отправка завершена.", curses.color_pair(4))
    except:
        stdscr.addstr(2, 1, "Ошибка: не удаётся связаться с нодой.", curses.color_pair(4))
    stdscr.addstr(3, 1, "Нажмите любую клавишу.", curses.color_pair(2) + curses.A_BOLD)
    stdscr.getch()
    stdscr.clear()

#
# Пользовательский интерфейс
#

echo_cursor = 0
archive_cursor = 0

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

def current_time():
    draw_title (height - 1, width - 10, datetime.now().strftime("%H:%M"))

def get_echo_length(echo):
    if os.path.exists("echo/" + echo):
        f = open ("echo/" + echo, "r")
        echo_length = len(f.read().split("\n")) - 2
        f.close()
    else:
        echo_length = 0
    return echo_length

def draw_echo_selector(start, cursor, archive):
    stdscr.attron(curses.color_pair(1))
    stdscr.attron(curses.A_BOLD)
    stdscr.border()
    if archive:
        echoareas = archives
        draw_title(0, 1, "Архив эхоконференций")
    else:
        echoareas = echoes
        draw_title(0, 1, "Список эхоконференций")
    y = 0
    for echo in echoareas:
        if y - start < height - 2:
            if y == cursor:
                if y >= start:
                    draw_cursor(y - start, curses.color_pair(3))
                stdscr.attron (curses.color_pair(3) + curses.A_BOLD)
            else:
                if y >= start:
                    draw_cursor(y - start, curses.color_pair(4))
                stdscr.attron (curses.color_pair(4))
                stdscr.attroff (curses.A_BOLD)
            if y + 1 >= start + 1:
                echo_length = get_echo_length(echo[0])
                last = 0
                for i in lasts:
                    if echo[0] == i[0]:
                        last = i[1]
                if last < echo_length:
                    stdscr.addstr(y + 1 - start, 1, "+")
                stdscr.addstr(y + 1 - start, 3, echo[0])
                echocount = len(open("echo/" + echo[0], "r").read().split("\n")) - 1
                last = -1
                for n in lasts:
                    if n[0] == echo[0]:
                        last = echocount - n[1]
                if last == -1:
                    last = echocount + 1
                stdscr.addstr(y + 1 - start, 25, str(echocount))
                stdscr.addstr(y + 1 - start, 31, str(last - 1))
                if width - 38 >= len(echo[1]):
                    stdscr.addstr(y + 1 - start, 37, echo[1])
                else:
                    cut_index = width - 38 - len(echo[1])
                    stdscr.addstr(y + 1 - start, 37, echo[1][:cut_index])
        y = y + 1
    current_time()
    stdscr.refresh()

def echo_selector():
    global echo_cursor, archive_cursor
    archive = False
    echoareas = echoes
    key = 0
    start = 0
    go = True
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
        elif key == ord("s") or key == ord("S"):
            make_toss()
            send_mail()
        elif key == 9:
            if archive:
                archive = False
                archive_cursor = cursor
                cursor = echo_cursor
                echoareas = echoes
                stdscr.clear()
            else:
                archive = True
                echo_cursor = cursor
                cursor = archive_cursor
                echoareas = archives
                stdscr.clear()
        elif key == 10 or key == curses.KEY_RIGHT:
            last = 0
            for i in lasts:
                if i[0] == echoareas[cursor][0]:
                    last = i[1]
            echo_length = get_echo_length(echoareas[cursor][0])
            if last > 0 and last < echo_length:
                last = last + 1
            if cursor == 0:
                go = not echo_reader(echoareas[cursor][0], last, archive, True)
            else:
                go = not echo_reader(echoareas[cursor][0], last, archive, False)
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
        if line.startswith(">>>>>>"):
            code = chr(16)
        elif line.startswith(">>>>>"):
            code = chr(15)
        elif line.startswith(">>>>"):
            code = chr(16)
        elif line.startswith(">>>"):
            code = chr(15)
        elif line.startswith(">>"):
            code = chr(16)
        elif line.startswith(">"):
            code = chr (15)
        else:
            code = " "
        body = body + code
        for word in line.split(" "):
            if n + len(word) + 1 <= width - 2:
                n = n + len(word)
                body = body + word
                if not word[-1:] == "\n":
                    n = n + 1
                    body = body + " "
            else:
                body = body[:-1]
                if len(word) < width - 2:
                    body = body + "\n" + code + word
                    n = len (word)
                else:
                    chunks, chunksize = len(word), width - 2
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
    stdscr.border()
    draw_title(0, 1, echo + " / " + msgid)
    current_time()
    for i in range(0, 3):
        draw_cursor(i, 1)
    stdscr.addstr(1, 1, "От:   ", curses.color_pair(2) + curses.A_BOLD)
    stdscr.addstr(2, 1, "Кому: ", curses.color_pair(2) + curses.A_BOLD)
    stdscr.addstr(3, 1, "Тема: ", curses.color_pair(2) + curses.A_BOLD)
    stdscr.addstr(4, 0, "├", curses.color_pair(1) + curses.A_BOLD)
    stdscr.addstr(4, width - 1, "┤", curses.color_pair(1) + curses.A_BOLD)
    for i in range(1, width - 1):
        stdscr.addstr(4, i, "─", curses.color_pair(1) + curses.A_BOLD)

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
    curses.init_pair(1, 4, 0)
    curses.init_pair(2, 3, 0)
    curses.init_pair(3, 7, 4)
    curses.init_pair(4, 7, 0)
    curses.init_pair(5, 2, 0)
    get_term_size()

def message_box(smsg):
    maxlen = 0
    msg = smsg.split("\n")
    for line in msg:
        if len(line) > maxlen:
            maxlen = len(line)
    msgwin = curses.newwin(len(msg) + 4, maxlen + 2, int(height / 2 - 2) , int(width / 2 - maxlen / 2))
    msgwin.attron(curses.color_pair(1))
    msgwin.attron(curses.A_BOLD)
    msgwin.border()
    i = 1
    for line in msg:
        msgwin.addstr(i, 1, line, curses.color_pair(4))
        i = i + 1
    msgwin.addstr(len(msg) + 2, int((maxlen + 2 - 21) / 2), "Нажмите любую клавишу", curses.color_pair(2) + curses.A_BOLD)
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
    global lasts
    stdscr.clear()
    stdscr.attron(curses.color_pair(1))
    stdscr.attron(curses.A_BOLD)
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
            draw_reader(echo, msgids[msgn])
            msg_string = str(msgn + 1) + " / " + str(len(msgids))
            draw_title (0, width - len(msg_string) - 5, msg_string)
            msgtime = time.strftime("%Y.%m.%d %H:%M UTC", time.gmtime(int(msg[2])))
            stdscr.addstr(1, 7, msg[3] + " (" + msg[4] + ")", curses.color_pair(4))
            stdscr.addstr(1, width - len(msgtime) - 1, msgtime, curses.color_pair(4))
            stdscr.addstr(2, 7, msg[5], curses.color_pair(4))
            stdscr.addstr(3, 7, msg[6][:width - 8], curses.color_pair(4))
            draw_title(4, 1, size)
            for i in range (0, height - 6):
                draw_cursor(i + 4, 1)
                if i < len(msgbody) - 1:
                    if len(msgbody[y+i]) > 0:
                        if msgbody[y + i][0] == chr(15):
                            stdscr.attron(curses.color_pair(2))
                        elif msgbody[y + i][0] == chr(16):
                            stdscr.attron(curses.color_pair(5))
                        else:
                            stdscr.attron(curses.color_pair(4))
                        stdscr.attroff(curses.A_BOLD)
                        stdscr.addstr(i + 5, 1, msgbody[y + i][1:])
        else:
            draw_reader(echo, "")
        stdscr.attron(curses.color_pair(1))
        stdscr.attron(curses.A_BOLD)
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
        elif key == curses.KEY_UP and y > 0:
            if len(msgids) > 0:
                y = y - 1
        elif key == curses.KEY_PPAGE:
            if len(msgids) > 0:
                y = y - height + 6
                if y < 0:
                    y = 0
        elif key == curses.KEY_NPAGE:
            if len(msgids) > 0 and len(msgbody) > height - 6:
                y = y + height - 6
                if y + height - 6 >= len(msgbody):
                    y = len(msgbody) - height + 6
        elif key == curses.KEY_DOWN:
            if len(msgids) > 0:
                if y + height - 6 < len(msgbody):
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
                f.write(echo + "\n")
                f.write(msg[3] + "\n")
                if not msg[6].startswith("Re:"):
                    f.write("Re: " + msg[6] + "\n")
                else:
                    f.write(msg[6] + "\n")
                for line in msg[8:]:
                    if line.strip() != "":
                        f.write("\n>" + line)
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
        elif key == curses.KEY_F10:
            go = False
            quit = True
    flag = False
    for i in range(0, len(lasts)):
        if echo == lasts[i][0]:
            flag = True
            lasts[i][1] = msgn
    if not flag:
        lasts.append([echo, msgn])
    f = open("lasts.lst", "wb")
    pickle.dump(lasts, f)
    f.close()
    stdscr.clear()
    return quit

check_directories()
load_config()
echoes.insert(0, ["favorites", "Избранные сообщения"])
if os.path.exists("lasts.lst"):
    f = open("lasts.lst", "rb")
    lasts = pickle.load(f)
    f.close()
stdscr = curses.initscr()
curses.start_color()
curses.noecho()
curses.curs_set(False)
stdscr.keypad(True)
curses.init_pair(1, 4, 0)
curses.init_pair(2, 3, 0)
curses.init_pair(3, 7, 4)
curses.init_pair(4, 7, 0)
curses.init_pair(5, 2, 0)
get_term_size()
echo_selector()
curses.echo()
curses.curs_set(True)
curses.endwin()
