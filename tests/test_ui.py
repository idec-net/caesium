from api import MsgMetadata
from core.ui import MsgModeStack, ReaderMode


def msg(msgid):
    return MsgMetadata(msgid, "", "", 0, "", "", "", "")


def test_push_pop():
    msgs = MsgModeStack(ReaderMode.ECHO, [], -1)
    assert not msgs.stack
    assert msgs.mode == ReaderMode.ECHO
    assert msgs.data == []
    assert msgs.msgn == -1

    # re-write current mode
    msgs.push(ReaderMode.ECHO, [msg("0")])
    assert not msgs.stack
    assert msgs.mode == ReaderMode.ECHO
    assert msgs.data == [msg("0")]
    assert msgs.msgn == -1

    # push on new mode only
    msgs.msgn = 0
    msgs.push(ReaderMode.SUBJ, [msg("1"), msg("0")])
    assert msgs.stack == [(ReaderMode.ECHO, [msg("0")], 0)]
    assert msgs.mode == ReaderMode.SUBJ
    assert msgs.data == [msg("1"), msg("0")]
    assert msgs.msgn == 1

    msgs.pop()
    assert not msgs.stack
    assert msgs.mode == ReaderMode.ECHO
    assert msgs.data == [msg("0")]
    assert msgs.msgn == 0


def test_modeSubj():
    msgs = MsgModeStack(ReaderMode.ECHO, [msg("0")], 0)
    #
    msgs.modeSubjOn([msg("1"), msg("0")])
    assert msgs.stack == [(ReaderMode.ECHO, [msg("0")], 0)]
    assert msgs.mode == ReaderMode.SUBJ
    assert msgs.data == [msg("1"), msg("0")]
    assert msgs.msgn == 1
    #
    msgs.modeSubjOn([msg("2"), msg("1"), msg("0")])
    assert msgs.stack == [(ReaderMode.ECHO, [msg("0")], 0)]
    assert msgs.mode == ReaderMode.SUBJ
    assert msgs.data == [msg("2"), msg("1"), msg("0")]
    assert msgs.msgn == 2
    #
    msgs.modeSubjOff()
    assert not msgs.stack
    assert msgs.mode == ReaderMode.ECHO
    assert msgs.data == [msg("0")]
    assert msgs.msgn == 0


def test_modeSubj_differMsgid():
    msgs = MsgModeStack(ReaderMode.ECHO, [msg("0"), msg("1")], 1)
    #
    msgs.modeSubjOn([msg("1"), msg("01"), msg("001"), msg("0001")])
    assert msgs.stack == [(ReaderMode.ECHO, [msg("0"), msg("1")], 1)]
    assert msgs.mode == ReaderMode.SUBJ
    assert msgs.data == [msg("1"), msg("01"), msg("001"), msg("0001")]
    assert msgs.msgn == 0
    #
    msgs.msgn = 3  # 0001
    msgs.pop()
    assert not msgs.stack
    assert msgs.mode == ReaderMode.ECHO
    assert msgs.data == [msg("0"), msg("1")]
    assert msgs.msgn == 1  # no 0001 msg, restore firstly selected


def test_modeQs():
    msgs = MsgModeStack(ReaderMode.ECHO, [msg("0"), msg("1")], 1)
    #
    msgs.modeQsOn([1])
    assert msgs.stack == [(ReaderMode.ECHO, [msg("0"), msg("1")], 1)]
    assert msgs.mode == ReaderMode.SEARCH
    assert msgs.data == [msg("1")]
    assert msgs.msgn == 0
    #
    msgs.modeSubjOn([msg("10"), msg("11"), msg("1")])
    assert msgs.stack == [(ReaderMode.ECHO, [msg("0"), msg("1")], 1),
                          (ReaderMode.SEARCH, [msg("1")], 0)]
    assert msgs.mode == ReaderMode.SUBJ
    assert msgs.data == [msg("10"), msg("11"), msg("1")]
    assert msgs.msgn == 2
    #
    msgs.pop()
    msgs.pop()
    msgs.pop()
    #
    assert not msgs.stack
    assert msgs.mode == ReaderMode.ECHO
    assert msgs.data == [msg("0"), msg("1")]
    assert msgs.msgn == 1
