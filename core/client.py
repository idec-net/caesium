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


def _do_request(request):
    if not request.headers:
        request.headers = _headers()
    with urllib.request.urlopen(request) as f:
        data = f.read()
        if f.info().get("Content-Encoding") in ("gzip", "deflate"):
            data = zlib.decompress(data, 16 + zlib.MAX_WBITS)
    return data.decode("utf-8")


def get_bundle(url, msgids):
    req = urllib.request.Request(url + "u/m/" + msgids)
    data = _do_request(req).split("\n")
    return list(filter(None, data))


def get_msg_list(url, echoareas, offset=None, count=None):
    # type: (str, List[str], int, int) -> List[str]
    if not echoareas:
        return []
    x_filter = "/%s:%s" % (str(offset), str(count or "")) if offset else ""

    echoareas = "/".join(echoareas) + x_filter
    req = urllib.request.Request(url + "u/e/" + echoareas, method="GET")
    data = _do_request(req)
    data = data.split("\n")
    return list(filter(None, data))


def send_msg(url, auth, msg_b64):  # type: (str, str, str) -> str
    data = urllib.parse.urlencode({"tmsg": msg_b64, "pauth": auth}).encode("utf-8")
    req = urllib.request.Request(url + "u/point", data=data, method="POST")
    return _do_request(req)


def get_echo_count(url, echoareas):  # type: (str, List[str]) -> dict[str, int]
    if not echoareas:
        return {}
    echoareas = "/".join(echoareas)
    req = urllib.request.Request(url + "x/c/" + echoareas, method="GET")
    data = _do_request(req).split("\n")
    echo_counts = {it[0]: int(it[1])
                   for it in map(lambda it: it.split(":"),
                                 filter(None, data))}
    return echo_counts


def get_echo_hash(url, echoareas):  # type: (str, List[str]) -> dict[str, str]
    if not echoareas:
        return {}
    echoareas = "/".join(echoareas)
    req = urllib.request.Request(url + "x/h/" + echoareas, method="GET")
    data = _do_request(req).split("\n")
    echo_hash = {it[0]: it[1]
                 for it in map(lambda it: it.split(":"),
                               filter(None, data))}
    return echo_hash


def get_features(url):  # type: (str) -> List[str]
    req = urllib.request.Request(url + "x/features", method="GET")
    try:
        data = _do_request(req).split("\n")
    except Exception as ex:
        return ["error: " + str(ex)]
    return list(filter(None, map(lambda it: it.strip(), data)))
