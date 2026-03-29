# coding=utf-8
import codecs
import os
from typing import Optional, List, Callable

from . import MsgMetadata, FindQuery, filterEchoarea, buildFindMatchers, txtApiMatch

storage = "txt"


def init(directory=""):
    global storage
    storage = directory
    if storage:
        if not storage.endswith("/"):
            storage += "/"
        if not os.path.exists(storage):
            os.mkdir(storage)
    if not os.path.exists(storage + "echo"):
        os.mkdir(storage + "echo")
    if not os.path.exists(storage + "msg"):
        os.mkdir(storage + "msg")
    if not os.path.exists(storage + "echo/favorites"):
        open(storage + "echo/favorites", "w")
    if not os.path.exists("echo/carbonarea"):
        open(storage + "echo/carbonarea", "w")
    if not os.path.exists(storage + "nodes"):
        os.mkdir(storage + "nodes")


def getEchoLength(echo):
    if os.path.exists(storage + "echo/" + echo):
        echo_length = len(open(storage + "echo/" + echo, "r").read().split("\n")) - 1
    else:
        echo_length = 0
    return echo_length


# noinspection PyUnusedLocal
def saveToFavorites(msgid, msg):
    favorites = []
    if os.path.exists(storage + "echo/favorites"):
        with open(storage + "echo/favorites", "r") as f:
            favorites = f.read().splitlines()

    if msgid not in favorites:
        with open(storage + "echo/favorites", "a") as f:
            f.write(msgid + "\n")
        return True
    else:
        return False


def getEchoMsgids(echo):
    if not os.path.exists(storage + "echo/" + echo):
        return []
    with open(storage + "echo/" + echo, "r") as f:
        return f.read().splitlines()


def getEchoMsgsMetadata(echo):
    # type: (str) -> List[MsgMetadata]
    if not os.path.exists(storage + "echo/" + echo):
        return []
    with open(storage + "echo/" + echo, "r") as f:
        msgids = f.read().splitlines()
    echoMsgs = []
    for msgid in msgids:
        header = _readHeader(msgid)
        echoMsgs.append(MsgMetadata.fromList(msgid, header))
    return echoMsgs


def _readHeader(msgid):
    header = []
    with codecs.open(storage + "msg/" + msgid, "r", "utf-8") as f:
        lastLine = ""
        while len(header) < 6:
            buf = f.read(200)
            if not buf:
                break  #
            lines = buf.split("\n")
            lines[0] = lastLine + lines[0]
            if len(lines) > 1:
                header.extend(lines[0:-1])
            lastLine = lines[-1]
    return header


def getCarbonarea():
    if not os.path.exists(storage + "echo/carbonarea"):
        return []
    with open(storage + "echo/carbonarea", "r") as f:
        return list(filter(lambda item: len(item) == 20,
                           f.read().splitlines()))


# noinspection PyUnusedLocal
def addToCarbonarea(msgid, msgbody):
    with codecs.open(storage + "echo/carbonarea", "a", "utf-8") as f:
        f.write(msgid + "\n")


# noinspection PyUnusedLocal
def saveMessage(raw, node, to):
    carbonarea = getCarbonarea()
    for msg in raw:
        msgid = msg[0]
        msgbody = msg[1]
        with codecs.open(storage + "echo/" + msgbody[1], "a", "utf-8") as f:
            f.write(msgid + "\n")
        with codecs.open(storage + "msg/" + msgid, "w", "utf-8") as f:
            f.write("\n".join(msgbody))
        if to:
            for name in to:
                if name in msgbody[5] and msgid not in carbonarea:
                    addToCarbonarea(msgid, msgbody)


def getFavoritesList():
    if not os.path.exists(storage + "echo/favorites"):
        return []

    with open(storage + "echo/favorites", "r") as f:
        return list(filter(lambda it: len(it) == 20, f.read().splitlines()))


def removeFromFavorites(msgid):
    favoritesList = getFavoritesList()
    favoritesList.remove(msgid)
    with open(storage + "echo/favorites", "w") as f:
        f.write("\n".join(favoritesList))


def removeEchoarea(echoarea):
    msgids = []
    fEcho = storage + "echo/%s" % echoarea
    if os.path.exists(fEcho):
        with open(fEcho, "r") as f:
            msgids = f.read().splitlines()
    #
    for msgid in msgids:
        msgid = storage + "msg/%s" % msgid
        if os.path.exists(msgid):
            os.remove(msgid)
    #
    if os.path.exists(fEcho):
        os.remove(fEcho)


# noinspection PyUnusedLocal
def readMsg(msgid, echoarea):
    if not os.path.exists(storage + "msg/" + msgid) or not msgid:
        return ["", "", "", "", "", "", "", "", "Сообщение отсутствует в базе"], 0

    with open(storage + "msg/" + msgid, "r") as f:
        msg = f.read().split("\n")
    size = os.stat(storage + "msg/" + msgid).st_size
    return msg, size


def findMsg(msgid):
    for echo in os.listdir(storage + "echo/"):
        if echo in ("carbonarea", "favorites"):
            continue  # not echo

        with codecs.open(storage + "echo/" + echo, "r", "utf-8") as f:
            exists = next(filter(lambda it: it.strip() == msgid,
                                 f.read().split("\n")), None)
            if exists:
                return readMsg(msgid, echo)
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
        echoareas = [echoarea]
    else:
        echoareas = sorted(list(filter(
            lambda e: e not in ("favorites", "carbonarea"),
            os.listdir(storage + "echo/"))))

    threadMsgids = []
    for echo in echoareas:
        echoMsgids = getEchoMsgids(echo)
        for msgid in echoMsgids:
            header = _readHeader(msgid)
            if header[6] in (subj, subjRe, subjReSpace):
                threadMsgids.append(MsgMetadata.fromList(msgid, header))
    return threadMsgids


FIND_CANCEL = 1
FIND_OK = 0


def findQueryMsgids(fq: FindQuery,
                    progressHandler: Callable = None) -> List[MsgMetadata]:
    echoareas = sorted(list(filter(
        lambda e: e not in ("favorites", "carbonarea"),
        os.listdir(storage + "echo/"))))
    echoareas = filterEchoarea(fq, echoareas, 0)
    #
    findResult = []
    totalMsgProgress = 0
    echoProgress = 0
    totalEchoareas = len(echoareas)
    match, matchNot = buildFindMatchers(fq)

    for echo in echoareas:
        echoMsgids = getEchoMsgids(echo)
        echoProgress += 1
        echoMsgProgress = 0
        echoTotalMsgs = len(echoMsgids)

        for msgid_ in echoMsgids:
            if len(findResult) >= fq.limit:
                return findResult
            totalMsgProgress += 1
            echoMsgProgress += 1
            if progressHandler:
                progress = (echoProgress, totalEchoareas,
                            echoMsgProgress, echoTotalMsgs,
                            totalMsgProgress, len(findResult))
                if progressHandler(progress) == FIND_CANCEL:
                    return []
            #
            with open(storage + "msg/" + msgid_, "r") as f:
                msg = f.read().split("\n")

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
