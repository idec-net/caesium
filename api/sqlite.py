# coding=utf-8
import sqlite3
from datetime import datetime
from typing import Optional, List, Callable

from . import MsgMetadata, FindQuery, buildFindMatcher
from core import FEAT_FEATURES, FEAT_X_C

con = None  # type: Optional[sqlite3.Connection]
c = None  # type: Optional[sqlite3.Cursor]


# Frequently Asked Questions
# (18) Case-insensitive matching of Unicode characters does not work.
# https://www.sqlite.org/faq.html#q18
#
# All the missing SQLite functions
# https://github.com/nalgeon/sqlean/
#
# 5 ways to implement case-insensitive search in SQLite with full Unicode support
# https://shallowdepth.online/posts/2022/01/5-ways-to-implement-case-insensitive-search-in-sqlite-with-full-unicode-support/


def init(db="idec.db"):
    global con, c
    con = sqlite3.connect(db)
    c = con.cursor()

    # Create database
    c.execute("""CREATE TABLE IF NOT EXISTS msg(
        id         INTEGER PRIMARY KEY AUTOINCREMENT UNIQUE NOT NULL,
        msgid      TEXT,
        favorites  INTEGER DEFAULT 0,
        carbonarea INTEGER DEFAULT 0,
        tags       TEXT,
        echoarea   TEXT,
        time       INTEGER,
        fr         TEXT,
        addr       TEXT,
        t          TEXT,
        subject    TEXT,
        body       TEXT);""")
    c.execute("CREATE INDEX IF NOT EXISTS msgid    ON 'msg' ('msgid');")
    c.execute("CREATE INDEX IF NOT EXISTS echoarea ON 'msg' ('echoarea');")
    c.execute("CREATE INDEX IF NOT EXISTS time     ON 'msg' ('time');")
    c.execute("CREATE INDEX IF NOT EXISTS subject  ON 'msg' ('subject');")
    c.execute("CREATE INDEX IF NOT EXISTS body     ON 'msg' ('body');")

    c.execute("""CREATE TABLE IF NOT EXISTS node_feature(
        node        TEXT,
        feature     TEXT,
        response    TEXT,
        PRIMARY KEY (node, feature));""")
    c.execute("CREATE INDEX IF NOT EXISTS ix_node_feature"
              " ON node_feature (node, feature);")

    con.commit()


def getEchoLength(echo):
    row = c.execute("SELECT COUNT(1) FROM msg WHERE echoarea = ?;",
                    (echo,)).fetchone()
    return row[0]


# noinspection PyUnusedLocal
def saveToFavorites(msgid, msg):
    favorites = c.execute("SELECT COUNT(1) FROM msg WHERE msgid = ? AND favorites = 1",
                          (msgid,)).fetchone()[0]
    if favorites == 0:
        c.execute("UPDATE msg SET favorites = 1 WHERE msgid = ?;", (msgid,))
        con.commit()
        return True
    else:
        return False


def getEchoMsgids(echo):
    msgids = []
    for row in c.execute("SELECT msgid FROM msg WHERE echoarea = ? ORDER BY id;",
                         (echo,)):
        if row[0]:
            msgids.append(row[0])
    return msgids


def getEchoMsgsMetadata(echo):
    # type: (str) -> List[MsgMetadata]
    if echo == "favorites":
        rows = c.execute(
            "SELECT msgid, tags, echoarea, time, fr, addr, t, subject"
            " FROM msg WHERE favorites = 1 ORDER BY id;")
    elif echo == "carbonarea":
        rows = c.execute(
            "SELECT msgid, tags, echoarea, time, fr, addr, t, subject"
            " FROM msg WHERE carbonarea = 1 ORDER BY id;")
    else:
        rows = c.execute(
            "SELECT msgid, tags, echoarea, time, fr, addr, t, subject"
            " FROM msg WHERE echoarea = ? ORDER BY id;",
            (echo,))
    return list(map(lambda r: MsgMetadata.fromList(r[0], r[1:]), rows))


def getCarbonarea():
    msgids = []
    for row in c.execute("SELECT msgid FROM msg WHERE carbonarea = 1 ORDER BY id"):
        msgids.append(row[0])
    return msgids


# noinspection PyUnusedLocal
def addToCarbonarea(msgid, msgbody):
    c.execute("UPDATE msg SET carbonarea = 1 WHERE msgid = ?;",
              (msgid,))
    con.commit()


# noinspection PyUnusedLocal
def saveMessage(raw, node, to):
    for msg in raw:
        msgid = msg[0]
        msgbody = msg[1]
        c.execute(
            "INSERT INTO msg ("
            " msgid, tags, echoarea, time, fr, addr,"
            " t, subject, body"
            ") VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);",
            (msgid, msgbody[0], msgbody[1], msgbody[2], msgbody[3], msgbody[4],
             msgbody[5], msgbody[6], "\n".join(msgbody[7:])))
    con.commit()
    for msg in raw:
        msgid = msg[0]
        msgbody = msg[1]
        if to:
            carbonarea = getCarbonarea()
            for name in to:
                if name in msgbody[5] and msgid not in carbonarea:
                    addToCarbonarea(msgid, msgbody)


def getFavoritesList():
    msgids = []
    for row in c.execute("SELECT msgid FROM msg WHERE favorites = 1;"):
        msgids.append(row[0])
    return msgids


def removeFromFavorites(msgid):
    c.execute("UPDATE msg SET favorites = 0 WHERE msgid = ?;", (msgid,))
    con.commit()


def removeEchoarea(echoarea):
    c.execute("DELETE FROM msg WHERE echoarea = ?;", (echoarea,))
    con.commit()


# noinspection PyUnusedLocal
def readMsg(msgid, echoarea):
    row = c.execute("SELECT tags, echoarea, time, fr, addr, t, subject, body"
                    " FROM msg WHERE msgid = ?;",
                    (msgid,)).fetchone()
    if not row:
        return ["", "", "", "", "", "", "", "", "Сообщение отсутствует в базе"], 0
    msg = "\n".join((row[0], row[1], str(row[2]), row[3],
                     row[4], row[5], row[6], row[7]))

    size = len(msg.encode("utf-8"))
    return msg.split("\n"), size


def findMsg(msgid):
    return readMsg(msgid, None)


def findSubjMsgids(echoarea, subj):  # type: (str, str) -> List[str]
    if subj.startswith("Re: "):
        subj = subj[4:]
    elif subj.startswith("Re:"):
        subj = subj[3:]
    subjRe = "Re:" + subj
    subjReSpace = "Re: " + subj
    whereClause = "TRUE"
    args = []
    if echoarea:
        whereClause += " AND echoarea = ? "
        args.append(echoarea)

    rows = c.execute("SELECT msgid, tags, echoarea, time, fr, addr, t, subject"
                     " FROM msg"
                     " WHERE %s"
                     "   AND (subject = ? OR subject = ? OR subject = ?)"
                     " ORDER BY id"
                     " LIMIT 1000;" % whereClause,
                     (*args, subj, subjRe, subjReSpace))
    return list(map(lambda r: MsgMetadata.fromList(r[0], r[1:]), rows))


FIND_CANCEL = 1
FIND_OK = 0


def findQueryMsgids(fq: FindQuery,
                    progressHandler: Callable = None) -> List[MsgMetadata]:
    args = []
    where = []
    progress = 0

    # noinspection PyUnusedLocal
    def countMsg(arg):
        nonlocal progress
        progress += 1
        return 1  # always TRUE

    con.create_function("PROGRESS", 1, countMsg)

    if fq.query:
        match = buildFindMatcher(fq.query, fq)
        con.create_function("MATCH", 1, match)

        if fq.msgid:
            where.append("msgid = ?")
            args.append(fq.query)
        if fq.body:
            where.append("MATCH(body)")
        if fq.subj:
            where.append("MATCH(subject)")
        if fq.fr:
            where.append("MATCH(fr)")
        if fq.to:
            where.append("MATCH(t)")

    if where:
        where = "PROGRESS(msgid) AND (" + " OR ".join(where) + ")"
    else:
        where = "PROGRESS(msgid)"

    if fq.queryNot:
        matchNot = buildFindMatcher(fq.queryNot, fq)
        con.create_function("MATCH_NOT", 1, matchNot)

        whereNot = []
        if fq.body:
            whereNot.append("NOT MATCH_NOT(body)")
        if fq.subj:
            whereNot.append("NOT MATCH_NOT(subject)")
        if fq.fr:
            whereNot.append("NOT MATCH_NOT(fr)")
        if fq.to:
            whereNot.append("NOT MATCH_NOT(t)")
        if whereNot:
            where += " AND (" + " AND ".join(whereNot) + ")"

    count_where = "TRUE"
    count_args = []
    if fq.dtFr:
        dtFr = int(datetime.combine(fq.dtFr, datetime.min.time()).timestamp())
        where += " AND time >= ?"
        args.append(dtFr)
        count_where += " AND time >= ?"
        count_args.append(dtFr)

    if fq.dtTo:
        dtTo = int(datetime.combine(fq.dtTo, datetime.max.time()).timestamp())
        where += " AND time <= ?"
        args.append(dtTo)
        count_where += " AND time <= ?"
        count_args.append(dtTo)

    if fq.echo and fq.echoQuery:
        echos = list(filter(None, fq.echoQuery.split(" ")))
        where += " AND (" + " OR ".join([" echoarea LIKE ? "] * len(echos)) + ")"
        for e in echos:
            args.append("%" + e + "%")
        count_where += " AND (" + " OR ".join([" echoarea LIKE ? "] * len(echos)) + ")"
        for e in echos:
            count_args.append("%" + e + "%")
    if fq.echo and fq.echoQueryNot:
        echos = list(filter(None, fq.echoQueryNot.split(" ")))
        where += " AND " + " AND ".join(["echoarea NOT LIKE ?"] * len(echos))
        for e in echos:
            args.append("%" + e + "%")
        count_where += " AND " + " AND ".join(["echoarea NOT LIKE ?"] * len(echos))
        for e in echos:
            count_args.append("%" + e + "%")
    if fq.echoSkipArch and fq.echoArch:
        echos = list(filter(None, fq.echoArch.split(" ")))
        where += " AND " + " AND ".join(["echoarea <> ?"] * len(echos))
        args.extend(echos)
        count_where += " AND " + " AND ".join(["echoarea <> ?"] * len(echos))
        count_args.extend(echos)
    try:
        if progressHandler:
            total = c.execute(
                "SELECT COUNT(DISTINCT msgid)"
                " FROM msg"
                " WHERE %s;" % count_where,
                count_args).fetchone()[0]

            def progressHandlerWrapper():
                progressHandler((0, 0, 0, 0, progress, 0, total))

            con.set_progress_handler(progressHandlerWrapper, 100)

        rows = c.execute(
            "SELECT DISTINCT msgid, tags, echoarea, time, fr, addr, t, subject"
            " FROM msg"
            " WHERE %s"
            " ORDER BY id"
            " LIMIT ?;" % where,
            (*args, fq.limit))
        return list(map(lambda r: MsgMetadata.fromList(r[0], r[1:]), rows))
    except sqlite3.OperationalError as ex:
        if "interrupted" == str(ex):
            return []  #
        raise ex
    finally:
        con.create_function("PROGRESS", 1, None)
        con.create_function("MATCH", 1, None)
        con.create_function("MATCH_NOT", 1, None)
        con.set_progress_handler(None, 1)


def getNodeFeatures(node):  # type: (str) -> Optional[List[str]]
    features = c.execute("SELECT response FROM node_feature"
                         " WHERE node = ? AND feature = ?;",
                         (node, FEAT_FEATURES)).fetchone()
    if features:
        return list(filter(None, map(lambda it: it.strip(),
                                     features[0].splitlines())))
    return None


def saveNodeFeatures(node, features):  # type: (str, List[str]) -> None
    features = "\n".join(features)
    c.execute("DELETE FROM node_feature WHERE node = ? AND feature = ?;",
              (node, FEAT_FEATURES))
    c.execute("INSERT INTO node_feature (node, feature, response) VALUES (?, ?, ?);",
              (node, FEAT_FEATURES, features))
    con.commit()


def getNodeEchoCounts(node):  # type: (str) -> Optional[dict[str, int]]
    ec = c.execute("SELECT response FROM node_feature"
                   " WHERE node = ? AND feature = ?;",
                   (node, FEAT_X_C)).fetchone()
    if ec:
        echoCounts = list(filter(None, map(lambda it: it.strip().split(":"),
                                           ec[0].splitlines())))
        return {echo[0]: int(echo[1]) for echo in echoCounts}
    return None


def saveNodeEchoCounts(node, echo_counts):  # type: (str, dict[str, int]) -> None
    ec = ["%s:%s\n" % (echo, str(count))
          for echo, count in echo_counts.items()]
    ec = "".join(ec)

    c.execute("DELETE FROM node_feature WHERE node = ? AND feature = ?;",
              (node, FEAT_X_C))
    c.execute("INSERT INTO node_feature (node, feature, response) VALUES (?, ?, ?);",
              (node, FEAT_X_C, ec))
    con.commit()
