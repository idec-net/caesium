import re
import time
from dataclasses import dataclass
from datetime import date
from typing import Callable, Tuple


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
    def fromList(msgid, msg):
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
    dtFr: date = None
    dtTo: date = None
    msgid: bool = True
    body: bool = True
    subj: bool = True
    fr: bool = True
    to: bool = True
    echo: bool = True
    echoQuery: str = ""
    echoQueryNot: str = ""
    echoArch: str = ""  # archive or stat echoareas
    echoSkipArch: bool = True
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
        echoQuery = list(filter(None, fq.echoQuery.split(" ")))
        echoareas = list(filter(
            lambda e: any(map(lambda q: q in (e[0:-extLen] if extLen else e),
                              echoQuery)),
            echoareas))
    if fq.echo and fq.echoQueryNot:
        echoQuery = list(filter(None, fq.echoQueryNot.split(" ")))
        echoareas = list(filter(
            lambda e: all(map(lambda q: q not in (e[0:-extLen] if extLen else e),
                              echoQuery)),
            echoareas))
    if fq.echoSkipArch and fq.echoArch:
        echoArch = list(filter(None, fq.echoArch.split(" ")))
        echoareas = list(filter(
            lambda e: all(map(lambda q: q != (e[0:-extLen] if extLen else e),
                              echoArch)),
            echoareas))
    return echoareas


originTemplate = re.compile(r"^\s*\+\+\+")


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


def buildFindMatcher(query, fq: FindQuery) -> Callable[[str], int]:
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
                    orig = originTemplate.match(line)
                    if not orig:
                        return 1  # sqlite compatible result
                    res = pattern.search(s, res.end())
                return 0  # sqlite compatible result
        else:
            def _match(s: str):
                res = pattern.search(s)
                return 1 if res else 0  # sqlite compatible result
        return _match

    return match(_compilePattern(query, flags, fq.regex, fq.word))


def buildFindMatchers(fq: FindQuery) -> Tuple[Callable[[str], int],
                                              Callable[[str], int]]:
    match = None
    if fq.query:
        match = buildFindMatcher(fq.query, fq)

    matchNot = None
    if fq.queryNot:
        matchNot = buildFindMatcher(fq.queryNot, fq)

    return match, matchNot


def txtApiMatch(fq: FindQuery, match, matchNot, msgid, msg) -> bool:
    try:
        if fq.dtFr and date.fromtimestamp(int(msg[2])) < fq.dtFr:
            return False
        if fq.dtTo and date.fromtimestamp(int(msg[2])) > fq.dtTo:
            return False
    except ValueError as e:
        raise ValueError("msgid :: " + msgid) from e
    if not match and not matchNot:
        return True  # any matched
    # Skip not-matched first
    if matchNot and fq.body and matchNot("\n".join(msg[7:])):
        return False
    if matchNot and fq.subj and matchNot(msg[6]):
        return False
    if matchNot and fq.fr and matchNot(msg[3]):
        return False
    if matchNot and fq.to and matchNot(msg[5]):
        return False
    if not match:
        return True
    # Positive
    if fq.msgid and msgid == fq.query:
        return True
    if match and fq.subj and match(msg[6]):
        return True
    if match and fq.fr and match(msg[3]):
        return True
    if match and fq.to and match(msg[5]):
        return True
    if match and fq.body and match("\n".join(msg[7:])):
        return True
    #
    return False
