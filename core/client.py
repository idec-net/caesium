# coding=utf-8
import urllib.parse
import urllib.request
import zlib
from typing import List

from core import __version__

USER_AGENT = "Caesium/" + __version__


def _headers():
    return {"User-Agent": USER_AGENT,
            "Accept-Encoding": "gzip,deflate",
            "Connection": "close"}


def _doRequest(request):
    if not request.headers:
        request.headers = _headers()
    with urllib.request.urlopen(request) as f:
        data = f.read()
        if f.info().get("Content-Encoding") in ("gzip", "deflate"):
            data = zlib.decompress(data, 16 + zlib.MAX_WBITS)
    return data.decode("utf-8")


def getBundle(url, msgids):
    req = urllib.request.Request(url + "u/m/" + msgids)
    data = _doRequest(req).split("\n")
    return list(filter(None, data))


def getMsgList(url, echoareas, offset=None, count=65535):
    # type: (str, List[str], int, int) -> List[str]
    if not echoareas:
        return []
    x_filter = "/%s:%s" % (str(offset), str(count)) if offset else ""

    echoareas = "/".join(echoareas) + x_filter
    req = urllib.request.Request(url + "u/e/" + echoareas, method="GET")
    data = _doRequest(req)
    data = data.split("\n")
    return list(filter(None, data))


def sendMsg(url, auth, msg_b64):  # type: (str, str, str) -> str
    data = urllib.parse.urlencode({"tmsg": msg_b64, "pauth": auth}).encode("utf-8")
    req = urllib.request.Request(url + "u/point", data=data, method="POST")
    return _doRequest(req)


def getEchoCount(url, echoareas):  # type: (str, List[str]) -> dict[str, int]
    if not echoareas:
        return {}
    echoareas = "/".join(echoareas)
    req = urllib.request.Request(url + "x/c/" + echoareas, method="GET")
    data = _doRequest(req).split("\n")
    echoCounts = {it[0]: int(it[1])
                  for it in map(lambda it: it.split(":"),
                                filter(None, data))}
    return echoCounts


def getEchoHash(url, echoareas):  # type: (str, List[str]) -> dict[str, str]
    if not echoareas:
        return {}
    echoareas = "/".join(echoareas)
    req = urllib.request.Request(url + "x/h/" + echoareas, method="GET")
    data = _doRequest(req).split("\n")
    echoHash = {it[0]: it[1]
                for it in map(lambda it: it.split(":"),
                              filter(None, data))}
    return echoHash


def getFeatures(url):  # type: (str) -> List[str]
    req = urllib.request.Request(url + "x/features", method="GET")
    try:
        data = _doRequest(req).split("\n")
    except Exception as ex:
        return ["error: " + str(ex)]
    return list(filter(None, map(lambda it: it.strip(), data)))
