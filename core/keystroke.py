import curses
from typing import Tuple, Any, Union

# VisiData - keys.py
# https://github.com/saulpw/visidata/blob/develop/visidata/keys.py#L5
PRETTY_KEYS = {
    ' ': 'Space',  # must be first
    '^[': 'Alt+',
    '^J': 'Enter',
    '^M': 'Enter',
    'KEY_ENTER': 'Enter',
    '^I': 'Tab',
    'KEY_BTAB': 'Shift+Tab',
    '^@': 'Ctrl+Space',
    'KEY_UP': 'Up',
    'KEY_DOWN': 'Down',
    'KEY_LEFT': 'Left',
    'KEY_RIGHT': 'Right',
    'KEY_HOME': 'Home',
    'KEY_END': 'End',
    'KEY_EOL': 'End',
    'KEY_PPAGE': 'PgUp',
    'KEY_NPAGE': 'PgDn',

    'kUP3': 'Alt+Up',
    'kUP5': 'Ctrl+Up',
    'kUP6': 'Ctrl+Shift+Up',
    'kUP7': 'Alt+Ctrl+Up',
    'kUP': 'Shift+Up',
    'kDN3': 'Alt+Down',
    'kDN5': 'Ctrl+Down',
    'kDN6': 'Ctrl+Shift+Down',
    'kDN7': 'Alt+Ctrl+Down',
    'kDN': 'Shift+Down',
    'kLFT5': 'Ctrl+Left',
    'kRIT5': 'Ctrl+Right',
    'kHOM5': 'Ctrl+Home',
    'kEND5': 'Ctrl+End',
    'kPRV5': 'Ctrl+PgUp',
    'kNXT5': 'Ctrl+PgDn',
    'KEY_IC5': 'Ctrl+Ins',
    'KEY_DC5': 'Ctrl+Del',
    'kDC5': 'Ctrl+Del',
    'KEY_SDC': 'Shift+Del',

    'KEY_IC': 'Ins',
    'KEY_DC': 'Del',

    'KEY_SRIGHT': 'Shift+Right',
    'KEY_SR': 'Shift+Up',
    'KEY_SF3': 'Alt+Down',
    'KEY_SF5': 'Ctrl+Down',
    'KEY_SF6': 'Ctrl+Shift+Down',
    'KEY_SF7': 'Alt+Ctrl+Down',
    'KEY_SF': 'Shift+Down',
    'KEY_SLEFT': 'Shift+Left',
    'KEY_SHOME': 'Shift+Home',
    'KEY_SEND': 'Shift+End',
    'KEY_SPREVIOUS': 'Shift+PgUp',
    'KEY_SNEXT': 'Shift+PgDn',

    'kxIN': 'FocusIn',
    'kxOUT': 'FocusOut',

    'KEY_BACKSPACE': 'Bksp',
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
    d[f'KEY_F({i + 12})'] = f'Shift+F{i}'
    d[f'KEY_F({i + 24})'] = f'Ctrl+F{i}'
    d[f'KEY_F({i + 36})'] = f'Ctrl+Shift+F{i}'
    d[f'KEY_F({i + 48})'] = f'Alt+F{i}'
    d[f'KEY_F({i + 60})'] = f'Alt+Shift+F{i}'


def prettykeys(key):
    if not key or '+' in key[:-1]:
        return key

    for k, v in PRETTY_KEYS.items():
        key = key.replace(k, v)

    # replace ^ with Ctrl but not if ^ is last char
    key = key[:-1].replace('^', 'Ctrl+') + key[-1]
    return key.strip()


PENDING_KEYS = []


def getkeystroke(scr: curses.window, init_ch=-1) -> Tuple[str, int, Any]:
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

    if name == 'Alt+' and PENDING_KEYS and PENDING_KEYS[0] != curses.KEY_MOUSE:
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
    if name == 'Alt+':  # Single ^[
        name = 'ESC'
    elif name == 'Ctrl+?' and k == 127:  # for Android termux
        name = 'Bksp'
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
