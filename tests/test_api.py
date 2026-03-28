import base64
import os
import shutil
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from api import MsgMetadata, FindQuery, buildFindMatcher


def test_initAio():
    import api.aio as api
    api.init("test2.aio")
    assert api.storage == "test2.aio/"
    assert Path("test2.aio").is_dir()
    shutil.rmtree(Path("test2.aio"))


def test_initAit():
    import api.ait as api
    api.init("test2.ait")
    assert api.storage == "test2.ait/"
    assert Path("test2.ait").is_dir()
    shutil.rmtree(Path("test2.ait"))


def test_initSqlite():
    import api.sqlite as api
    api.init("test2.db")
    assert api.c
    assert api.con
    assert Path("test2.db").is_file()
    os.remove(Path("test2.db"))


def test_initTxt():
    import api.txt as api
    api.init("test2.txt")
    assert api.storage == "test2.txt/"
    assert Path("test2.txt").is_dir()
    shutil.rmtree("test2.txt")


@pytest.fixture
def api(storage):
    if storage == "aio":
        import api.aio as api
        api.init("test.aio")
    elif storage == "ait":
        import api.ait as api
        api.init("test.ait")
    elif storage == "sqlite":
        import api.sqlite as api
        api.init("test.db")
    elif storage == "txt":
        import api.txt as api
        api.init("test.txt")
    else:
        raise ValueError("Unknown API")
    clean(api)
    try:
        yield api
    finally:
        clean(api)


def clean(api):
    api.removeEchoarea("test.local")
    api.removeEchoarea("test2.local")
    api.removeEchoarea("test3.local")
    api.removeEchoarea("carbonarea")
    api.removeEchoarea("favorites")
    api.removeEchoarea("idec.talks")


# noinspection PyTestParametrized
@pytest.mark.parametrize("storage", ["aio", "ait", "sqlite", "txt"])
def test_getEchoLength(api):
    assert api.getEchoLength("ring2.global") == 4
    assert api.getEchoLength("test.local") == 0


# noinspection PyTestParametrized
@pytest.mark.parametrize("storage", ["aio", "ait", "sqlite", "txt"])
def test_saveMessages(api):
    assert api.getEchoLength("test.local") == 0

    msg1 = ["ii/ok", "test.local", "0", "admin", "node,1", "All", "Subj", "", "Msg1", "Row2"]
    msg2 = ["ii/ok", "test.local", "0", "admin", "node,1", "All", "Subj", "", "Msg2", "Row2"]

    api.saveMessage([("11", msg1), ("22", msg2)], "node", "user")
    assert api.getEchoLength("test.local") == 2
    #
    msg, size = api.readMsg("11", "test.local")
    assert msg == msg1

    msg, size = api.readMsg("22", "test.local")
    assert msg == msg2

    msgids = api.getEchoMsgids("test.local")
    assert msgids == ["11", "22"]
    assert api.getEchoMsgsMetadata("test.local") == [MsgMetadata.fromList("11", msg1),
                                                     MsgMetadata.fromList("22", msg2)]


# noinspection PyTestParametrized
@pytest.mark.parametrize("storage", ["aio", "ait", "sqlite", "txt"])
def test_addToCarbonarea(api):
    assert api.getEchoLength("test.local") == 0

    msg1 = ["ii/ok", "test.local", "0", "admin", "node,1", "All", "Subj", "", "Msg1", "Row2"]
    msg2 = ["ii/ok", "test.local", "0", "admin", "node,1", "user", "Subj", "", "Msg2", "Row2"]

    api.saveMessage([("1" * 20, msg1), ("2" * 20, msg2)], "node", ["user"])
    assert api.getEchoLength("test.local") == 2
    assert api.getCarbonarea() == ["2" * 20]
    #
    msg, size = api.readMsg("1" * 20, "test.local")
    assert msg == msg1

    msg, size = api.readMsg("2" * 20, "carbonarea")
    assert msg == msg2

    data = api.getEchoMsgsMetadata("carbonarea")
    assert data == [MsgMetadata.fromList("2" * 20, msg2)]


# noinspection PyTestParametrized
@pytest.mark.parametrize("storage", ["aio", "ait", "sqlite", "txt"])
def test_saveFavorites(api):
    assert not api.getFavoritesList()

    msg1 = ["ii/ok", "test.local", "0", "admin", "node,1", "All", "Subj", "", "Msg1", "Row2"]
    msg2 = ["ii/ok", "test.local", "0", "admin", "node,1", "user", "Subj", "", "Msg2", "Row2"]
    api.saveMessage([("1" * 20, msg1), ("2" * 20, msg2)], "node", ["user"])
    api.saveToFavorites("2" * 20, msg2)

    favorites = api.getFavoritesList()
    assert favorites == ["2" * 20]
    msg, size = api.readMsg("2" * 20, "favorites")
    assert msg == msg2

    data = api.getEchoMsgsMetadata("favorites")
    assert data == [MsgMetadata.fromList("2" * 20, msg2)]

    api.removeFromFavorites("2" * 20)
    assert not api.getFavoritesList()

    data = api.getEchoMsgsMetadata("favorites")
    assert data == []


# noinspection PyTestParametrized
@pytest.mark.parametrize("storage", ["aio", "ait", "sqlite", "txt"])
def test_removeFromFavorites(api):
    msg1 = ["ii/ok", "test.local", "0", "admin", "node,1", "All", "Subj", "", "Msg1", "Row2"]
    msg2 = ["ii/ok", "test.local", "0", "admin", "node,1", "user", "Subj", "", "Msg2", "Row2"]
    api.saveMessage([("1" * 20, msg1), ("2" * 20, msg2)], "node", ["user"])
    api.saveToFavorites("1" * 20, msg1)
    api.saveToFavorites("2" * 20, msg2)
    #
    api.removeFromFavorites("1" * 20)
    #
    favorites = api.getFavoritesList()
    assert favorites == ["2" * 20]
    msg, size = api.readMsg("2" * 20, "favorites")
    assert msg == msg2


# noinspection PyTestParametrized
@pytest.mark.parametrize("storage", ["aio", "ait", "sqlite", "txt"])
def test_nonPrintable(api):
    msgid = "nFaF9Z8R81USSRIE7YUF"
    msgbody = ("aWkvb2sKaWRlYy50YWxrcwoxNzI5NjA0OTcyCnJldm9sdGVj"
               "aAp0Z2ksMTUKQWxsCkZpcnN0IHRlc3QKChwVLyASGBQePwo=")
    msgbody = base64.b64decode(msgbody).decode("utf8").split("\n")
    #
    api.saveMessage([(msgid, msgbody)], "", "")
    #
    assert api.getEchoLength("idec.talks") == 1
    assert api.getEchoMsgids("idec.talks") == [msgid]
    assert api.getEchoMsgsMetadata("idec.talks") == [MsgMetadata.fromList(msgid, msgbody)]
    #
    msg, _ = api.readMsg(msgid, "idec.talks")
    assert msg == msgbody
    #
    api.saveToFavorites(msgid, msgbody)
    assert api.getFavoritesList() == [msgid]
    msg, _ = api.readMsg(msgid, "favorites")
    assert msg == msgbody

    data = api.getEchoMsgsMetadata("idec.talks")
    assert data == [MsgMetadata.fromList(msgid, msgbody)]


# noinspection PyTestParametrized
@pytest.mark.parametrize("storage", ["aio", "ait", "sqlite", "txt"])
def test_findMsg(api):
    msg, size = api.findMsg("unknonwnmsgid")
    assert msg == ["", "", "", "", "", "", "", "", "Сообщение отсутствует в базе"]
    assert size == 0

    msg, size = api.findMsg("25Ll1pZMnIbdWB8Ring2")
    assert msg[1] == "ring2.global"
    assert size == 81


# noinspection PyTestParametrized
@pytest.mark.parametrize("storage", ["aio", "ait", "sqlite", "txt"])
def test_nodeFeatures(api):
    features = api.getNodeFeatures("unknown")
    assert features is None
    #
    api.saveNodeFeatures("node", ["feat1", "", "feat2"])
    features = api.getNodeFeatures("node")
    assert features == ["feat1", "feat2"]
    #
    api.saveNodeFeatures("node", ["feat1", "feat3"])
    features = api.getNodeFeatures("node")
    assert features == ["feat1", "feat3"]


# noinspection PyTestParametrized
@pytest.mark.parametrize("storage", ["aio", "ait", "sqlite", "txt"])
def test_nodeEchoCounts(api):
    ec = api.getNodeEchoCounts("unknown")
    assert ec is None
    #
    api.saveNodeEchoCounts("node", {"echo.1": 1, "echo.2": 2})
    ec = api.getNodeEchoCounts("node")
    assert ec == {"echo.1": 1, "echo.2": 2}
    #
    api.saveNodeEchoCounts("node", {"echo.2": 2, "echo.3": 3})
    ec = api.getNodeEchoCounts("node")
    assert ec == {"echo.2": 2, "echo.3": 3}


# noinspection PyTestParametrized
@pytest.mark.parametrize("storage", ["aio", "ait", "sqlite", "txt"])
def test_findSubjMsgids(api):
    msg1 = ["ii/ok", "test.local", "0", "admin", "node,1", "All", "Subj", "", "Msg1", "Row2"]
    msg2 = ["ii/ok", "test.local", "1", "admin", "node,1", "user", "Re: Subj", "", "Msg2", "Row2"]
    msg3 = ["ii/ok", "test.local", "2", "admin", "node,1", "user", "Subj2", "", "Msg2", "Row2"]
    api.saveMessage([("1" * 20, msg1), ("2" * 20, msg2), ("3" * 20, msg3)], "node", ["user"])

    data = api.findSubjMsgids("test.local", "Re: Subj")
    assert data == [MsgMetadata.fromList("1" * 20, msg1),
                    MsgMetadata.fromList("2" * 20, msg2)]

    data = api.findSubjMsgids(None, "Re: Subj")
    assert data == [MsgMetadata.fromList("1" * 20, msg1),
                    MsgMetadata.fromList("2" * 20, msg2)]


# noinspection PyTestParametrized
@pytest.mark.parametrize("storage", ["aio", "ait", "sqlite", "txt"])
def test_findQueryMsgids(api):
    msg1 = ["ii/ok", "test.local", "0", "юзер", "node,1", "All", "Сабж", "", "Msg1", "Row2"]
    msg2 = ["ii/ok", "test2.local", "1", "admin", "node,1", "юзер", "Re: Subj", "", "Мсг2", "Row2"]
    api.saveMessage([("1" * 20, msg1), ("2" * 20, msg2)], "node", ["user"])

    def query(q, msgid=False, body=False, subj=False, fr=False, to=False,
              echo=False, echoQuery=""):
        return FindQuery(query=q,
                         msgid=msgid, body=body, subj=subj, fr=fr, to=to,
                         echo=echo, echoQuery=echoQuery)

    # msgid exact
    data = api.findQueryMsgids(query("1" * 20, True, False, False, True, False, False))
    assert data == [MsgMetadata.fromList("1" * 20, msg1)]
    data = api.findQueryMsgids(query("1" * 19, True, False, False, True, False, False))
    assert data == []
    # unicode body
    data = api.findQueryMsgids(query("Мсг2", True, True, True, True, True, False))
    assert data == [MsgMetadata.fromList("2" * 20, msg2)]
    # unicode subj
    data = api.findQueryMsgids(query("Сабж", True, True, True, True, True, False))
    assert data == [MsgMetadata.fromList("1" * 20, msg1)]
    # unicode from
    data = api.findQueryMsgids(query("юзер", False, False, False, True, False, False))
    assert data == [MsgMetadata.fromList("1" * 20, msg1)]
    # unicode to
    data = api.findQueryMsgids(query("юзер", False, False, False, False, True, False))
    assert data == [MsgMetadata.fromList("2" * 20, msg2)]
    # unicode echo only
    data = api.findQueryMsgids(query("Row2", True, True, True, True, True, True, "test2.local"))
    assert data == [MsgMetadata.fromList("2" * 20, msg2)]
    # empty results
    data = api.findQueryMsgids(query("Unknown", True, True, True, True, True, False))
    assert data == []


# noinspection PyTestParametrized
@pytest.mark.parametrize("storage", ["aio", "ait", "sqlite", "txt"])
def test_findQueryMatcher(api):
    msg1 = ["ii/ok", "test.local", "0", "u", "n,1", "t", "S", "", "", "zxcqwe+", "zxcQWE+"]
    msg2 = ["ii/ok", "test.local", "1", "u", "n,1", "t", "S", "", "", " +++ zxc+", " zxc+"]
    msg3 = ["ii/ok", "test.local", "1", "u", "n,1", "t", "S", "", "", " qwe+", " QWE+"]
    msg4 = ["ii/ok", "test.local", "1", "u", "n,1", "t", "S", "", "", " +++ qwe+", " +++ QWE+"]
    msg5 = ["ii/ok", "test.local", "1", "u", "n,1", "t", "S", "", "", "юникод+", ""]
    msg6 = ["ii/ok", "test.local", "1", "u", "n,1", "t", "S", "", "", " +++ ЮНИКОД+", ""]
    api.saveMessage([("1" * 20, msg1),
                     ("2" * 20, msg2),
                     ("3" * 20, msg3),
                     ("4" * 20, msg4),
                     ("5" * 20, msg5),
                     ("6" * 20, msg6)],
                    "node", None)

    def query(q, regex=False, case=False, word=False, orig=False):
        return FindQuery(
            query=q,
            msgid=False, subj=False, fr=False, to=False, echo=False, body=True,
            regex=regex, case=case, word=word, orig=orig)
    #
    data = api.findQueryMsgids(query("qwe+", regex=True, orig=True))
    assert data == [MsgMetadata.fromList("1" * 20, msg1),
                    MsgMetadata.fromList("3" * 20, msg3),
                    MsgMetadata.fromList("4" * 20, msg4)]

    data = api.findQueryMsgids(query("qwe+", case=True, word=True))
    assert data == [MsgMetadata.fromList("3" * 20, msg3)]

    data = api.findQueryMsgids(query("юникод+", case=False, orig=True))
    assert data == [MsgMetadata.fromList("5" * 20, msg5),
                    MsgMetadata.fromList("6" * 20, msg6)]

    data = api.findQueryMsgids(query("юникод+", case=True, orig=True))
    assert data == [MsgMetadata.fromList("5" * 20, msg5)]


# noinspection PyTestParametrized
@pytest.mark.parametrize("storage", ["aio", "ait", "sqlite", "txt"])
def test_findQueryEchoMulti(api):
    msg1 = ["ii/ok", "test.local", "0", "u", "n,1", "t", "S", "", "", "qwe", "qwe"]
    msg2 = ["ii/ok", "test2.local", "1", "u", "n,1", "t", "S", "", "", "qwe", "qwe"]
    msg3 = ["ii/ok", "test3.local", "1", "u", "n,1", "t", "S", "", "", " qwe", "qwe"]
    api.saveMessage([("1" * 20, msg1),
                     ("2" * 20, msg2),
                     ("3" * 20, msg3)],
                    "node", None)

    data = api.findQueryMsgids(
        FindQuery("qwe", echoQuery="test.local test3.local"))
    assert data == [MsgMetadata.fromList("1" * 20, msg1),
                    MsgMetadata.fromList("3" * 20, msg3)]

    data = api.findQueryMsgids(
        FindQuery("qwe", echoQueryNot="test.local test3.local"))
    assert data == [MsgMetadata.fromList("2" * 20, msg2)]


# noinspection PyTestParametrized
@pytest.mark.parametrize("storage", ["aio", "ait", "sqlite", "txt"])
def test_findQueryNotTo(api):
    msg1 = ["ii/ok", "test.local", "0", "u", "n,1", "RSS-bot", "S", "", "", "qwe", "qwe"]
    msg2 = ["ii/ok", "test2.local", "1", "u", "n,1", "robot", "S", "", "", "qwe", "qwe"]
    msg3 = ["ii/ok", "test3.local", "1", "u", "n,1", "t", "S", "", "", " qwe", "qwe"]
    api.saveMessage([("1" * 20, msg1),
                     ("2" * 20, msg2),
                     ("3" * 20, msg3)],
                    "node", None)

    data = api.findQueryMsgids(
        FindQuery("qwe", "bot", regex=True))
    assert data == [MsgMetadata.fromList("3" * 20, msg3)]

    data = api.findQueryMsgids(
        FindQuery("qwe", echoQueryNot="test. test2."))
    assert data == [MsgMetadata.fromList("3" * 20, msg3)]

    data = api.findQueryMsgids(
        FindQuery("qwe", echoSkipArch=True, echoArch="test.local test2.local"))
    assert data == [MsgMetadata.fromList("3" * 20, msg3)]


# noinspection PyTestParametrized
@pytest.mark.parametrize("storage", ["aio", "ait", "sqlite", "txt"])
def test_findQueryDate(api):
    now = datetime.now()
    msg1 = ["ii/ok", "test.local", str(int((now + timedelta(days=-1)).timestamp())),
            "u", "n,1", "t", "S", "", "", "qwe", "qwe"]
    msg2 = ["ii/ok", "test2.local", str(int(now.timestamp())),
            "u", "n,1", "t", "S", "", "", "qwe", "qwe"]
    msg3 = ["ii/ok", "test3.local", str(int((now + timedelta(days=+1)).timestamp())),
            "u", "n,1", "t", "S", "", "", " qwe", "qwe"]
    api.saveMessage([("1" * 20, msg1),
                     ("2" * 20, msg2),
                     ("3" * 20, msg3)],
                    "node", None)

    data = api.findQueryMsgids(FindQuery("qwe", dtFr=now.date()))
    assert data == [MsgMetadata.fromList("2" * 20, msg2),
                    MsgMetadata.fromList("3" * 20, msg3)]

    data = api.findQueryMsgids(FindQuery("qwe", dtTo=now.date()))
    assert data == [MsgMetadata.fromList("1" * 20, msg1),
                    MsgMetadata.fromList("2" * 20, msg2)]

    data = api.findQueryMsgids(FindQuery("qwe", dtFr=now.date(), dtTo=now.date()))
    assert data == [MsgMetadata.fromList("2" * 20, msg2)]


# noinspection PyTestParametrized
@pytest.mark.parametrize("storage", ["aio", "ait", "sqlite", "txt"])
def test_findQueryEmpty(api):
    data = api.findQueryMsgids(FindQuery())
    assert len(data) >= 4

    data = api.findQueryMsgids(FindQuery(queryNot="nnii"))
    assert len(data) == 1


def test_findMatcherRegex():
    # any case, anywhere
    matcher = buildFindMatcher(
        "qwe+", FindQuery(regex=True, case=False, word=False, orig=True))
    assert not matcher("\n +++ zxc+")  # query
    assert not matcher("\n zxc+")  # query
    assert matcher("\n qwe+")
    assert matcher("\n QWE+")
    assert matcher("\n +++ QWE+")
    assert matcher("\n +++ qwe+")
    assert matcher("zxcqwe+")
    assert matcher("zxcQWE+")
    assert matcher(" +++ zxcQWE+")
    assert matcher(" +++ zxcqwe+")

    # case, anywhere
    matcher = buildFindMatcher(
        "qwe+", FindQuery(regex=True, case=True, word=False, orig=True))
    assert not matcher("\n +++ zxc+")  # query
    assert not matcher("\n zxc+")  # query
    assert not matcher("\n QWE+")  # case
    assert not matcher("\n +++ QWE+")  # case
    assert matcher("\n qwe+")
    assert matcher("\n +++ qwe+")

    # any case, not origin
    matcher = buildFindMatcher(
        "qwe+", FindQuery(regex=True, case=False, word=False, orig=False))
    assert not matcher("\n +++ zxc+")  # query
    assert not matcher("\n zxc+")  # query
    assert not matcher("\n +++ QWE+")  # origin
    assert not matcher("\n +++ qwe+")  # origin
    assert matcher("\n QWE+")
    assert matcher("\n qwe+")

    # case, not origin
    matcher = buildFindMatcher(
        "qwe+", FindQuery(regex=True, case=True, word=False, orig=False))
    assert not matcher("\n +++ zxc+")  # query
    assert not matcher("\n zxc+")  # query
    assert not matcher("\n +++ qwe+")  # origin
    assert not matcher("\n +++ QWE+")  # origin
    assert not matcher("\n QWE+")  # case
    assert matcher("\n qwe+")


def test_findMatcherWord():
    # any case, anywhere
    matcher = buildFindMatcher(
        "qwe+", FindQuery(regex=False, case=False, word=True, orig=True))
    assert not matcher("\n +++ zxc+")  # query
    assert not matcher("\n zxc+")  # query
    assert not matcher("zxcqwe+")  # word
    assert not matcher("zxcQWE+")  # word
    assert not matcher(" +++ zxcQWE+")  # word
    assert not matcher(" +++ zxcqwe+")  # word
    assert matcher("\n qwe+")
    assert matcher("\n QWE+")
    assert matcher("\n.QWE+.")
    assert matcher("\n-QWE+-")
    assert matcher("\n +++ QWE+")
    assert matcher("\n +++ qwe+")

    # case, anywhere
    matcher = buildFindMatcher(
        "qwe+", FindQuery(regex=False, case=True, word=True, orig=True))
    assert not matcher("\n +++ zxc+")  # query
    assert not matcher("\n zxc+")  # query
    assert not matcher("\n QWE+")  # case
    assert not matcher("\n +++ QWE+")  # case
    assert not matcher("\n zxcqwe+")  # word
    assert matcher("\n qwe+")
    assert matcher("\n.qwe+.")
    assert matcher("\n-qwe+-")
    assert matcher("\n +++ qwe+")

    # any case, not origin
    matcher = buildFindMatcher(
        "qwe+", FindQuery(regex=False, case=False, word=True, orig=False))
    assert not matcher("\n +++ zxc+")  # query
    assert not matcher("\n zxc+")  # query
    assert not matcher("\n +++ QWE+")  # origin
    assert not matcher("\n +++ qwe+")  # origin
    assert not matcher("\n zxcqwe+")  # word
    assert not matcher("\n zxcQWE+")  # word
    assert matcher("\n QWE+")
    assert matcher("\n qwe+")

    # case, not origin
    matcher = buildFindMatcher(
        "qwe+", FindQuery(regex=False, case=True, word=True, orig=False))
    assert not matcher("\n +++ zxc+\n")  # query
    assert not matcher("\n zxc+\n")  # query
    assert not matcher("\n +++ qwe+\n")  # origin
    assert not matcher("\n +++ QWE+\n")  # origin
    assert not matcher("\n QWE+\n")  # case
    assert not matcher("\n zxcqwe+\n")  # word
    assert not matcher("\n zxcQWE+\n")  # word
    assert matcher("\n qwe+\n")
    assert matcher("qwe+")
