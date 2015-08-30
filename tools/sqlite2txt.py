#!/usr/bin/env python3

import os, sqlite3
from shutil import rmtree

if os.path.exists("echo/"):
    rmtree("echo/")
if os.path.exists("msg/"):
    rmtree("msg/")
os.mkdir("echo/")
os.mkdir("msg/")

conn = sqlite3.connect("../ii.db")
c = conn.cursor()

echoareas = []
for row in c.execute("SELECT echoarea FROM msg GROUP BY echoarea;"):
    echoareas.append(row[0])

for echoarea in echoareas:
    print("Echoarea: " + echoarea)
    echo = open("echo/" + echoarea, "w")
    msgids = []
    for msg in c.execute("SELECT * FROM msg WHERE echoarea = '" + echoarea + "' ORDER BY id;"):
        print ("MSGID: " + msg[1], end=" ")
        echo.write(msg[1] + "\n")
        msgf = open("msg/" + msg[1], "w")
        msgf.write(msg[2] + "\n" + msg[3] + "\n" + str(msg[4]) + "\n" + msg[5] + "\n" + msg[6] + "\n" + msg[7] + "\n" + msg[8] + "\n\n" + msg[9])
        msgf.close()
        print("OK")
    echo.close()

conn.close()
