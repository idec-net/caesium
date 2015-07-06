import os, urllib.request

node = ""
auth = ""
echoes = []

def load_config():
    global node, auth, echoes
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

def get_local_msg_list(echo):
    if os.path.exists("echo/" + echo):
        f = open("echo/" + echo, "r")
        msglist = f.read().split("\n")
    else:
        f = open("echo/" + echo, "w")
        msglist = []
    f.close()
    return msglist

def get_remote_msg_list(echo):
    return urllib.request.urlopen(node + "u/e/" + echo).read().decode("utf-8").split("\n")[1:-1]
