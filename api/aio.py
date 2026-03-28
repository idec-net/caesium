# coding=utf-8
import codecs
import os
from typing import Optional, List, Callable

from . import MsgMetadata, FindQuery, filterEchoarea, buildFindMatchers, txtApiMatch

storage = "aio/"


def init(directory="aio/"):
    global storage
    storage = directory
    if not storage.endswith("/"):
        storage += "/"
    if not os.path.exists(storage):
        os.mkdir(storage)
    if not os.path.exists(storage + "nodes"):
        os.mkdir(storage + "nodes")


def getEchoLength(echo):
    if os.path.exists(storage + echo + ".aio"):
        with open(storage + echo + ".aio", "r", newline="\n") as f:
            return len(f.readlines())
    return 0


def saveToFavorites(msgid, msg):
    favorites = []
    if os.path.exists(storage + "favorites.aio"):
        with open(storage + "favorites.aio", "r") as f:
            favorites = list(map(lambda it: it.split(":")[0],
                                 filter(lambda it: it, f.read().split("\n"))))
    if msgid not in favorites:
        with codecs.open(storage + "favorites.aio", "a", "utf-8") as f:
            f.write(msgid + ":" + chr(15).join(msg) + "\n")
        return True
    else:
        return False


def getEchoMsgids(echo):
    if not os.path.exists(storage + echo + ".aio"):
        return []

    with codecs.open(storage + echo + ".aio", "r", "utf-8") as f:
        return list(map(lambda it: it.split(":")[0],
                        filter(None, f.read().split("\n"))))


def getEchoMsgsMetadata(echo):
    # type: (str) -> List[MsgMetadata]
    if not os.path.exists(storage + echo + ".aio"):
        return []

    echo_msgs = []
    with codecs.open(storage + echo + ".aio", "r", "utf-8") as f:
        for str_msg in filter(None, f.read().split("\n")):
            msgid, msg = str_msg.split(":", maxsplit=1)
            msg = msg.split(chr(15))
            echo_msgs.append(MsgMetadata.fromList(msgid, msg))
    return echo_msgs


def getCarbonarea():
    if not os.path.exists(storage + "carbonarea.aio"):
        return []
    with open(storage + "carbonarea.aio", "r") as f:
        return list(filter(lambda it: len(it) == 20,
                           map(lambda it: it.split(":")[0],
                               filter(lambda it: it, f.read().split("\n")))))


def addToCarbonarea(msgid, msgbody):
    with codecs.open(storage + "carbonarea.aio", "a", "utf-8") as f:
        f.write(msgid + ":" + chr(15).join(msgbody) + "\n")


# noinspection PyUnusedLocal
def saveMessage(raw, node, to):
    for msg in raw:
        msgid = msg[0]
        msgbody = msg[1]
        with codecs.open(storage + msgbody[1] + ".aio", "a", "utf-8") as f:
            f.write(msgid + ":" + chr(15).join(msgbody) + "\n")
        if to:
            carbonarea = getCarbonarea()
            for name in to:
                if name in msgbody[5] and msgid not in carbonarea:
                    addToCarbonarea(msgid, msgbody)


def getFavoritesList():
    if not os.path.exists(storage + "favorites.aio"):
        return []
    with codecs.open(storage + "favorites.aio", "r", "utf-8") as f:
        return list(map(lambda msg: msg.split(":")[0],
                        filter(None, f.read().split("\n"))))


def removeFromFavorites(msgid):
    with codecs.open(storage + "favorites.aio", "r", "utf-8") as f:
        favorites = list(filter(lambda it: it and not it.startswith(msgid + ":"),
                                f.read().split("\n")))
    with codecs.open(storage + "favorites.aio", "w", "utf-8") as f:
        f.write("\n".join(favorites))


def removeEchoarea(echoarea):
    if os.path.exists(storage + "%s.aio" % echoarea):
        os.remove(storage + "%s.aio" % echoarea)


def readMsg(msgid, echoarea):
    if not os.path.exists(storage + echoarea + ".aio") or not msgid:
        return ["", "", "", "", "", "", "", "", "Сообщение отсутствует в базе"], 0

    with codecs.open(storage + echoarea + ".aio", "r", "utf-8") as f:
        index = list(filter(lambda i: i.startswith(msgid),
                            f.read().split("\n")))
    msg = None
    size = 0
    if index:
        msg = ":".join(index[-1].split(":")[1:]).split(chr(15))
    if msg:
        size = len("\n".join(msg).encode("utf-8"))
    return msg, size


def findMsg(msgid):
    for echo in os.listdir(storage):
        if echo in ("carbonarea.aio", "favorites.aio") or not echo.endswith(".aio"):
            continue  # not echo

        with codecs.open(storage + echo, "r", "utf-8") as f:
            index = list(filter(lambda it: it.startswith(msgid + ":"),
                                f.read().split("\n")))
        if index:
            msg = ":".join(index[-1].split(":")[1:]).split(chr(15))
            size = len("\n".join(msg).encode("utf-8"))
            return msg, size
    return ["", "", "", "", "", "", "", "", "Сообщение отсутствует в базе"], 0


def findSubjMsgids(echoarea, subj):
    # type: (Optional[str], str) -> List[str]
    if subj.startswith("Re: "):
        subj = subj[4:]
    elif subj.startswith("Re:"):
        subj = subj[3:]
    subjRe = "Re:" + subj
    subjReSpace = "Re: " + subj

    if echoarea:
        echoareas = [echoarea + ".aio"]
    else:
        echoareas = sorted(list(filter(
            lambda e: e.endswith(".aio") and e not in ("favorites.aio",
                                                       "carbonarea.aio"),
            os.listdir(storage))))

    threadMsgs = []
    for echo in echoareas:
        with codecs.open(storage + echo, "r", "utf-8") as f:
            for strMsg in filter(None, f.read().split("\n")):
                msgid, msg = strMsg.split(":", maxsplit=1)
                msg = msg.split(chr(15))
                if msg[6] in (subj, subjRe, subjReSpace):
                    threadMsgs.append(MsgMetadata.fromList(msgid, msg))
    return threadMsgs


FIND_CANCEL = 1
FIND_OK = 0


def findQueryMsgids(fq: FindQuery,
                    progressHandler: Callable = None) -> List[MsgMetadata]:
    echoareas = sorted(list(filter(
        lambda e: e.endswith(".aio") and e not in ("favorites.aio",
                                                   "carbonarea.aio"),
        os.listdir(storage))))
    echoareas = filterEchoarea(fq, echoareas, len(".aio"))
    #
    findResult = []
    totalMsgProgress = 0
    echoProgress = 0
    totalEchoareas = len(echoareas)
    match, matchNot = buildFindMatchers(fq)

    for echo in echoareas:
        with codecs.open(storage + echo, "r", "utf-8") as f:
            echo_msgs = list(filter(None, f.read().split("\n")))
        echoProgress += 1
        echoMsgProgress = 0
        echoTotalMsgs = len(echo_msgs)

        for msg in echo_msgs:
            if len(findResult) >= fq.limit:
                return findResult  #
            #
            totalMsgProgress += 1
            echoMsgProgress += 1
            if progressHandler:
                progress = (echoProgress, totalEchoareas,
                            echoMsgProgress, echoTotalMsgs,
                            totalMsgProgress, len(findResult))
                if progressHandler(progress) == FIND_CANCEL:
                    return []
            #
            msg = msg.split(chr(15))
            msgid_, msg[0] = msg[0].split(":")

            if txtApiMatch(fq, match, matchNot, msgid_, msg):
                findResult.append(MsgMetadata.fromList(msgid_, msg))

    return findResult


def getNodeFeatures(node):  # type: (str) -> Optional[List[str]]
    features = storage + "nodes/" + node + ".x-features"
    if not os.path.exists(features):
        return None  #

    with open(features, "r") as f:
        return list(filter(None, map(lambda it: it.strip(),
                                     f.read().splitlines())))


def saveNodeFeatures(node, features):  # type: (str, List[str]) -> None
    xFeatures = storage + "nodes/" + node + ".x-features"
    with open(xFeatures, "w") as f:
        f.write("\n".join(features))


def getNodeEchoCounts(node):  # type: (str) -> Optional[dict[str, int]]
    xCounts = storage + "nodes/" + node + ".x-counts"
    if not os.path.exists(xCounts):
        return None  #

    with open(xCounts, "r") as f:
        echoCounts = list(filter(None, map(lambda it: it.strip().split(":"),
                                           f.read().splitlines())))
        return {echo[0]: int(echo[1]) for echo in echoCounts}


def saveNodeEchoCounts(node, echo_counts):  # type: (str, dict[str, int]) -> None
    ec = ["%s:%s\n" % (echo, str(count))
          for echo, count in echo_counts.items()]
    xCounts = storage + "nodes/" + node + ".x-counts"
    with open(xCounts, "w") as f:
        f.writelines(ec)
