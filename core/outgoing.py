import codecs
import os
from datetime import datetime
from typing import List

from api import MsgMetadata
from core import config, parser

storage = ""


def init(cfg, storage_=""):
    global storage
    storage = storage_
    if storage:
        if not storage.endswith("/"):
            storage += "/"
    if not os.path.exists(storage + "out"):
        os.mkdir(storage + "out")

    for nd in map(directory, cfg.nodes):
        if not os.path.exists(nd):
            os.mkdir(nd)


def directory(node):
    return storage + "out/" + node.nodename + "/"


def get_out_msgids(node, drafts=False):
    # type: (config.Node, bool) -> List[str]
    msgids = []
    node_dir = directory(node)
    if os.path.exists(node_dir):
        if drafts:
            msgids = [f for f in sorted(os.listdir(node_dir))
                      if f.endswith(".draft")]
        else:
            msgids = [f for f in sorted(os.listdir(node_dir))
                      if f.endswith(".out") or f.endswith(".outmsg")]
    return msgids


def get_out_msgs_metadata(node, drafts=False):
    # type: (config.Node, bool) -> List[MsgMetadata]
    msgids = get_out_msgids(node, drafts)
    msgs_metadata = []
    node_dir = directory(node)
    for msgid in msgids:
        with codecs.open(node_dir + msgid, "r", "utf-8") as f:
            msg = f.read().strip().replace("\r", "").split("\n")
            if len(msg) < 4:
                msg += [""] * (4 - len(msg))
            msgs_metadata.append(MsgMetadata.from_list(
                msgid, ["", msg[0], datetime.now().timestamp(), "", "", msg[1], msg[2]]))
    return msgs_metadata


def read_out_msg(msgid, node):  # type: (str, config.Node) -> (List[str], int)
    node_dir = directory(node)
    with open(node_dir + msgid, "r") as f:
        temp = f.read().strip().replace("\r", "").split("\n")
    if len(temp) < 4:
        temp += [""] * (4 - len(temp))
    msg = ["",
           temp[0],
           "",
           "",
           "",
           temp[1],
           temp[2]]
    for line in temp[3:]:
        if not (line.startswith("@repto:")):
            msg.append(line)
    size = os.stat(node_dir + msgid).st_size
    return msg, size


def save_out(filepath):
    with codecs.open("temp", "r", "utf-8") as f:
        new = f.read().strip().replace("\r", "").split("\n")
    if len(new) <= 1:
        os.remove("temp")
    else:
        with codecs.open(filepath, "w", "utf-8") as f:
            f.write("\n".join(new))
        os.remove("temp")


def outcount(node):
    outpath = directory(node)
    num = 0
    for x in os.listdir(outpath):
        s_num = x.split(".", maxsplit=1)[0]
        if s_num.isdigit():
            num = max(num, int(s_num))
    return outpath + "/%s" % str(num + 1).zfill(5)


def get_out_length(node, drafts=False):
    node_dir = directory(node)
    if drafts:
        return len([f for f in os.listdir(node_dir)
                    if f.endswith(".draft")])
    else:
        return len([f for f in os.listdir(node_dir)
                    if f.endswith(".out") or f.endswith(".outmsg")])


def new_msg(echo):
    with open("template.txt", "r") as t:
        with open("temp", "w") as f:
            f.write(echo + "\n")
            f.write("All\n")
            f.write("No subject\n\n")
            f.write(t.read())


def quote_msg(msgid, msg, oldquote):
    with open("template.txt", "r") as t:
        with open("temp", "w") as f:
            subj = msg[6]
            if not msg[6].startswith("Re:"):
                subj = "Re: " + subj
            f.write(msg[1] + "\n")
            f.write(msg[3] + "\n")
            f.write(subj + "\n\n")
            f.write("@repto:" + msgid + "\n")
            #
            if oldquote:
                author = ""
            elif " " not in msg[3]:
                author = msg[3]
            else:
                author = "".join(map(lambda word: word[0], msg[3].split(" ")))
            for line in msg[8:]:
                if line.startswith("+++") or not line.strip():
                    continue  # skip sign and empty lines
                qq = parser.quote_template.match(line)
                if qq:
                    quoter = ">"
                    if len(line) > qq.span()[1] and line[qq.span()[1]] != " ":
                        quoter += " "
                    f.write("\n" + line[:qq.span()[1]]
                            + quoter
                            + line[qq.span()[1]:])
                else:
                    f.write("\n" + author + "> " + line)
            f.write(t.read())
