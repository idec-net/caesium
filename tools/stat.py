#!/usr/bin/env python3

import sys, calendar, datetime

echoareas = []
config = ""
start_date = ""
end_date = ""
title = "Echoareas"

if "-f" in sys.argv and len(sys.argv) == 7:
    config = sys.argv[sys.argv.index("-f") + 1]
else:
    print("Usage: idec-stat -f config_file -s YYYY.MM.DD -e YYYY.MM.DD.\n")
    quit()

if "-s" in sys.argv and len(sys.argv) == 7:
    date = sys.argv[sys.argv.index("-s") + 1].split(".")
    start_date = calendar.timegm(datetime.date(int(date[0]), int(date[1]), int(date[2])).timetuple())
else:
    print("Usage: idec-stat -f config_file -s YYYY.MM.DD -e YYYY.MM.DD.\n")
    quit()

if "-e" in sys.argv and len(sys.argv) == 7:
    date = sys.argv[sys.argv.index("-e") + 1].split(".")
    end_date = calendar.timegm(datetime.date(int(date[0]), int(date[1]), int(date[2])).timetuple())
else:
    print("Usage: idec-stat -f config_file -s YYYY.MM.DD -e YYYY.MM.DD.\n")
    quit()

def load_config():
    global echoareas, title
    lines = open(config, "r").read().split("\n")
    for line in lines:
        param = line.split(" ")
        if param[0] == "echo":
            echoareas.append(param[1])
        if param[0] == "title":
            title = " ".join(param[1:])

def calculate_msgs(echoarea):
    ret = []
    msgids = open("echo/" + echoarea, "r").read().split("\n")
    for msgid in msgids:
        if len(msgid) == 20:
            msg = open("msg/" + msgid, "r").read().split("\n")
            if int(msg[2]) >= start_date and int(msg[2]) < end_date:
                ret.append(msgid)
    return ret

def calculate_echoareas():
    ret = []
    for echoarea in echoareas:
        ret.append([echoarea, len(calculate_msgs(echoarea))])
    ret = sorted(ret, key=lambda ret: ret[1], reverse = True)
    return ret

load_config()
stat = calculate_echoareas()
value_of_division = round(stat[0][1] / 54 + 0.49)
total = 0
print("%-25s ▒ ≈ %s messages" % (title, value_of_division))
print("───────────────────────────────────────────────────────────────────────────────")
for item in stat:
    dots = ""
    graph = ""
    empty = ""
    for i in range(1, 25 - len(item[0]) - len(str(item[1]))):
        dots = dots + "."
    for i in range(1, round(item[1] / value_of_division + 0.49) + 1):
        graph = graph + "█"
    for i in range(1, 55 - len(graph)):
        empty = empty + "▒"
    print("%s%s%s %s%s" % (item[0], dots, item[1], graph, empty))
    total = total + item[1]
print("───────────────────────────────────────────────────────────────────────────────")

empty = ""
for i in range(1, 20 - len(str(total))):
    empty = empty + " "

print("Total", empty, total, sep="")
