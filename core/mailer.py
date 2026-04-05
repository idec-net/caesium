import base64
import codecs
import itertools
import os
import traceback
from datetime import datetime
from typing import List

import api.ait
from api import MsgMetadata
from core import config, parser, client, FEAT_X_C, FEAT_U_E, utils
from core.config import CFG

API = api.ait
storage = ""
blacklist = []
if os.path.exists("blacklist.txt"):
    with open("blacklist.txt", "r") as bl:
        blacklist = list(filter(None, map(lambda it: it.strip(),
                                          bl.readlines())))


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


def getOutMsgids(node, drafts=False):
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


def getOutMsgsMetadata(node, drafts=False):
    # type: (config.Node, bool) -> List[MsgMetadata]
    msgids = getOutMsgids(node, drafts)
    msgs_metadata = []
    node_dir = directory(node)
    for msgid in msgids:
        with codecs.open(node_dir + msgid, "r", "utf-8") as f:
            msg = f.read().strip().replace("\r", "").split("\n")
            if len(msg) < 4:
                msg += [""] * (4 - len(msg))
            msgs_metadata.append(MsgMetadata.fromList(
                msgid, ["", msg[0], datetime.now().timestamp(), "", "", msg[1], msg[2]]))
    return msgs_metadata


def readOutMsg(msgid, node):  # type: (str, config.Node) -> (List[str], int)
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


def saveOut(filepath):
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


def getOutLength(node, drafts=False):
    node_dir = directory(node)
    if drafts:
        return len([f for f in os.listdir(node_dir)
                    if f.endswith(".draft")])
    else:
        return len([f for f in os.listdir(node_dir)
                    if f.endswith(".out") or f.endswith(".outmsg")])


def newMsg(echo):
    with open("template.txt", "r") as t:
        with open("temp", "w") as f:
            f.write(echo + "\n")
            f.write("All\n")
            f.write("No subject\n\n")
            f.write(t.read())


def quoteMsg(msgid, msg, oldquote):
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
                qq = parser.quoteTemplate.match(line)
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


def makeToss(node):  # type: (config.Node) -> None
    nodeDir = directory(node)
    lst = [x for x in os.listdir(nodeDir)
           if x.endswith(".out")]
    for msg in lst:
        with codecs.open(nodeDir + "%s" % msg, "r", "utf-8") as f:
            text_raw = f.read()
        txtB64 = base64.b64encode(text_raw.encode("utf-8")).decode("utf-8")
        with codecs.open(nodeDir + "%s.toss" % msg, "w", "utf-8") as f:
            f.write(txtB64)
        os.rename(nodeDir + "%s" % msg,
                  nodeDir + "%s%s" % (msg, "msg"))


def sendMail(node):  # type: (config.Node) -> None
    nodeDir = directory(node)
    lst = [x for x in sorted(os.listdir(nodeDir))
           if x.endswith(".toss")]
    total = str(len(lst))
    try:
        for n, msg in enumerate(lst, start=1):
            print("\rОтправка сообщения: " + str(n) + "/" + total, end="")
            msgToss = nodeDir + msg
            with codecs.open(msgToss, "r", "utf-8") as f:
                text = f.read()
            #
            result = client.sendMsg(node.url, node.auth, text)
            #
            if result.startswith("msg ok"):
                os.remove(msgToss)
            elif result == "msg big!":
                print("\nERROR: very big message (limit 64K)!")
            elif result == "auth error!":
                print("\nERROR: unknown auth!")
            else:
                print("\nERROR: unknown error!")
        if len(lst) > 0:
            print()
    except Exception as ex:
        print("\nОшибка: не удаётся связаться с нодой. " + str(ex))


def debundle(bundle, getList=None):
    messages = []
    for msg in filter(None, bundle):
        m = msg.split(":")
        msgid = m[0]
        if len(msgid) == 20 and m[1]:
            msgbody = base64.b64decode(m[1].encode("ascii")).decode("utf8").split("\n")
            if getList and msgid not in getList:
                print(f"\nWARNING:"
                      f" msgid: {msgid} received but not requested: [{', '.join(getList)}]."
                      f" Skipped. Please report to node sysop.")
            else:
                messages.append([msgid, msgbody])
    if messages:
        API.saveMessage(messages, CFG.node(), CFG.node().to)


def fetchMail(node, forceFullIdx=False):  # type: (config.Node, bool) -> None
    print("Работа с " + node.url)
    try:
        if node.auth:
            makeToss(node)
            sendMail(node)
        getMail(node, forceFullIdx)
    except KeyboardInterrupt:
        print("\nПрервано пользователем")
    except Exception as ex:
        print("\nОШИБКА: " + str(ex))
        print(traceback.format_exc())
    input("Нажмите Enter для продолжения.")


def getMail(node, forceFullIdx=False):  # type: (config.Node, bool) -> None
    features = API.getNodeFeatures(node.nodename)
    if features is None:
        print("Запрос x/features...")
        features = client.getFeatures(node.url)
        API.saveNodeFeatures(node.nodename, features)
        print("  x/features: " + ", ".join(features))
    isNodeSmart = FEAT_X_C in features and FEAT_U_E in features
    #
    echoareas = list(map(lambda e: e.name, filter(lambda e: e.sync,
                                                  node.echoareas)))
    oldNec = None
    newNec = None
    offsets = None
    if isNodeSmart:
        oldNec = API.getNodeEchoCounts(node.nodename)
        newNec = client.getEchoCount(node.url, echoareas)
        offsets = utils.offsetsEchoCount(oldNec or {}, newNec)

    fetchMsgList = []
    if isNodeSmart and oldNec and not forceFullIdx:
        print("Получение свежего индекса от ноды...")
        remoteMsgList = []
        grouped = {offset: [ec[0] for ec in ec]
                   for offset, ec in itertools.groupby(offsets.items(),
                                                       lambda ec: ec[1])}
        for offset, echoareas in grouped.items():
            print("  offset %s: %s" % (str(offset), ", ".join(echoareas)))
            remoteMsgList += client.getMsgList(node.url, echoareas, offset)
    else:
        print("Получение полного индекса от ноды...")
        remoteMsgList = client.getMsgList(node.url, echoareas)

    print("Построение разностного индекса...")
    localIndex = None
    for line in remoteMsgList:
        if parser.echoTemplate.match(line):
            localIndex = API.getEchoMsgids(line)
        elif len(line) == 20 and line not in localIndex and line not in blacklist:
            fetchMsgList.append(line)
    if fetchMsgList:
        total = str(len(fetchMsgList))
        count = 0
        for getList in utils.separate(fetchMsgList):
            count += len(getList)
            print("\rПолучение сообщений: " + str(count) + "/" + total, end="")
            debundle(client.getBundle(node.url, "/".join(getList)), getList)
    else:
        print("Новых сообщений не обнаружено.", end="")
    if isNodeSmart:
        API.saveNodeEchoCounts(node.nodename, newNec)
    print()
