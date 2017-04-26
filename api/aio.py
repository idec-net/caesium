import os, codecs, sys

def get_echo_length(echo):
    if os.path.exists("aio/" + echo + ".aio"):
        echo_length = sum(1 for l in open("aio/" + echo + ".aio", "r", newline="\n"))
    else:
        echo_length = 0
    return echo_length

def save_to_favorites(msgid, msg):
    if os.path.exists("aio/favorites.aio"):
        f = open("aio/favorites.aio", "r").read().split("\n")
        favorites = []
        for line in f:
            favorites.append(line.split(":")[0])
    else:
        favorites = []
    if not msgid in favorites:
        codecs.open("aio/favorites.aio", "a", "utf-8").write(msgid + ":" + chr(15).join(msg) + "\n")
        return True
    else:
        return False

def get_echo_msgids(echo):
    if os.path.exists("aio/" + echo + ".aio"):
        f = codecs.open("aio/" + echo + ".aio", "r", "utf-8").read().split("\n")
        msgids = []
        for line in f:
            if len(line) > 0:
                msgids.append(line.split(":")[0])
    else:
        msgids = []
    return msgids

def get_carbonarea():
    try:
        f = open("aio/carbonarea.aio", "r").read().split("\n")
        carbonarea = []
        for line in f:
            carbonarea.append(line.split(":")[0])
        return carbonarea
    except:
        return []

def add_to_carbonarea(msgid, msgbody):
    codecs.open("aio/carbonarea.aio", "a", "utf-8").write(msgid + ":" + chr(15).join(msgbody) + "\n")

def save_message(raw, counts, remote_counts, node):
    co = counts
    for msg in raw:
        msgid = msg[0]
        msgbody = msg[1]
        if msgbody[1] in co[node]:
            co[node][msgbody[1]] += 1
        else:
            co[node][msgbody[1]] = remote_counts[msgbody[1]]
        codecs.open("aio/" + msgbody[1] + ".aio", "a", "utf-8").write(msgid + ":" + chr(15).join(msgbody) + "\n")
    return co

def get_favorites_list():
    return codecs.open("aio/favorites.aio", "r", "utf-8").read().split("\n")

def remove_from_favorites(msgid):
    favorites_list = get_favorites_list()
    favorites = []
    for item in favorites_list:
        if not item.startswith(msgid):
            favorites.append(item)
    codecs.open("aio/favorites.aio", "w", "utf-8").write("\n".join(favorites))

def remove_echoarea(echoarea):
    try:
        os.remove("ait/%s.aio" % echoarea)
    except:
        None

def get_msg_list_data(echoarea):
    f = codecs.open("aio/%s.aio" % echoarea, "r", "utf-8").read().split("\n")
    lst = []
    for msg in f:
        if len(msg) > 1:
            rawmsg = msg.split(chr(15))
            lst.append([rawmsg[0].split(":")[0], rawmsg[3], rawmsg[6], time.strftime("%Y.%m.%d", time.gmtime(int(rawmsg[2])))])
    return lst

def read_msg(msgid, echoarea):
    size = "0b"
    if os.path.exists("aio/" + echoarea + ".aio") and msgid != "":
        index = codecs.open("aio/" + echoarea + ".aio", "r", "utf-8").read().split("\n")
        msg = None
        for item in index:
            if item.startswith(msgid):
                msg = ":".join(item.split(":")[1:]).split(chr(15))
        if msg:
            size = len ("\n".join(msg).encode("utf-8"))
        else:
            size = 0
        if size < 1024:
            size = str(size) + " B"
        else:
            size = str(format(size / 1024, ".2f")) + " KB"
    else:
        msg = ["", "", "", "", "", "", "", "", "Сообщение отсутствует в базе"]
    return msg, size
