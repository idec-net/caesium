#!/usr/bin/env python3

import urllib.request, base64, codecs, os, sys

def check_directories():
    if not os.path.exists("out"):
        os.makedirs("out")

def load_config():
    node = ""
    auth = False
    nodename = "unknown"
    f = open(config, "r").read().split("\n")
    for line in f:
        param = line.split(" ")
        if param[0] == "node":
            node = param[1]
        elif param[0] == "nodename":
            nodename = param[1:]
        elif param[0] == "auth":
            auth = param[1]
    return node, nodename, auth

def make_toss():
    lst = [x for x in os.listdir("out/" + nodename) if x.endswith(".out")]
    for msg in lst:
        text = codecs.open("out/" + nodename + "/%s" % msg, "r", "utf-8").read()
        coded_text = base64.b64encode(text.encode("utf-8"))
        codecs.open("out/" + nodename + "/%s.toss" % msg, "w", "utf-8").write(coded_text.decode("utf-8"))
        os.rename("out/" + nodename + "/%s" % msg, "out/" + nodename + "/%s%s" % (msg, "msg"))

def send_mail():
    lst = [x for x in sorted(os.listdir("out/" + nodename)) if x.endswith(".toss")]
    max = len(lst)
    n = 1
    try:
        for msg in lst:
            print("\rОтправка сообщения: " + str(n) + "/" + str(max), end="")
            text = codecs.open("out/" + nodename + "/%s" % msg, "r", "utf-8").read()
            data = urllib.parse.urlencode({"tmsg": text,"pauth": auth}).encode("utf-8")
            request = urllib.request.Request(node + "u/point")
            result = urllib.request.urlopen(request, data).read().decode("utf-8")
            if result.startswith("msg ok"):
                os.remove("out/" + nodename + "/%s" % msg)
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

def show_help():
    print("Usage: sender.py [-f filename] [-n node] [-o] [-to name1,name2...] [-h].")
    print()
    print("  -f filename  load config file. Default idec-fetcher.cfg.")
    print("  -n node      node address.")
    print("  -m nodename  nodename for search .out messages.")
    print("  -a authkey   authkey.")
    print("  -h           this message.")
    print()
    print("If -f not exist, script will load config from current directory with name\nsender.cfg.")

args = sys.argv[1:]

conf = "-f" in args
if conf:
    config = args[args.index("-f") + 1]
else:
    config = "sender.cfg"
h = "-h" in args
if "-n" in args:
    node = args[args.index("-n") + 1]
if "-m" in args:
    nodename = args[args.index("-m") + 1]
if "-a" in args:
    auth = args[args.index("-a") + 1]
wait = "-w" in args

if h:
    show_help()
    quit()

if not "-n" in args and not "-a" in args and not "-m" in args and not os.path.exists(config):
    print("Config file not found.")
    quit()

check_directories()
if not "-n" in args or not "-a" in args and not "-m" in args:
    node, nodename, auth = load_config()
print("Работа с " + node)
make_toss()
send_mail()
if wait:
    input("Нажмите Enter для продолжения.")
    print()
