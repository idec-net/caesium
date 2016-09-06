import os

def get_echo_length(echo):
    if os.path.exists("echo/" + echo):
        echo_length = len(open ("echo/" + echo, "r").read().split("\n")) - 1
    else:
        echo_length = 0
    return echo_length

def get_echocount(echoarea):
    return len(open("echo/" + echoarea, "r").read().split("\n")) - 1

def save_to_favorites(msgid, msg):
    if os.path.exists("echo/favorites"):
        favorites = open("echo/favorites", "r").read().split("\n")
    else:
        favorites = []
    if not msgid in favorites:
        open("echo/favorites", "a").write(msgid + "\n")
        return True
    else:
        return False

def get_echo_msgids(echo):
    if os.path.exists("echo/" + echo):
        msgids = open("echo/" + echo, "r").read().split("\n")[:-1]
    else:
        msgids = []
    return msgids

def get_carbonarea():
    try:
        return open("echo/carbonarea", "r").read().split("\n")
    except:
        return []

def add_to_carbonarea(msgid, msgbody):
    codecs.open("echo/carbonarea", "a", "utf-8").write(msgid + "\n")

def save_message(msgid, msgbody):
    codecs.open("msg/" + msgid, "w", "utf-8").write(msgbody)

def get_favorites_list():
    return open("echo/favorites", "r").read().split("\n")

def remove_from_favorites(msgid):
    favorites_list = get_favorites_list()
    favorites_list.remove(msgid)
    open("echo/favorites", "w").write("\n".join(favorites_list))

def read_msg(msgid, echoarea):
    size = "0b"
    if os.path.exists("msg/" + msgid) and msgid != "":
        msg = open("msg/" + msgid, "r").read().split("\n")
        size = os.stat("msg/" + msgid).st_size
        if size < 1024:
            size = str(size) + " B"
        else:
            size = str(format(size / 1024, ".2f")) + " KB"
    else:
        msg = ["", "", "", "", "", "", "", "", "Сообщение отсутствует в базе"]
    return msg, size
