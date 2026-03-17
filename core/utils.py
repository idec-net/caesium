import os
import platform
import subprocess
import time
from typing import List


def separate(fetch_list, step=20):  # type: (List, int) -> List
    for x in range(0, len(fetch_list), step):
        yield fetch_list[x:x + step]


def msgn_status(total, msgn, width):  # type: (int, int, int) -> str
    remains = total - msgn - 1
    if width >= 80:
        return "Сообщение %d из %d (%d осталось)" % (msgn + 1, total, remains)
    return "%d/%d [%d]" % (msgn + 1, total, remains)


def msg_strftime(msg_time_sec, width):  # type: (str, int) -> str
    if not str.isdigit(msg_time_sec):
        return ""
    msg_time_sec = time.gmtime(int(msg_time_sec))
    if width >= 80:
        return time.strftime("%d %b %Y %H:%M UTC", msg_time_sec)
    return time.strftime("%d.%m.%y %H:%M", msg_time_sec)


def msg_strfsize(size_bytes):  # type: (int) -> str
    if size_bytes < 1024:
        return str(size_bytes) + " B"
    return str(format(size_bytes / 1024, ".2f")) + " KiB"


def open_file(filepath):
    if platform.system() == "Darwin":  # macOS
        subprocess.call(("open", filepath))
    elif platform.system() == "Windows":  # windows
        os.startfile(filepath)
    elif os.getenv("TERMUX_VERSION", ""):  # android probably
        subprocess.call(("termux-open", filepath))
    else:  # linux variants
        subprocess.call(("xdg-open", filepath))


def offsets_echo_count(old, new):
    # type: (dict[str, int], dict[str, int]) -> dict[str, int]
    offsets = {}
    for echo, count in new.items():
        if echo not in old:
            offsets[echo] = 0
        elif old[echo] < count:
            offsets[echo] = old[echo]
    return offsets
