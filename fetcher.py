#!/usr/bin/env python3

import os, urllib.request, base64, codecs, sys

config = ""
clone = []
old = False
node = ""
echoareas = []
ue_ext = False
wait = False
to = []
debug = False

def load_config():
    global node, echoareas
    cfg = open(config, "r").read().split("\n")
    for line in cfg:
        param = line.split(" ")
        if param[0] == "node":
            node = param[1]
        elif param[0] == "echo":
            echoareas.append(param[1])

def get_msg_list(echo, ext = False, start = -48):
    msg_list = []
    if not ext or echo in clone or old:
        r = urllib.request.Request(node + "u/e/" + echo)
    else:
        r = urllib.request.Request(node + "u/e/" + echo + "/" + str(start) + ":48")
    with urllib.request.urlopen(r) as f:
        lines = f.read().decode("utf-8").split("\n")
        for line in lines:
            if line != echo and len(line) > 0:
                msg_list.append(line)
    return msg_list

def get_local_msg_list(echo):
    if not os.path.exists("echo/" + echo):
        return []
    else:
        local_msg_list = codecs.open("echo/" + echo, "r", "utf-8").read().split("\n")
        return local_msg_list

def separate(l, step=48):
    for x in range(0, len(l), step):
        yield l[x:x+step]

def get_bundle(msgids):
    bundle = []
    r = urllib.request.Request(node + "u/m/" + msgids)
    with urllib.request.urlopen(r) as f:
        bundle = f.read().decode("utf-8").split("\n")
    return bundle

def debundle(bundle):
    for msg in bundle:
        if msg:
            m = msg.split(":")
            msgid = m[0]
            if len(msgid) == 20 and m[1]:
                msgbody = base64.b64decode(m[1].encode("ascii")).decode("utf8")
                if len(to) > 0:
                    try:
                        carbonarea = open("echo/carbonarea", "r").read().split("\n")
                    except:
                        carbonarea = []
                    if msgbody.split("\n")[5] in to and not msgid in carbonarea:
                        codecs.open("echo/carbonarea", "a", "utf-8").write(msgid + "\n")
                codecs.open("msg/" + msgid, "w", "utf-8").write(msgbody)
                codecs.open("echo/" + msgbody.split("\n")[1], "a", "utf-8").write(msgid + "\n")

if "-f" in sys.argv:
    config = sys.argv[sys.argv.index("-f") + 1]
if "-o" in sys.argv:
    old = True
if "-c" in sys.argv:
    clone = sys.argv[sys.argv.index("-c") + 1].split(",")
if "-n" in sys.argv:
    node = sys.argv[sys.argv.index("-n") + 1]
if "-e" in sys.argv:
    echoareas = sys.argv[sys.argv.index("-e") + 1].split(",")
if "-t" in sys.argv:
    to = sys.argv[sys.argv.index("-t") + 1].split(",")
if "-w" in sys.argv:
    wait = True
if "-d" in sys.argv:
    debug = True

if len(sys.argv) == 1:
    print("Использование: fetcher.py -f config_file [-c cloned_echoarea1,cloned_echoarea2,...] [-o] или")
    print("               fetcher.py -n node_address -e echoarea.1,echoarea.2 [-c ...] [-o]\n")
    print("  -f указывает путь к конфигурационному файлу;")
    print("  -n указывает адрес подключения к ноде;")
    print("  -e указывает эхоконференции для фетчинга (разделитель запятая);")
    print("  -c указывает эхконференции для клонирования (разделитель запятая);")
    print("  -o опция включает клонирование все эхоконференции из конфига;")
    print("  -t указывает имя пользователя, по которому определяются сообщения для копирования в карбонку;")
    print("  -w ожидать реакции пользователя после окончания фетчинга;")
    print("  -d режим расширенного отображения действий программы.")
    quit()

if "-f" in sys.argv:
    try:
        load_config()
    except:
        print("Не удаётся найти файл конфигурации")

for echo in clone:
    try:
        os.remove("echo/" + echo)
    except:
        None

try:
    r = urllib.request.Request(node + "x/features")
    with urllib.request.urlopen(r) as f:
        if "u/e" in f.read().decode("utf-8").split("\n"):
            ue_ext = True
            print("Расширенная схема u/e поддерживается.")
        else:
            print("Расширенная схема u/e не поддерживается.")
except:
    print("Не поддерживается схема x/features.")

remote = False
remote_msg_list = []
print("Поиск новых сообщений...")
for echo in echoareas:
    if old:
        try:
            os.remove("echo/" + echo)
        except:
            None
    local_msg_list = get_local_msg_list(echo)
    try:
        if not os.path.exists("echo/" + echo) and ue_ext:
            remote_msg_list = remote_msg_list + get_msg_list(echo, True)
            remote = True
        elif ue_ext:
            loop = True
            start = -48
            while loop:
                if debug:
                    print("{0:26}{1:54}".format("Поиск в " + echo, " Смещение индекса: " + str(start)), end="\r")
                tmp = []
                remote = get_msg_list(echo, True, start)
                remote.reverse()
                if len(remote) == 0:
                    print("\nEmpty echoarea.")
                    loop = False
                for msgid in remote:
                    if not msgid in local_msg_list:
                        tmp.append(msgid)
                    else:
                        loop = False
                        break
                tmp.reverse()
                remote_msg_list = remote_msg_list + tmp
                start = start - 48
            if debug:
                print()
            remote = True
        else:
            remote_msg_list = remote_msg_list + get_msg_list(echo)
            remote = True
    except:
        print("Не удаётся связаться с узлом: " + node)
        remote = False
if len(remote_msg_list) == 0:
    print("Новых сообщений не найдено.")
if remote and len(remote_msg_list) > 0:
    msg_list = [x for x in remote_msg_list if x not in local_msg_list and x != ""]
    msg_list_len = str(len(msg_list))
    if len(msg_list) > 0:
        count = 0
        for get_list in separate(msg_list):
            count = count + len(get_list)
            print("Получение: " + str(count) + "/"  + msg_list_len, end="\r")
            debundle(get_bundle("/".join(get_list)))
    print()

if wait:
    input("Нажмите Enter для продолжения.")
    print()
