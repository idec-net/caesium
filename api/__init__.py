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
    queryNot: str = ""
    msgid: bool = True
    body: bool = True
    subj: bool = True
    fr: bool = True
    to: bool = True
    echo: bool = True
    echoQuery: str = ""
    echoQueryNot: str = ""
    limit: int = DEFAULT_LIMIT
    regex: bool = False
    case: bool = False
    word: bool = False
    orig: bool = False

    def __repr__(self):
        if self.query and self.queryNot:
            return self.query + " AND NOT " + self.queryNot
        elif self.queryNot:
            return "NOT " + self.queryNot
        return self.query


def filterEchoarea(fq: FindQuery, echoareas, extLen):
    if fq.echo and fq.echoQuery:
        echoQuery = fq.echoQuery.split(" ")
        echoareas = list(filter(
            lambda e: any(map(lambda q: q in (e[0:-extLen] if extLen else e),
                              echoQuery)),
            echoareas))
    if fq.echo and fq.echoQueryNot:
        echoQuery = fq.echoQueryNot.split(" ")
        echoareas = list(filter(
            lambda e: all(map(lambda q: q not in (e[0:-extLen] if extLen else e),
                              echoQuery)),
            echoareas))
    return echoareas


origin_template = re.compile(r"^\s*\+\+\+")


def _compilePattern(query, flags, regex, word):
    if regex:
        p = re.compile(query, flags)
    else:
        query = re.escape(query)
        if word:
            p = re.compile(r"(^|[\s.+-?/\\(){}]+)" + query + r"($|[\s.+-?/\\(){}]+)", flags)
        else:
            p = re.compile(query, flags)
    return p


def build_find_matcher(fq: FindQuery) -> Callable[[str], int]:
    flags = re.UNICODE
    if not fq.case:
        flags |= re.IGNORECASE

    def match(pattern):
        if not fq.orig:
            def _match(s):
                res = pattern.search(s)
                # skip origin
                while res:
                    line = s.rfind("\n", 0, res.end())
                    line = s[line if line != -1 else 0:res.end()]
                    orig = origin_template.match(line)
                    if not orig:
                        return 1  # sqlite compatible result
                    res = pattern.search(s, res.end())
                return 0  # sqlite compatible result
        else:
            def _match(s: str):
                res = pattern.search(s)
                return 1 if res else 0  # sqlite compatible result
        return _match
    #
    mp = None
    mpNot = None
    if fq.query:
        mp = match(_compilePattern(fq.query, flags, fq.regex, fq.word))

    if fq.queryNot:
        mpNot = match(_compilePattern(fq.queryNot, flags, fq.regex, fq.word))

    def matcher(s):
        return ((mp(s) if mp else True)
                and ((not mpNot(s)) if mpNot else True))

    return matcher
