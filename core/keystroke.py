import curses
from typing import Tuple, Any, Union

from core.cmd import Cmd, Common, Out, Reader, Selector

# VisiData - keys.py
# https://github.com/saulpw/visidata/blob/develop/visidata/keys.py#L5
PRETTY_KEYS = {
    ' ': 'SPC',  # must be first
    '^[': 'M-',
    '^J': 'RET',
    '^M': 'RET',
    'KEY_ENTER': 'RET',
    '^I': 'Tab',
    'KEY_BTAB': 'S-Tab',
    '^@': 'C-SPC',
    'KEY_UP': 'Up',
    'KEY_DOWN': 'Down',
    'KEY_LEFT': 'Left',
    'KEY_RIGHT': 'Right',
    'KEY_HOME': 'Home',
    'KEY_END': 'End',
    'KEY_EOL': 'End',
    'KEY_PPAGE': 'PgUp',
    'KEY_NPAGE': 'PgDn',

    'kUP3': 'M-Up',
    'kUP5': 'C-Up',
    'kUP6': 'C-S-Up',
    'kUP7': 'M-C-Up',
    'kUP': 'S-Up',
    'kDN3': 'M-Down',
    'kDN5': 'C-Down',
    'kDN6': 'C-S-Down',
    'kDN7': 'M-C-Down',
    'kDN': 'S-Down',
    'kLFT5': 'C-Left',
    'kRIT5': 'C-Right',
    'kHOM5': 'C-Home',
    'kEND5': 'C-End',
    'kPRV5': 'C-PgUp',
    'kNXT5': 'C-PgDn',
    'KEY_IC5': 'C-Ins',
    'KEY_DC5': 'C-Del',
    'kDC5': 'C-Del',
    'KEY_SDC': 'S-Del',

    'KEY_IC': 'Ins',
    'KEY_DC': 'Del',

    'KEY_SRIGHT': 'S-Right',
    'KEY_SR': 'S-Up',
    'KEY_SF3': 'M-Down',
    'KEY_SF5': 'C-Down',
    'KEY_SF6': 'C-S-Down',
    'KEY_SF7': 'M-C-Down',
    'KEY_SF': 'S-Down',
    'KEY_SLEFT': 'S-Left',
    'KEY_SHOME': 'S-Home',
    'KEY_SEND': 'S-End',
    'KEY_SPREVIOUS': 'S-PgUp',
    'KEY_SNEXT': 'S-PgDn',

    'kxIN': 'FocusIn',
    'kxOUT': 'FocusOut',

    'KEY_BACKSPACE': 'BS',
    'BUTTON1_RELEASED': 'LeftBtnUp',
    'BUTTON2_RELEASED': 'MiddleBtnUp',
    'BUTTON3_RELEASED': 'RightBtnUp',
    'BUTTON1_PRESSED': 'LeftClick',
    'BUTTON2_PRESSED': 'MiddleClick',
    'BUTTON3_PRESSED': 'RightClick',
    'BUTTON4_PRESSED': 'ScrollUp',
    'BUTTON5_PRESSED': 'ScrollDown',
    'REPORT_MOUSE_POSITION': 'ScrollDown',
    '2097152': 'ScrollDown',
}

for i in range(1, 13):
    d = PRETTY_KEYS
    d[f'KEY_F({i})'] = f'F{i}'
    d[f'KEY_F({i + 12})'] = f'S-F{i}'
    d[f'KEY_F({i + 24})'] = f'C-F{i}'
    d[f'KEY_F({i + 36})'] = f'C-S-F{i}'
    d[f'KEY_F({i + 48})'] = f'M-F{i}'
    d[f'KEY_F({i + 60})'] = f'M-S-F{i}'


def prettykeys(key):
    if not key or '+' in key[:-1]:
        return key

    for k, v in PRETTY_KEYS.items():
        key = key.replace(k, v)

    # replace ^ with Ctrl but not if ^ is last char
    key = key[:-1].replace('^', 'C-') + key[-1]
    if len(key) == 3 and key.startswith("C-"):
        key = key[:-1] + key[-1].lower()
    if len(key) == 1 and key.isupper():
        key = "S-" + key.lower()
    return key.strip()


PENDING_KEYS = []


class KsSeq:
    MAX_LEN = 32
    ks: str = ""  # last keystroke or keystroke sequence
    sequences = []

    @staticmethod
    def any_startswith(ks):
        return any(filter(lambda s: s.startswith(f"{KsSeq.ks} {ks}".strip()),
                          KsSeq.sequences))

    @staticmethod
    def init_sequences():
        KsSeq.sequences = []
        for group in (Common, Out, Selector, Reader):
            for attr, val in group.__dict__.items():
                if isinstance(val, Cmd) and val.ks:
                    KsSeq.sequences += [_ for _ in val.ks if " " in _]


def getkeystroke(scr: curses.window, init_ch=-1) -> Tuple[str, int, Any]:
    ks, key, _ = _getkeystroke(scr, init_ch)
    #
    if len(KsSeq.ks) < KsSeq.MAX_LEN and KsSeq.any_startswith(ks):
        KsSeq.ks = f"{KsSeq.ks} {ks}".strip()  # make keystroke sequence
    else:
        KsSeq.ks = ks  # flush current sequence
    if KsSeq.ks in KsSeq.sequences:
        return KsSeq.ks, key, _  #
    return ks, key, _  #


def _getkeystroke(scr: curses.window, init_ch=-1) -> Tuple[str, int, Any]:
    # drainPendingKeys
    if not PENDING_KEYS:
        while True:
            k = get_wch(scr, init_ch)
            if init_ch != -1:
                init_ch = -1  # reset initial ch to prevent endless loop
            if k == -1:
                break  #
            PENDING_KEYS.append(k)
            if k == curses.KEY_MOUSE:
                PENDING_KEYS.append(curses.getmouse())
        try:
            # Read out lost PRESSED/RELEASED events
            while orphan_mouse_evt := curses.getmouse():
                PENDING_KEYS.append(curses.KEY_MOUSE)
                PENDING_KEYS.append(orphan_mouse_evt)
        except curses.error:
            pass
    #
    if not PENDING_KEYS:
        return '', 0, None  #

    k = PENDING_KEYS.pop(0)
    if k == curses.KEY_MOUSE:
        mouse_evt = PENDING_KEYS.pop(0)
        return '', k, mouse_evt

    if isinstance(k, str):
        if ord(k) >= 32 and ord(k) != 127:  # 127 == DEL or ^?
            return prettykeys(k), ord(k), None
        k = ord(k)
    name = prettykeys(curses.keyname(k).decode('utf-8'))

    if name == 'M-' and PENDING_KEYS and PENDING_KEYS[0] != curses.KEY_MOUSE:
        k = PENDING_KEYS.pop(0)
        if isinstance(k, str):
            if ord(k) >= 32 and ord(k) != 127:  # 127 == DEL or ^?
                name += prettykeys(k)
                k = ord(k)
            else:
                k = ord(k)
                name += prettykeys(curses.keyname(k).decode('utf-8'))
        else:
            name += prettykeys(curses.keyname(k).decode('utf-8'))
    if name == "M-":  # Single ^[
        name = "ESC"
    elif name == "M-M-":
        name = "M-ESC"
    elif name == "C-?" and k == 127:  # for Android termux
        name = "BS"
    return name, k, None


def get_wch(scr: curses.window, init_ch=-1) -> Union[int, str]:
    # npyscreen - wgwidget._get_ch
    # https://github.com/npcole/npyscreen/blob/master/npyscreen/wgwidget.py#L475

    # For now, disable all attempt to use get_wch()
    # but everything that follows could be in the except clause above.
    # Try to read utf-8 if possible.
    _stored_bytes = []
    if init_ch == -1:
        ch = scr.getch()
    else:
        ch = init_ch
    if ch <= 193:
        return ch
    # if we are here, we need to read 1, 2 or 3 more bytes.
    # all of the subsequent bytes should be in the range 128 - 191,
    # but we'll risk not checking...
    elif 194 <= ch <= 223:
        # 2 bytes
        _stored_bytes.append(ch)
        _stored_bytes.append(scr.getch())
    elif 224 <= ch <= 239:
        # 3 bytes
        _stored_bytes.append(ch)
        _stored_bytes.append(scr.getch())
        _stored_bytes.append(scr.getch())
    elif 240 <= ch <= 244:
        # 4 bytes
        _stored_bytes.append(ch)
        _stored_bytes.append(scr.getch())
        _stored_bytes.append(scr.getch())
        _stored_bytes.append(scr.getch())
    elif ch >= 245:
        # probably a control character
        return ch

    ch = bytes(_stored_bytes).decode('utf-8', errors='strict')
    return ch
