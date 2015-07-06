import urllib.request, base64, codecs, os

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

def get_msg_list(echo):
    msg_list = []
    r = urllib.request.Request(ii.node + "u/e/" + echo)
    with urllib.request.urlopen(r) as f:
        lines = f.read().decode("utf-8").split("\n")
        for line in lines:
            if line != echo:
                msg_list.append(line)
    return msg_list

def get_local_msg_list(echo):
    if not os.path.exists("../base/echo/" + echo):
        return []
    else:
        local_msg_list = codecs.open("../base/echo/" + echo, "r", "utf-8").read().split("\n")
        return local_msg_list

def get_bundle(msgids):
    print ("Fetch %su/m/%s\n" % (ii.node, msgids))
    bundle = []
    r = urllib.request.Request(ii.node + "u/m/" + msgids)
    with urllib.request.urlopen(r) as f:
        bundle = f.read().decode("utf-8").split("\n")
    return bundle

def debundle(echo, bundle):
    for msg in bundle:
        if msg:
            m = msg.split(":")
            msgid = m[0]
            if len(msgid) == 20 and m[1]:
                codecs.open("../base/msg/" + msgid, "w", "utf-8").write(base64.b64decode(m[1]).decode("utf-8"))
                codecs.open("../base/echo/" + echo, "a", "utf-8").write(msgid + "\n")
                codecs.open("../.newmsg", "a", "utf-8").write(msgid + "\n")

def fetch_mail():
    for echo in ii.echoes:
        remote_msg_list = get_msg_list(echo)
        if len(remote_msg_list) > 1:
            local_msg_list = get_local_msg_list(echo)
            msg_list = [x for x in remote_msg_list if x not in local_msg_list]
            for get_list in ii.separate(msg_list):
                debundle(echo, get_bundle("/".join(get_list)))
        else:
            codecs.open("../base/echo/" + echo, "a", "utf-8").close()
