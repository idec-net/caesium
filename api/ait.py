# coding=utf-8
import codecs
import os
from typing import Optional, List, Callable

from . import MsgMetadata, FindQuery, filterEchoarea, buildFindMatchers, txtApiMatch

storage = "ait/"


def init(directory="ait/"):
    global storage
    storage = directory
    if not storage.endswith("/"):
        storage += "/"
    if not os.path.exists(storage):
        os.mkdir(storage)
    if not os.path.exists(storage + "nodes"):
        os.mkdir(storage + "nodes")


def getEchoLength(echo):
    if os.path.exists(storage + echo + ".iat"):
        echo_length = sum(1 for _ in open(storage + echo + ".iat", "r", newline="\n"))
    else:
        echo_length = 0
    return echo_length


def saveToFavorites(msgid, msg):
    favorites = []
    if os.path.exists(storage + "favorites.mat"):
        with open(storage + "favorites.mat", "r") as f:
            for line in f.read().splitlines():
                favorites.append(line.split(":")[0])
    if msgid not in favorites:
        with codecs.open(storage + "favorites.iat", "a", "utf-8") as f:
            f.write(msgid + "\n")
        with codecs.open(storage + "favorites.mat", "a", "utf-8") as f:
            f.write(msgid + ":" + chr(15).join(msg) + "\n")
        return True
    else:
        return False


def getEchoMsgids(echo):
    if os.path.exists(storage + echo + ".iat"):
        with codecs.open(storage + echo + ".iat", "r", "utf-8") as f:
            return list(filter(None, f.read().splitlines()))
    return []


def getEchoMsgsMetadata(echo):
    # type: (str) -> List[MsgMetadata]
    if not os.path.exists(storage + echo + ".mat"):
        return []

    echo_msgs = []
    with codecs.open(storage + echo + ".mat", "r", "utf-8") as f:
        for str_msg in filter(None, f.read().split("\n")):
            msgid, msg = str_msg.split(":", maxsplit=1)
            msg = msg.split(chr(15))
            echo_msgs.append(MsgMetadata.fromList(msgid, msg))
    return echo_msgs


def getCarbonarea():
    if os.path.exists(storage + "carbonarea.iat"):
        with open(storage + "carbonarea.iat", "r") as f:
            return list(filter(None, f.read().splitlines()))
    return []


def addToCarbonarea(msgid, msgbody):
    with codecs.open(storage + "carbonarea.iat", "a", "utf-8") as f:
        f.write(msgid + "\n")
    with codecs.open(storage + "carbonarea.mat", "a", "utf-8") as f:
        f.write(msgid + ":" + chr(15).join(msgbody) + "\n")


# noinspection PyUnusedLocal
def saveMessage(raw, node, to):
    for msg in raw:
        msgid = msg[0]
        msgbody = msg[1]
        with codecs.open(storage + msgbody[1] + ".iat", "a", "utf-8") as f:
            f.write(msgid + "\n")
        with codecs.open(storage + msgbody[1] + ".mat", "a", "utf-8") as f:
            f.write(msgid + ":" + chr(15).join(msgbody) + "\n")
        if to:
            carbonarea = getCarbonarea()
            for name in to:
                if name in msgbody[5] and msgid not in carbonarea:
                    addToCarbonarea(msgid, msgbody)


def getFavoritesList():
    if not os.path.exists(storage + "favorites.iat"):
        return []
    with codecs.open(storage + "favorites.iat", "r", "utf-8") as f:
        return f.read().splitlines()


def removeFromFavorites(msgid):
    with codecs.open(storage + "favorites.mat", "r", "utf-8") as f:
        favorites_list = f.read().split("\n")
    favorites = []
    favoritesIdx = []
    for item in favorites_list:
        if not item.startswith(msgid + ":"):
            favorites.append(item)
            favoritesIdx.append(item.split(":")[0])
    with codecs.open(storage + "favorites.iat", "w", "utf-8") as f:
        f.write("\n".join(favoritesIdx))
    with codecs.open(storage + "favorites.mat", "w", "utf-8") as f:
        f.write("\n".join(favorites))


def removeEchoarea(echoarea):
    if os.path.exists(storage + "%s.iat" % echoarea):
        os.remove(storage + "%s.iat" % echoarea)
    if os.path.exists(storage + "%s.mat" % echoarea):
        os.remove(storage + "%s.mat" % echoarea)


def readMsg(msgid, echoarea):
    if not os.path.exists(storage + echoarea + ".mat") or not msgid:
        return ["", "", "", "", "", "", "", "", "Сообщение отсутствует в базе"], 0

    with codecs.open(storage + echoarea + ".mat", "r", "utf-8") as f:
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
        if echo in ("carbonarea.iat", "favorites.iat") or not echo.endswith(".iat"):
            continue  # not echo

        with codecs.open(storage + echo, "r", "utf-8") as f:
            exists = list(filter(lambda it: it.strip() == msgid,
                                 f.read().split("\n")))
            if exists:
                return readMsg(msgid, echo[0:-len(".iat")])
    return ["", "", "", "", "", "", "", "", "Сообщение отсутствует в базе"], 0


def findSubjMsgids(echoarea, subj):
    # type: (str, str) -> List[MsgMetadata]
    if subj.startswith("Re: "):
        subj = subj[4:]
    elif subj.startswith("Re:"):
        subj = subj[3:]
    subjRe = "Re:" + subj
    subjReSpace = "Re: " + subj

    if echoarea:
        echoareas = [echoarea + ".mat"]
    else:
        echoareas = sorted(list(filter(
            lambda e: e.endswith(".mat") and e not in ("favorites.mat",
                                                       "carbonarea.mat"),
            os.listdir(storage))))

    threadMsgs = []
    for echo in echoareas:
        with codecs.open(storage + echo, "r", "utf-8") as f:
            for str_msg in filter(None, f.read().split("\n")):
                msgid, msg = str_msg.split(":", maxsplit=1)
                msg = msg.split(chr(15))
                if msg[6] in (subj, subjRe, subjReSpace):
                    threadMsgs.append(MsgMetadata.fromList(msgid, msg))
    return threadMsgs


FIND_CANCEL = 1
FIND_OK = 0


def findQueryMsgids(fq: FindQuery,
                    progressHandler: Callable = None) -> List[MsgMetadata]:
    echoareas = sorted(list(filter(
        lambda e: e.endswith(".mat") and e not in ("favorites.mat",
                                                   "carbonarea.mat"),
        os.listdir(storage))))
    echoareas = filterEchoarea(fq, echoareas, len(".mat"))
    #
    findResult = []
    totalMsgProgress = 0
    echoProgress = 0
    totalEchoareas = len(echoareas)
    match, matchNot = buildFindMatchers(fq)

    for echo in echoareas:
        with codecs.open(storage + echo, "r", "utf-8") as f:
            echoMsgs = list(filter(None, f.read().split("\n")))
        echoProgress += 1
        echoMsgProgress = 0
        echoTotalMsgs = len(echoMsgs)

        for msg in echoMsgs:
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
