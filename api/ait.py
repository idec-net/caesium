# coding=utf-8
import codecs
import os
from typing import Optional, List, Callable

from . import MsgMetadata

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


def get_echo_length(echo):
    if os.path.exists(storage + echo + ".iat"):
        echo_length = sum(1 for _ in open(storage + echo + ".iat", "r", newline="\n"))
    else:
        echo_length = 0
    return echo_length


def save_to_favorites(msgid, msg):
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


def get_echo_msgids(echo):
    if os.path.exists(storage + echo + ".iat"):
        with codecs.open(storage + echo + ".iat", "r", "utf-8") as f:
            return list(filter(None, f.read().splitlines()))
    return []


def get_echo_msgs_metadata(echo):
    # type: (str) -> List[MsgMetadata]
    if not os.path.exists(storage + echo + ".mat"):
        return []

    echo_msgs = []
    with codecs.open(storage + echo + ".mat", "r", "utf-8") as f:
        for str_msg in filter(None, f.read().split("\n")):
            msgid, msg = str_msg.split(":", maxsplit=1)
            msg = msg.split(chr(15))
            echo_msgs.append(MsgMetadata.from_list(msgid, msg))
    return echo_msgs


def get_carbonarea():
    if os.path.exists(storage + "carbonarea.iat"):
        with open(storage + "carbonarea.iat", "r") as f:
            return list(filter(None, f.read().splitlines()))
    return []


def add_to_carbonarea(msgid, msgbody):
    with codecs.open(storage + "carbonarea.iat", "a", "utf-8") as f:
        f.write(msgid + "\n")
    with codecs.open(storage + "carbonarea.mat", "a", "utf-8") as f:
        f.write(msgid + ":" + chr(15).join(msgbody) + "\n")


# noinspection PyUnusedLocal
def save_message(raw, node, to):
    for msg in raw:
        msgid = msg[0]
        msgbody = msg[1]
        with codecs.open(storage + msgbody[1] + ".iat", "a", "utf-8") as f:
            f.write(msgid + "\n")
        with codecs.open(storage + msgbody[1] + ".mat", "a", "utf-8") as f:
            f.write(msgid + ":" + chr(15).join(msgbody) + "\n")
        if to:
            carbonarea = get_carbonarea()
            for name in to:
                if name in msgbody[5] and msgid not in carbonarea:
                    add_to_carbonarea(msgid, msgbody)


def get_favorites_list():
    if not os.path.exists(storage + "favorites.iat"):
        return []
    with codecs.open(storage + "favorites.iat", "r", "utf-8") as f:
        return f.read().splitlines()


def remove_from_favorites(msgid):
    with codecs.open(storage + "favorites.mat", "r", "utf-8") as f:
        favorites_list = f.read().split("\n")
    favorites = []
    favorites_index = []
    for item in favorites_list:
        if not item.startswith(msgid + ":"):
            favorites.append(item)
            favorites_index.append(item.split(":")[0])
    with codecs.open(storage + "favorites.iat", "w", "utf-8") as f:
        f.write("\n".join(favorites_index))
    with codecs.open(storage + "favorites.mat", "w", "utf-8") as f:
        f.write("\n".join(favorites))


def remove_echoarea(echoarea):
    if os.path.exists(storage + "%s.iat" % echoarea):
        os.remove(storage + "%s.iat" % echoarea)
    if os.path.exists(storage + "%s.mat" % echoarea):
        os.remove(storage + "%s.mat" % echoarea)


def get_msg_list_data(echoarea, msgids=None):
    # type: (Optional[str], List[str]) -> List[MsgMetadata]
    if echoarea:
        echoareas = [echoarea + ".mat"]
    else:
        echoareas = sorted(list(filter(
            lambda e: e.endswith(".mat") and e not in ("favorites.mat",
                                                       "carbonarea.mat"),
            os.listdir(storage))))
    lst = []
    for echo in echoareas:
        with codecs.open(storage + echo, "r", "utf-8") as f:
            for msg in filter(None, f.read().split("\n")):
                rawmsg = msg.split(chr(15))
                msgid, rawmsg[0] = rawmsg[0].split(":")
                if msgids and msgid not in msgids:
                    continue  # msg
                lst.append(MsgMetadata.from_list(msgid, rawmsg))
    return lst


def read_msg(msgid, echoarea):
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


def find_msg(msgid):
    for echo in os.listdir(storage):
        if echo in ("carbonarea.iat", "favorites.iat") or not echo.endswith(".iat"):
            continue  # not echo

        with codecs.open(storage + echo, "r", "utf-8") as f:
            exists = list(filter(lambda it: it.strip() == msgid,
                                 f.read().split("\n")))
            if exists:
                return read_msg(msgid, echo[0:-len(".iat")])
    return ["", "", "", "", "", "", "", "", "Сообщение отсутствует в базе"], 0


def find_subj_msgids(echoarea, subj):
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

    thread_msgs = []
    for echo in echoareas:
        with codecs.open(storage + echo, "r", "utf-8") as f:
            for str_msg in filter(None, f.read().split("\n")):
                msgid, msg = str_msg.split(":", maxsplit=1)
                msg = msg.split(chr(15))
                if msg[6] in (subj, subjRe, subjReSpace):
                    thread_msgs.append(MsgMetadata.from_list(msgid, msg))
    return thread_msgs


FIND_CANCEL = 1
FIND_OK = 0


def find_query_msgids(query, msgid, body, subj, fr, to, echoarea,
                      limit=1000, progress_handler=None):
    # type: (str, bool, bool, bool, bool, bool, str, int, Callable) -> List[MsgMetadata]
    query_low = query.lower()

    def match(s):
        return query_low in s.lower()

    echoareas = sorted(list(filter(
        lambda e: e.endswith(".mat") and e not in ("favorites.mat",
                                                   "carbonarea.mat"),
        os.listdir(storage))))
    if echoarea:
        echoareas = list(filter(lambda e: echoarea in e[0:-4], echoareas))

    find_result = []
    total_msg_progress = 0
    echo_progress = 0
    total_echoareas = len(echoareas)

    for echo in echoareas:
        with codecs.open(storage + echo, "r", "utf-8") as f:
            echo_msgs = list(filter(None, f.read().split("\n")))
        echo_progress += 1
        echo_msg_progress = 0
        echo_total_msgs = len(echo_msgs)

        for msg in echo_msgs:
            if len(find_result) >= limit:
                return find_result  #
            #
            total_msg_progress += 1
            echo_msg_progress += 1
            if progress_handler:
                progress = (echo_progress, total_echoareas,
                            echo_msg_progress, echo_total_msgs,
                            total_msg_progress, len(find_result))
                if progress_handler(progress) == FIND_CANCEL:
                    return []
            #
            msg = msg.split(chr(15))
            msgid_, msg[0] = msg[0].split(":")
            if msgid and msgid_ == query:
                find_result.append(MsgMetadata.from_list(msgid_, msg))
                continue  #
            if body and match("\n".join(msg[7:])):
                find_result.append(MsgMetadata.from_list(msgid_, msg))
                continue  #
            if subj and match(msg[6]):
                find_result.append(MsgMetadata.from_list(msgid_, msg))
                continue  #
            if fr and match(msg[3]):
                find_result.append(MsgMetadata.from_list(msgid_, msg))
                continue  #
            if to and match(msg[5]):
                find_result.append(MsgMetadata.from_list(msgid_, msg))
                continue  #
    return find_result


def get_node_features(node):  # type: (str) -> Optional[List[str]]
    features = storage + "nodes/" + node + ".x-features"
    if not os.path.exists(features):
        return None  #

    with open(features, "r") as f:
        return list(filter(None, map(lambda it: it.strip(),
                                     f.read().splitlines())))


def save_node_features(node, features):  # type: (str, List[str]) -> None
    x_features = storage + "nodes/" + node + ".x-features"
    with open(x_features, "w") as f:
        f.write("\n".join(features))


def get_node_echo_counts(node):  # type: (str) -> Optional[dict[str, int]]
    x_counts = storage + "nodes/" + node + ".x-counts"
    if not os.path.exists(x_counts):
        return None  #

    with open(x_counts, "r") as f:
        echo_counts = list(filter(None, map(lambda it: it.strip().split(":"),
                                            f.read().splitlines())))
        return {echo[0]: int(echo[1]) for echo in echo_counts}


def save_node_echo_counts(node, echo_counts):  # type: (str, dict[str, int]) -> None
    ec = ["%s:%s\n" % (echo, str(count))
          for echo, count in echo_counts.items()]
    x_counts = storage + "nodes/" + node + ".x-counts"
    with open(x_counts, "w") as f:
        f.writelines(ec)
