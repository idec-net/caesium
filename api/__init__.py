import re
import time
from dataclasses import dataclass
from typing import Callable


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


@dataclass
class FindQuery:
    DEFAULT_LIMIT = 10000
    query: str = ""
    msgid: bool = True
    body: bool = True
    subj: bool = True
    fr: bool = True
    to: bool = True
    echo: bool = True
    echo_query: str = ""
    limit: int = DEFAULT_LIMIT
    regex: bool = False
    case: bool = False
    word: bool = False
    orig: bool = False


origin_template = re.compile(r"^\s*\+\+\+")


def build_find_matcher(fq: FindQuery) -> Callable[[str], int]:
    flags = re.UNICODE
    if not fq.case:
        flags |= re.IGNORECASE
    if fq.regex:
        query = fq.query
        q = re.compile(query, flags)
    else:
        query = re.escape(fq.query)
        if fq.word:
            q = re.compile(r"(^|[\s.+-?/\\(){}]+)" + query + r"($|[\s.+-?/\\(){}]+)", flags)
        else:
            q = re.compile(query, flags)

    def match(s: str):
        res = q.search(s)
        if not res or fq.orig:
            return 1 if res else 0  # sqlite compatible result
        # skip origin
        while res:
            line = s.rfind("\n", 0, res.end())
            line = s[line if line != -1 else 0:res.end()]
            orig = origin_template.match(line)
            if not orig:
                return 1  # sqlite compatible result
            res = q.search(s, res.end())
        return 0  # sqlite compatible result

    return match
