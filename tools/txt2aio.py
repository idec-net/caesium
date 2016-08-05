#!/usr/bin/env python3

import sys, re

def msg_filter(msgid):
    rr = re.compile(r'^[a-z0-9A-Z]{20}$')
    if rr.match(msgid): return True

echoarea = sys.argv[1]

index = open("echo/" + echoarea, "r").read().split("\n")

for msgid in index:
    try:
        if msg_filter(msgid):
            msg = open("msg/" + msgid, "r").read().split("\n")
            open(echoarea + ".aio", "a").write(msgid + ":" + chr(15).join(msg) + "\n")
            print(msgid + ": OK.")
        else:
            if len(msgid) > 0:
                print(msgid + ": incorrect msgid.")
    except:
        print(msgid + ": message not found.")
