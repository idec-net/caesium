import os, codecs, sys

def get_echo_length(echo):
    if os.path.exists("ait/" + echo + ".iat"):
        echo_length = sum(1 for l in open("ait/" + echo + ".iat", "r", newline="\n"))
    else:
        echo_length = 0
    return echo_length

def save_to_favorites(msgid, msg):
    if os.path.exists("ait/favorites.mat"):
        f = open("ait/favorites.iam", "r").read().split("\n")
        favorites = []
        for line in f:
            favorites.append(line.split(":")[0])
    else:
        favorites = []
    if not msgid in favorites:
        codecs.open("ait/favorites.iat", "a", "utf-8").write(msgid + "\n")
        codecs.open("ait/favorites.mat", "a", "utf-8").write(msgid + ":" + chr(15).join(msg) + "\n")
        return True
    else:
        return False

def get_echo_msgids(echo):
    if os.path.exists("ait/" + echo + ".iat"):
        f = codecs.open("ait/" + echo + ".iat", "r", "utf-8").read().split("\n")
        msgids = []
        for line in f:
            if len(line) > 0:
                msgids.append(line)
    else:
        msgids = []
    return msgids

def get_carbonarea():
    try:
        f = open("ait/carbonarea.iat", "r").read().split("\n")
        carbonarea = []
        for line in f:
            if len(line) > 0:
                carbonarea.append(line)
        return carbonarea
    except:
        return []

def add_to_carbonarea(msgid, msgbody):
    codecs.open("ait/carbonarea.iat", "a", "utf-8").write(msgid + "\n")
    codecs.open("ait/carbonarea.mat", "a", "utf-8").write(msgid + ":" + chr(15).join(msg) + "\n")

def save_message(msgid, msgbody):
    codecs.open("ait/" + msgbody[1] + ".iat", "w", "utf-8").write(msgid + "\n")
    codecs.open("ait/" + msgbody[1] + ".mat", "w", "utf-8").write(msgid + ":" + chr(15).join(msgbody) + "\n")

def get_favorites_list():
    return codecs.open("ait/favorites.mat", "r", "utf-8").read().split("\n")

def remove_from_favorites(msgid):
    favorites_list = get_favorites_list()
    favorites = []
    favorites_index = []
    for item in favorites_list:
        if not item.startswith(msgid):
            favorites.append(item)
            favorites_index.append(item.split(":")[0])
    codecs.open("ait/favorites.iat", "w", "utf-8").write("\n".join(favorites_index))
    codecs.open("ait/favorites.mat", "w", "utf-8").write("\n".join(favorites))

def read_msg(msgid, echoarea):
    size = "0b"
    if os.path.exists("ait/" + echoarea + ".mat") and msgid != "":
        index = codecs.open("ait/" + echoarea + ".mat", "r", "utf-8").read().split("\n")
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
