import base64
import os
import re
import sys
from dataclasses import dataclass
from datetime import datetime
from enum import Enum, auto
from typing import List, Optional, Tuple

from core import utils

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

gpg = None
try:
    # gpg-agent forwarding: inappropriate ioctl for device
    # https://stackoverflow.com/a/55032706
    if os.getenv("TERMUX_VERSION", ""):  # android probably
        if os.environ.get("GPG_TTY", None) is None:
            os.environ["GPG_TTY"] = os.ttyname(sys.stdout.fileno())
    # noinspection PyUnresolvedReferences
    import gnupg
    gpg = gnupg.GPG(gnupghome=BASE_DIR + '/../.gpg')
except ImportError:
    pass

GPG_PUB_KEY_ALGS = {
    # OpenPGP Message Format :: 9.1.  Public-Key Algorithms
    # https://datatracker.ietf.org/doc/html/rfc4880#section-9.1
    '1': 'RSA (Encrypt or Sign)',
    '2': 'RSA (Encrypt-Only)',
    '3': 'RSA (Sign-Only)',
    '16': 'Elgamal (Encrypt-Only)',
    '17': 'DSA (Digital Signature Algorithm)',
    # Elliptic Curve Cryptography (ECC) in OpenPGP :: 5.  Supported Public Key Algorithms
    # https://datatracker.ietf.org/doc/html/rfc6637#section-5
    '18': 'ECDH',
    '19': 'ECDSA',
}

INLINE_STYLE_ENABLED = False
BEGIN_PGP_KEY = "-----BEGIN PGP PUBLIC KEY BLOCK-----"
END_PGP_KEY = "-----END PGP PUBLIC KEY BLOCK-----"
BEGIN_PGP_SIGNED_MSG = "-----BEGIN PGP SIGNED MESSAGE-----"
BEGIN_PGP_SIGNATURE = "-----BEGIN PGP SIGNATURE-----"
END_PGP_SIGNATURE = "-----END PGP SIGNATURE-----"

b_pgpkey_template = re.compile(r"^(- )*-----BEGIN PGP PUBLIC KEY BLOCK-----\s*")
e_pgpkey_template = re.compile(r"^(- )*-----END PGP PUBLIC KEY BLOCK-----\s*")
b_pgpmsg_template = re.compile(r"^(- )*-----BEGIN PGP SIGNED MESSAGE-----\s*")
b_pgpsign_template = re.compile(r"^(- )*-----BEGIN PGP SIGNATURE-----\s*")
e_pgpsign_template = re.compile(r"^(- )*-----END PGP SIGNATURE-----\s*")
url_simple_template = re.compile(r"((https?|ftp|file|ii|magnet|gemini):/?"
                                 r"[-A-Za-zА-Яа-яЁё0-9+&@#/%?=~_|!:,.;()]+"
                                 r"[-A-Za-zА-Яа-яЁё0-9+&@#/%=~_|()])")
url_gemini_template = re.compile(r"^=>\s*(?P<url>[^\s]+)(?P<title>\s.+)*")
url_md_template = re.compile(r"\[(?P<title>.*?)]\((?P<url>.*?)\)")
header_template = re.compile(r"^(={1,3}\s)|(#{1,3}\s)")
ps_template = re.compile(r"(^\s*)(P+S|(P\.)+S|ps|З+Ы|(З\.)+Ы|//|#)")
quote_template = re.compile(r"^\s*[a-zA-Zа-яА-Я0-9_\-.()]{0,20}>{1,20}")
origin_template = re.compile(r"^\s*\+\+\+")
echo_template = re.compile(r"^[a-z0-9_!.-]{1,60}\.[a-z0-9_!.-]{1,60}$")
code_inline_template = re.compile(r"`[^`]+`(?=$|[\s.,:;'{}@!~_*\\/\-+=&%#()?])")
bold_inline_template = re.compile(
    r"(((?<=\s)|(?<=^))__[^\s_][^_]+[^\s_]__(?=$|[\s.,:;'{}@!~_*\\/\-+=&%#()?]))"
    r"|(((?<=\s)|(?<=^))\*\*[^\s*][^*]+[^\s*]\*\*(?=$|[\s.,:;'{}@!~_*\\/\-+=&%#()?]))")
italic_inline_template = re.compile(
    r"(((?<=\s)|(?<=^))_[^\s_][^_]+[^\s_]_(?=$|[\s.,:;'{}@!~_*\\/\-+=&%#()?]))"
    r"|(((?<=\s)|(?<=^))\*[^\s*][^*]+[^\s*]\*(?=$|[\s.,:;'{}@!~_*\\/\-+=&%#()?]))")
filename_sanitize = re.compile(r"\.{2}|^[ .]|[/<>:\"\\|?*]+|[ .]$")
simple_b64 = re.compile(r"^[-A-Za-z0-9+/]*={0,3}$")


class TT(Enum):
    BOLD_BEGIN = auto()
    BOLD_END = auto()
    CODE = auto()
    COMMENT = auto()
    HEADER = auto()
    HR = auto()
    ITALIC_BEGIN = auto()
    ITALIC_END = auto()
    ORIGIN = auto()
    QUOTE1 = auto()
    QUOTE2 = auto()
    TEXT = auto()
    UNDERLINE_BEGIN = auto()
    UNDERLINE_END = auto()
    URL = auto()
    LF = auto()


@dataclass
class Token:
    type: TT
    value: str  # source text
    line_num: int  # line number (0-based)
    render: List[str] = None  # soft-wrapped value according to screen width

    url: str = None
    # markdown/gemini-like url with title
    title: str = None
    # file url with attachment
    filename: str = None
    filedata: bytes = None
    pgp_key: bool = None

    @staticmethod
    def URL(value, line_num, url, title=None, filename=None, filedata=None,
            pgp_key=None):
        return Token(TT.URL, value, line_num,
                     url=url, title=title,
                     filename=filename, filedata=filedata,
                     pgp_key=pgp_key)

    @staticmethod
    def LF(line_num):
        return Token(TT.LF, "", line_num)

    @staticmethod
    def CODE(value, line_num):
        return Token(TT.CODE, value, line_num)


def is_code_block(line):
    return line.rstrip() == "===="


def is_code_block2(line):
    return line.startswith("```")


def tokenize(lines: List[str], start_line=0, in_code_block=False, end_line=0) -> List[Token]:
    tokens = []
    line_num = start_line
    while line_num - start_line < len(lines):
        if start_line < end_line and line_num == end_line:
            return tokens  #
        line = lines[line_num - start_line]
        #
        if not in_code_block:
            if header := header_template.match(line):
                tokens.extend(_inline(line[header.end():], line_num,
                                      Token(TT.HEADER, line[0:header.end()],
                                            line_num)))
                line_num += 1
                continue  #
            #
            if comment := ps_template.search(line):
                tokens.extend(_inline(line[comment.end():], line_num,
                                      Token(TT.COMMENT, line[0:comment.end()],
                                            line_num)))
                line_num += 1
                continue  #
            #
            if quote := quote_template.match(line):
                count = line[0:quote.span()[1]].count(">")
                kind = (TT.QUOTE1, TT.QUOTE2)[(count + 1) % 2]
                tokens.extend(_inline(line[quote.end():], line_num,
                                      Token(kind, line[0:quote.end()],
                                            line_num)))
                line_num += 1
                continue  #
            #
            if origin := origin_template.search(line):
                tokens.extend(_inline(line[origin.end():], line_num,
                                      Token(TT.ORIGIN, line[0:origin.end()],
                                            line_num)))
                line_num += 1
                continue  #
            #
            if line.rstrip() == "----":
                tokens.append(Token(TT.HR, line, line_num))
                line_num += 1
                continue  #
            #
            if is_code_block(line):
                check_code_block = is_code_block
            elif is_code_block2(line):
                check_code_block = is_code_block2
            else:
                check_code_block = None
            if check_code_block:
                next_lines = lines[line_num - start_line + 1:]
                code_block_end = None
                for i, l in enumerate(next_lines):
                    if check_code_block(l):
                        code_block_end = i
                        break

                if code_block_end is not None:
                    tokens.append(Token(TT.CODE, line, line_num))
                    line_num += 1
                    in_code_block = check_code_block
                    continue  # lines
            #
            if line.rstrip() == "/* XPM */":
                next_lines = lines[line_num - start_line:]
                xpm_tokens, xpm_lines_count = _tokenize_xpm(next_lines, line_num)
                if xpm_tokens:
                    tokens.extend(xpm_tokens)
                    line_num += xpm_lines_count
                    continue  # lines
            #
            if line.rstrip().startswith("@base64:"):
                next_lines = lines[line_num - start_line:]
                b64_tokens, b64_lines_count = _tokenize_base64(next_lines, line_num)
                if b64_tokens:
                    tokens.extend(b64_tokens)
                    line_num += b64_lines_count
                    continue  # lines
        if in_code_block and in_code_block(line):
            tokens.append(Token(TT.CODE, line, line_num))
            line_num += 1
            in_code_block = False
            continue  # lines
        #
        if b_pgpkey_template.match(line):
            nesting_lvl = line.rstrip().count("- ")
            next_lines = lines[line_num - start_line:]
            end_idx = 0
            for i, nline in enumerate(next_lines):
                if (e_pgpkey_template.match(nline)
                        and nline.rstrip().count("- ") == nesting_lvl):
                    end_idx = i
                    break
            if end_idx:
                key_tokens, lines_count = _tokenize_pgp_key_block(
                    next_lines, line_num, end_idx + 1)
                if key_tokens:
                    tokens.extend(key_tokens)
                    line_num += lines_count
                    continue  # lines
        #
        if b_pgpmsg_template.match(line):
            nesting_lvl = line.rstrip().count("- ")
            next_lines = lines[line_num - start_line:]
            sign_idx = 0
            end_idx = 0
            for i, nline in enumerate(next_lines):
                if (b_pgpsign_template.match(nline)
                        and nline.rstrip().count("- ") == nesting_lvl
                        and not end_idx and not sign_idx):
                    sign_idx = i
                if (e_pgpsign_template.match(nline)
                        and nline.rstrip().count("- ") == nesting_lvl
                        and not end_idx and sign_idx):
                    end_idx = i
                    break  #

            if sign_idx and end_idx:
                sign_msg_tokens, lines_count = _tokenize_pgp_signed_msg(
                    next_lines, line_num, in_code_block, sign_idx, end_idx + 1)
                if sign_msg_tokens:
                    tokens.extend(sign_msg_tokens)
                    line_num += lines_count
                    continue  # lines
        #
        if in_code_block:
            tokens.extend(_simple_inline(line, line_num, Token.CODE("", line_num)))
        else:
            tokens.extend(_inline(line, line_num, Token(TT.TEXT, "", line_num)))
        line_num += 1

    return tokens


def _inline(text: str, line_num: int, token: Token) -> List[Token]:
    if not INLINE_STYLE_ENABLED:
        return _simple_inline(text, line_num, token)

    tokens = []
    pos = 0
    while pos < len(text):
        match_url = url_simple_template.search(text, pos)  # type: re.Match
        match_md_url = url_md_template.search(text, pos)
        match_gem_url = url_gemini_template.search(text, pos)
        match_code = code_inline_template.search(text, pos)
        match_bold = bold_inline_template.search(text, pos)
        match_italic = italic_inline_template.search(text, pos)
        match = list(filter(lambda t: t[0],
                            ((match_code, TT.CODE),
                             (match_italic, TT.ITALIC_BEGIN),
                             (match_bold, TT.BOLD_BEGIN),  # after italic
                             (match_gem_url, TT.URL),
                             (match_md_url, TT.URL),
                             (match_url, TT.URL))))  # type: List[Tuple[re.Match, TT]]
        if match:
            # find nearest matched candidate
            match = min(match, key=lambda t: t[0].start())  # type: Tuple[re.Match, TT]
        if match and match[0].start() == pos:
            sub_str = match[0].group()
            if token.value:
                tokens.append(token)
                token = Token(token.type, "", line_num)
            #
            if match[1] == TT.URL:
                pos = match[0].end()
                # TODO: Inline styles in URL titles???
                if match[0] == match_gem_url:
                    tokens.append(Token(TT.TEXT, "=> ", line_num))
                # gemini/markdown titled url
                if match[0] in (match_gem_url, match_md_url):
                    tokens.append(Token.URL(
                        text[match[0].start():match[0].end()], line_num,
                        url=match[0].group("url").strip(),
                        title=(match[0].group("title") or "").strip()))
                # simple inline url
                else:
                    if sub_str.endswith(")") and "(" not in sub_str:
                        sub_str = sub_str[0:-1]
                        pos -= 1
                    tokens.append(Token.URL(sub_str, line_num, sub_str))
            elif match[1] == TT.CODE:
                tokens.extend(_inline(sub_str[1:-1], line_num,  # `
                                      Token(TT.CODE, "", line_num)))
                pos = match[0].end()
            elif match[1] == TT.ITALIC_BEGIN:
                tokens.append(Token(TT.ITALIC_BEGIN, "", line_num))
                tokens.extend(_inline(sub_str[1:-1], line_num,  # */_
                                      Token(token.type, "", line_num)))
                tokens.append(Token(TT.ITALIC_END, "", line_num))
                pos = match[0].end()
            elif match[1] == TT.BOLD_BEGIN:
                tokens.append(Token(TT.BOLD_BEGIN, "", line_num))
                tokens.extend(_inline(sub_str[2:-2], line_num,  # **/__
                                      Token(token.type, "", line_num)))
                tokens.append(Token(TT.BOLD_END, "", line_num))
                pos = match[0].end()
        else:
            url_start = match[0].start() if match else len(text)
            raw_text = text[pos:url_start]
            token.value += raw_text
            tokens.append(token)
            pos = url_start
            token = Token(token.type, "", line_num)
    if not text:
        tokens.append(token)
    return tokens


def _simple_inline(text: str, line_num: int, token: Token) -> List[Token]:
    # with URL only
    tokens = []
    pos = 0
    while pos < len(text):
        match = url_simple_template.search(text, pos)  # type: re.Match
        if match and match.start() == pos:
            url = match.group()
            if token.value:
                tokens.append(token)
                token = Token(token.type, "", line_num)
            pos = match.end()
            if url.endswith(")") and "(" not in url:
                url = url[0:-1]
                pos -= 1
            tokens.append(Token.URL(url, line_num, url))
        else:
            url_start = match.start() if match else len(text)
            raw_text = text[pos:url_start]
            token.value += raw_text
            tokens.append(token)
            pos = url_start
            token = Token(token.type, "", line_num)
    if not text:
        tokens.append(token)
    return tokens


def _tokenize_xpm(lines, line_num):  # type: (List[str], int) -> (List[Token], int)
    if len(lines) < 2 or not lines[0].startswith("/* XPM */"):
        return [], 0  #

    # filename
    fname = re.search(r"\w+\[]", lines[1])
    if not fname:
        return [], 0  #
    fname = fname.group().rstrip("[]")
    if fname.endswith("_xpm"):
        fname = fname[0:-4] + ".xpm"
    else:
        fname = fname + ".xpm"
    fname = filename_sanitize.sub("_", fname)

    # filedata
    value = ""
    ok = False
    xpm_lines_count = 0
    for line in lines:
        value += line
        xpm_lines_count += 1
        if line.rstrip().endswith("};"):
            ok = True
            break
        value += "\n"
    if not ok:
        return [], 0  #

    if not INLINE_STYLE_ENABLED:
        return ([Token(TT.CODE, line, line_num + i)
                 for i, line in enumerate(lines[0:xpm_lines_count])],
                xpm_lines_count)

    value = value.encode("utf-8")
    size = utils.msg_strfsize(len(value))
    url = "file:///%s (xpm, %s)" % (fname, size)
    token = Token.URL(url, line_num, url=url,
                      filename=fname, filedata=value)
    return [token], xpm_lines_count


def _tokenize_base64(lines, line_num):  # type: (List[str], int) -> (List[Token], int)
    if len(lines) < 2 or not lines[0].startswith("@base64:"):
        return [], 0  #

    # filename
    fname = lines[0].split(":", maxsplit=1)[1].strip()
    if not fname:
        return [], 0  #
    fname = filename_sanitize.sub("_", fname)

    # filedata
    value = ""
    b64_lines_count = 1
    for line in lines[1:]:
        line = line.strip()
        if line and simple_b64.match(line):
            value += line + "\n"
            b64_lines_count += 1
        else:
            break  #
    if not value:
        return [], 0  #
    if not INLINE_STYLE_ENABLED:
        return ([Token(TT.CODE, line, line_num + i)
                 for i, line in enumerate(lines[0:b64_lines_count])],
                b64_lines_count)
    try:
        value_bytes = base64.b64decode(value)
    except (TypeError, ValueError):
        return ([Token(TT.CODE, line, line_num + i)
                 for i, line in enumerate(lines[0:b64_lines_count])],
                b64_lines_count)
    size = utils.msg_strfsize(len(value_bytes))

    url = "file:///%s (b64, %s)" % (fname, size)
    token = Token.URL(url, line_num, url=url,
                      filename=fname, filedata=value_bytes)
    return [token], b64_lines_count


# region _tokenize_pgp_key
def _tokenize_pgp_key_block(lines, line_num, lines_count):
    if INLINE_STYLE_ENABLED:
        key_bytes = "\n".join((BEGIN_PGP_KEY,
                               *lines[1:lines_count-1],
                               END_PGP_KEY)).encode("utf-8")
        size = utils.msg_strfsize(len(key_bytes))

        fname = "pgp-public-key.asc"
        if gpg:
            try:
                fname, key_tokens = _tokenize_pgp_key(line_num, key_bytes)
            except Exception as ex:
                key_tokens = [
                    Token.LF(line_num), Token.CODE("Error: " + str(ex), line_num)
                ]
        else:
            key_tokens = []

        url = "file:///%s (PGP key, %s)" % (fname, size)
        token = Token.URL(url, line_num, url=url,
                          filename=fname, filedata=key_bytes, pgp_key=True)
        return [token, *key_tokens], lines_count  #

    return ([Token(TT.CODE, line, line_num + i)
             for i, line in enumerate(lines[0:lines_count])],
            lines_count)  #


def _pgp_key_tokens(key, fingerprint, num):
    return [Token.LF(num),
            Token.CODE("    KeyId: %s (%s)" % (key or "---",
                                               fingerprint or "---"), num)]


def _tokenize_pgp_key(num, key_bytes):
    val = gpg.scan_keys_mem(key_bytes)
    if not val:
        raise Exception('Invalid key')
    val = val[0]
    user = val['uids'][0]
    fname = f"{user}-pgp-public-key.asc"
    fname = filename_sanitize.sub("_", fname.replace(",", "_"))
    expires = "---"
    if val['expires']:
        expires = str(datetime.utcfromtimestamp(int(val['expires'])))
    alg = GPG_PUB_KEY_ALGS.get(val['algo'], val['algo'])
    created = str(datetime.utcfromtimestamp(int(val['date'])))
    key_fp = _pgp_key_tokens(val['keyid'], val['fingerprint'], num)
    for k, _, fp, _ in val['subkeys']:
        key_fp.extend(_pgp_key_tokens(k, fp, num))
    key_tokens = [
        *key_fp,
        Token.LF(num), Token.CODE("   UserId: " + user, num),
        Token.LF(num), Token.CODE("  Created: " + created, num),
        Token.LF(num), Token.CODE("  Expires: " + expires, num),
        Token.LF(num), Token.CODE("Algorithm: " + alg, num),
        Token.LF(num), Token.CODE("     Size: " + val['length'], num),
    ]
    return fname, key_tokens
# endregion _tokenize_pgp_key


# region _tokenize_pgp_signed_msg
def _tokenize_pgp_signed_msg(lines, line_num, in_code, sign_idx, lines_count):
    msg_body = lines[1:]
    msg_body_tokens = tokenize(
        msg_body, line_num + 1, in_code, line_num + sign_idx)
    if INLINE_STYLE_ENABLED and gpg:
        sign_tokens = _tokenize_pgp_signed_msg_verify(
            lines, sign_idx, line_num + sign_idx, lines_count)
    else:
        sign_tokens = [Token(TT.CODE, line, line_num + sign_idx + i)
                       for i, line in enumerate(lines[sign_idx:lines_count])]

    tokens = [Token(TT.CODE, lines[0], line_num),
              *msg_body_tokens,
              *sign_tokens]

    return tokens, lines_count  #


def _tokenize_pgp_signed_msg_verify(lines, sign_line_idx, sign_line, lines_count):
    nesting_lvl = lines[0].rstrip().count("- ")

    def strip_nesting(line):  # type: (str) -> str
        if (b_pgpsign_template.match(line)
                or b_pgpmsg_template.match(line)
                or e_pgpsign_template.match(line)
                or b_pgpkey_template.match(line)
                or e_pgpkey_template.match(line)):
            return line[nesting_lvl * 2:]
        return line

    signed_msg = [BEGIN_PGP_SIGNED_MSG,
                  *[strip_nesting(line) for line in lines[1:sign_line_idx]],
                  BEGIN_PGP_SIGNATURE,
                  *lines[sign_line_idx + 1:lines_count-1],
                  END_PGP_SIGNATURE]
    #
    sign = gpg.verify("\n".join(signed_msg).encode("utf-8"))
    ts = "---"
    if sign.timestamp:
        ts = str(datetime.utcfromtimestamp(int(sign.timestamp)))
    sign_tokens = [
        Token.CODE(lines[sign_line_idx], sign_line),
        Token.LF(sign_line),
        Token.CODE("   Status: " + str(sign.status), sign_line),
        *_pgp_key_tokens(sign.key_id, sign.fingerprint, sign_line),
        Token.LF(sign_line),
        Token.CODE("   Signer: " + (sign.username or '---'), sign_line),
        Token.LF(sign_line),
        Token.CODE("Timestamp: " + ts, sign_line),
        Token.CODE(lines[lines_count - 1], sign_line + (lines_count - sign_line_idx) - 1),
    ]
    return sign_tokens
# endregion


def prerender(tokens, width, height=None):
    # type: (List[Token], int, Optional[int]) -> int
    """:return: body height lines count"""
    if not tokens:
        return 1  #
    line_num = tokens[0].line_num
    x = 0
    y = 0
    in_quote = False
    for token in tokens:
        if token.line_num > line_num:
            y += 1
            x = 0
            line_num = token.line_num
            in_quote = False
        if token.type == TT.LF:
            y += 1
            x = 0
            token.render = ["", ""]
            continue  # tokens
        if token.render is None:
            token.render = []
        else:
            token.render.clear()
        if height and y + 1 > height:
            # early scrollable detected, reserve scrollbar width
            return prerender(tokens, width=width - 1, height=None)
        # pre-process
        value = token.value.replace("\t", "    ").rstrip("\r")
        if token.type == TT.URL and INLINE_STYLE_ENABLED:
            value = token.title or token.url
        elif token.type in (TT.QUOTE1, TT.QUOTE2):
            if value and value[0] != " " and not in_quote:
                value = " " + value
            in_quote = True  # add space once per line
        elif token.type == TT.HR:
            value = "─" * width

        # render token
        if x + len(value) <= width:
            x += len(value)
            token.render.append(value)
            continue  # tokens
        if token.type == TT.CODE:
            # do not split leading spaces
            x = render_chunks(token, "", x, width, value)
            y += len(token.render) - 1
            continue  # tokens

        # too wide, split by words
        words = value.split(" ")
        space = ""
        line = ""
        empty_new_line = False
        for word in words:
            empty_new_line = False
            word = space + word
            space = " "
            # insert word
            if x + len(word) <= width:
                line += word
                x += len(word)
                continue  # words
            # insert chunks
            if x + 1 < width < len(word):
                x = render_chunks(token, line, x, width, word)
                line = token.render.pop(len(token.render) - 1)
                continue  # words
            # new line
            if x:
                token.render.append(line)
            if word.startswith(" "):
                word = word[1:]
            if len(word) <= width:
                line = word
                x = len(word)
                space = " "
                empty_new_line = (x == 0)
                continue  # words

            # len(word) > width
            x = render_chunks(token, "", 0, width, word)
            line = token.render.pop(len(token.render) - 1)
        if line or empty_new_line:
            token.render.append(line)
        y += len(token.render) - 1
    if height and y + 1 > height:
        # scrollable detected, reserve scrollbar width
        return prerender(tokens, width=width - 1, height=None)
    return y + 1  #


@dataclass
class RangeLines:
    start: int
    end: int


def token_line_map(tokens):
    # type: (List[Token]) -> List[RangeLines]
    # token index to line number range
    t2l = []  # type: List[RangeLines]
    #
    line_num = 0
    token_line_num = 0
    for i, t in enumerate(tokens):
        if t.line_num > token_line_num:
            token_line_num = t.line_num
            line_num += 1
        #
        t2l.append(RangeLines(line_num, line_num + len(t.render) - 1))
        line_num += len(t.render) - 1
    return t2l


def render_chunks(token, line, x, width, word):
    chunk = word[0:width - x]
    word = word[width - x:]
    while chunk:
        token.render.append(line + chunk)
        x = len(line + chunk)
        line = ""
        chunk = word[0:width]
        word = word[width:]
    return x


def find_visible_token(tokens, scroll):
    # type: (List[Token], int) -> (int, int)
    """
    :return: Token num, offset in token.render
    """
    y = 0
    line_num = 0
    if scroll < 0:
        scroll = 0
    for i, token in enumerate(tokens):
        if token.line_num > line_num:
            line_num = token.line_num
            y += 1
        height = len(token.render) - 1
        y += height
        if y >= scroll:
            return i, height - (y - scroll)  #
    #
    if not tokens:
        return 0, 0
    return len(tokens) - 1, len(tokens[-1].render) - 1


def find_pos_by_anchor(tokens, anchor):
    # type: (List[Token], Token) -> int
    y = 0
    line_num = 0
    for token in tokens:
        if token.line_num > line_num:
            line_num = token.line_num
            y += 1
        #
        if token.type == TT.HEADER and " " in token.value:
            title = token.value.split(" ", maxsplit=1)[1].strip().lower()
            if title.replace(".", "").replace(" ", "-") == anchor.url[1:]:
                return y  #
            if anchor.title and anchor.title.strip().lower() == title:
                return y  #
        #
        y += len(token.render) - 1
    return -1  #
