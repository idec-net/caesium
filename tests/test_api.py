import base64
import os
import shutil
from pathlib import Path

import pytest

from api import MsgMetadata


def test_init_aio():
    import api.aio as api
    api.init("test2.aio")
    assert api.storage == "test2.aio/"
    assert Path("test2.aio").is_dir()
    shutil.rmtree(Path("test2.aio"))


def test_init_ait():
    import api.ait as api
    api.init("test2.ait")
    assert api.storage == "test2.ait/"
    assert Path("test2.ait").is_dir()
    shutil.rmtree(Path("test2.ait"))


def test_init_sqlite():
    import api.sqlite as api
    api.init("test2.db")
    assert api.c
    assert api.con
    assert Path("test2.db").is_file()
    os.remove(Path("test2.db"))


def test_init_txt():
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
    api.remove_echoarea("test.local")
    api.remove_echoarea("test2.local")
    api.remove_echoarea("test3.local")
    api.remove_echoarea("carbonarea")
    api.remove_echoarea("favorites")
    api.remove_echoarea("idec.talks")


# noinspection PyTestParametrized
@pytest.mark.parametrize("storage", ["aio", "ait", "sqlite", "txt"])
def test_get_echo_length(api):
    assert api.get_echo_length("ring2.global") == 4
    assert api.get_echo_length("test.local") == 0


# noinspection PyTestParametrized
@pytest.mark.parametrize("storage", ["aio", "ait", "sqlite", "txt"])
def test_save_messages(api):
    assert api.get_echo_length("test.local") == 0

    msg1 = ["ii/ok", "test.local", "0", "admin", "node,1", "All", "Subj", "", "Msg1", "Row2"]
    msg2 = ["ii/ok", "test.local", "0", "admin", "node,1", "All", "Subj", "", "Msg2", "Row2"]

    api.save_message([("11", msg1), ("22", msg2)], "node", "user")
    assert api.get_echo_length("test.local") == 2
    #
    msg, size = api.read_msg("11", "test.local")
    assert msg == msg1

    msg, size = api.read_msg("22", "test.local")
    assert msg == msg2

    msgids = api.get_echo_msgids("test.local")
    assert msgids == ["11", "22"]
    assert api.get_echo_msgs_metadata("test.local") == [MsgMetadata.from_list("11", msg1),
                                                        MsgMetadata.from_list("22", msg2)]

    data = api.get_msg_list_data("test.local")
    assert data == [MsgMetadata.from_list("11", msg1),
                    MsgMetadata.from_list("22", msg2)]


# noinspection PyTestParametrized
@pytest.mark.parametrize("storage", ["aio", "ait", "sqlite", "txt"])
def test_add_to_carbonarea(api):
    assert api.get_echo_length("test.local") == 0

    msg1 = ["ii/ok", "test.local", "0", "admin", "node,1", "All", "Subj", "", "Msg1", "Row2"]
    msg2 = ["ii/ok", "test.local", "0", "admin", "node,1", "user", "Subj", "", "Msg2", "Row2"]

    api.save_message([("1" * 20, msg1), ("2" * 20, msg2)], "node", ["user"])
    assert api.get_echo_length("test.local") == 2
    assert api.get_carbonarea() == ["2" * 20]
    #
    msg, size = api.read_msg("1" * 20, "test.local")
    assert msg == msg1

    msg, size = api.read_msg("2" * 20, "carbonarea")
    assert msg == msg2

    data = api.get_msg_list_data("carbonarea")
    assert data == [MsgMetadata.from_list("2" * 20, msg2)]


# noinspection PyTestParametrized
@pytest.mark.parametrize("storage", ["aio", "ait", "sqlite", "txt"])
def test_save_favorites(api):
    assert not api.get_favorites_list()

    msg1 = ["ii/ok", "test.local", "0", "admin", "node,1", "All", "Subj", "", "Msg1", "Row2"]
    msg2 = ["ii/ok", "test.local", "0", "admin", "node,1", "user", "Subj", "", "Msg2", "Row2"]
    api.save_message([("1" * 20, msg1), ("2" * 20, msg2)], "node", ["user"])
    api.save_to_favorites("2" * 20, msg2)

    favorites = api.get_favorites_list()
    assert favorites == ["2" * 20]
    msg, size = api.read_msg("2" * 20, "favorites")
    assert msg == msg2

    data = api.get_msg_list_data("favorites")
    assert data == [MsgMetadata.from_list("2" * 20, msg2)]

    api.remove_from_favorites("2" * 20)
    assert not api.get_favorites_list()

    data = api.get_msg_list_data("favorites")
    assert data == []


# noinspection PyTestParametrized
@pytest.mark.parametrize("storage", ["aio", "ait", "sqlite", "txt"])
def test_remove_from_favorites(api):
    msg1 = ["ii/ok", "test.local", "0", "admin", "node,1", "All", "Subj", "", "Msg1", "Row2"]
    msg2 = ["ii/ok", "test.local", "0", "admin", "node,1", "user", "Subj", "", "Msg2", "Row2"]
    api.save_message([("1" * 20, msg1), ("2" * 20, msg2)], "node", ["user"])
    api.save_to_favorites("1" * 20, msg1)
    api.save_to_favorites("2" * 20, msg2)
    #
    api.remove_from_favorites("1" * 20)
    #
    favorites = api.get_favorites_list()
    assert favorites == ["2" * 20]
    msg, size = api.read_msg("2" * 20, "favorites")
    assert msg == msg2


# noinspection PyTestParametrized
@pytest.mark.parametrize("storage", ["aio", "ait", "sqlite", "txt"])
def test_non_printable(api):
    msgid = "nFaF9Z8R81USSRIE7YUF"
    msgbody = ("aWkvb2sKaWRlYy50YWxrcwoxNzI5NjA0OTcyCnJldm9sdGVj"
               "aAp0Z2ksMTUKQWxsCkZpcnN0IHRlc3QKChwVLyASGBQePwo=")
    msgbody = base64.b64decode(msgbody).decode("utf8").split("\n")
    #
    api.save_message([(msgid, msgbody)], "", "")
    #
    assert api.get_echo_length("idec.talks") == 1
    assert api.get_echo_msgids("idec.talks") == [msgid]
    assert api.get_echo_msgs_metadata("idec.talks") == [MsgMetadata.from_list(msgid, msgbody)]
    #
    msg, _ = api.read_msg(msgid, "idec.talks")
    assert msg == msgbody
    #
    api.save_to_favorites(msgid, msgbody)
    assert api.get_favorites_list() == [msgid]
    msg, _ = api.read_msg(msgid, "favorites")
    assert msg == msgbody

    data = api.get_msg_list_data("idec.talks")
    assert data == [MsgMetadata.from_list(msgid, msgbody)]


# noinspection PyTestParametrized
@pytest.mark.parametrize("storage", ["aio", "ait", "sqlite", "txt"])
def test_find_msg(api):
    msg, size = api.find_msg("unknonwnmsgid")
    assert msg == ["", "", "", "", "", "", "", "", "Сообщение отсутствует в базе"]
    assert size == 0

    msg, size = api.find_msg("25Ll1pZMnIbdWB8Ring2")
    assert msg[1] == "ring2.global"
    assert size == 81


# noinspection PyTestParametrized
@pytest.mark.parametrize("storage", ["aio", "ait", "sqlite", "txt"])
def test_node_features(api):
    features = api.get_node_features("unknown")
    assert features is None
    #
    api.save_node_features("node", ["feat1", "", "feat2"])
    features = api.get_node_features("node")
    assert features == ["feat1", "feat2"]
    #
    api.save_node_features("node", ["feat1", "feat3"])
    features = api.get_node_features("node")
    assert features == ["feat1", "feat3"]


# noinspection PyTestParametrized
@pytest.mark.parametrize("storage", ["aio", "ait", "sqlite", "txt"])
def test_node_echo_counts(api):
    ec = api.get_node_echo_counts("unknown")
    assert ec is None
    #
    api.save_node_echo_counts("node", {"echo.1": 1, "echo.2": 2})
    ec = api.get_node_echo_counts("node")
    assert ec == {"echo.1": 1, "echo.2": 2}
    #
    api.save_node_echo_counts("node", {"echo.2": 2, "echo.3": 3})
    ec = api.get_node_echo_counts("node")
    assert ec == {"echo.2": 2, "echo.3": 3}


# noinspection PyTestParametrized
@pytest.mark.parametrize("storage", ["aio", "ait", "sqlite", "txt"])
def test_find_subj_msgids(api):
    msg1 = ["ii/ok", "test.local", "0", "admin", "node,1", "All", "Subj", "", "Msg1", "Row2"]
    msg2 = ["ii/ok", "test.local", "1", "admin", "node,1", "user", "Re: Subj", "", "Msg2", "Row2"]
    msg3 = ["ii/ok", "test.local", "2", "admin", "node,1", "user", "Subj2", "", "Msg2", "Row2"]
    api.save_message([("1" * 20, msg1), ("2" * 20, msg2), ("3" * 20, msg3)], "node", ["user"])

    data = api.find_subj_msgids("test.local", "Re: Subj")
    assert data == [MsgMetadata.from_list("1" * 20, msg1),
                    MsgMetadata.from_list("2" * 20, msg2)]

    data = api.find_subj_msgids(None, "Re: Subj")
    assert data == [MsgMetadata.from_list("1" * 20, msg1),
                    MsgMetadata.from_list("2" * 20, msg2)]


# noinspection PyTestParametrized
@pytest.mark.parametrize("storage", ["aio", "ait", "sqlite", "txt"])
def test_get_msg_list_data_by_ids_n_echo(api):
    msg1 = ["ii/ok", "test.local", "0", "admin", "node,1", "All", "Subj", "", "Msg1", "Row2"]
    msg2 = ["ii/ok", "test.local", "1", "admin", "node,1", "user", "Re: Subj", "", "Msg2", "Row2"]
    msg3 = ["ii/ok", "test.local", "0", "admin", "node,1", "user", "Subj2", "", "Msg2", "Row2"]
    api.save_message([("1" * 20, msg1), ("2" * 20, msg2), ("3" * 20, msg3)], "node", ["user"])

    data = api.get_msg_list_data("test.local", ["2" * 20, "3" * 20])
    assert data == [MsgMetadata.from_list("2" * 20, msg2),
                    MsgMetadata.from_list("3" * 20, msg3)]


# noinspection PyTestParametrized
@pytest.mark.parametrize("storage", ["aio", "ait", "sqlite", "txt"])
def test_get_msg_list_data_by_ids_only(api):
    msg1 = ["ii/ok", "test2.local", "0", "admin", "node,1", "All", "Subj", "", "Msg1", "Row2"]
    msg2 = ["ii/ok", "test3.local", "1", "admin", "node,1", "user", "Re: Subj", "", "Msg2", "Row2"]
    msg3 = ["ii/ok", "test.local", "0", "admin", "node,1", "user", "Subj2", "", "Msg2", "Row2"]
    api.save_message([("1" * 20, msg1), ("2" * 20, msg2), ("3" * 20, msg3)], "node", ["user"])

    data = api.get_msg_list_data(None, ["1" * 20, "3" * 20])
    assert data == [MsgMetadata.from_list("3" * 20, msg3),  # echo test.local
                    MsgMetadata.from_list("1" * 20, msg1)]  # echo test2.local


# noinspection PyTestParametrized
@pytest.mark.parametrize("storage", ["aio", "ait", "sqlite", "txt"])
def test_find_query_msgids(api):
    msg1 = ["ii/ok", "test.local", "0", "юзер", "node,1", "All", "Сабж", "", "Msg1", "Row2"]
    msg2 = ["ii/ok", "test2.local", "1", "admin", "node,1", "юзер", "Re: Subj", "", "Мсг2", "Row2"]
    api.save_message([("1" * 20, msg1), ("2" * 20, msg2)], "node", ["user"])

    # msgid exact
    data = api.find_query_msgids("1" * 20, True, False, False, True, False, "")
    assert data == [MsgMetadata.from_list("1" * 20, msg1)]
    data = api.find_query_msgids("1" * 19, True, False, False, True, False, "")
    assert data == []
    # unicode body
    data = api.find_query_msgids("Мсг2", True, True, True, True, True, "")
    assert data == [MsgMetadata.from_list("2" * 20, msg2)]
    # unicode subj
    data = api.find_query_msgids("Сабж", True, True, True, True, True, "")
    assert data == [MsgMetadata.from_list("1" * 20, msg1)]
    # unicode from
    data = api.find_query_msgids("юзер", False, False, False, True, False, "")
    assert data == [MsgMetadata.from_list("1" * 20, msg1)]
    # unicode to
    data = api.find_query_msgids("юзер", False, False, False, False, True, "")
    assert data == [MsgMetadata.from_list("2" * 20, msg2)]
    # unicode echo only
    data = api.find_query_msgids("Row2", True, True, True, True, True, "test2.local")
    assert data == [MsgMetadata.from_list("2" * 20, msg2)]
    # empty results
    data = api.find_query_msgids("Unknown", True, True, True, True, True, "")
    assert data == []
