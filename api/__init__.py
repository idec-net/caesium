import time
from dataclasses import dataclass


@dataclass
class MsgMetadata:
    msgid: str
    tags: str
    echo: str
    time: int
    fr: str
    addr: str
    to: str
    subj: str

    _strtime: str = None

    def strtime(self):
        if not self._strtime:
            self._strtime = time.strftime("%Y.%m.%d", time.gmtime(self.time))
        return self._strtime

    @staticmethod
    def from_list(msgid, msg):
        return MsgMetadata(msgid=msgid,
                           tags=msg[0],
                           echo=msg[1],
                           time=int(msg[2]),
                           fr=msg[3],
                           addr=msg[4],
                           to=msg[5],
                           subj=msg[6])
