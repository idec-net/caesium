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
HORIZONTAL_SCROLL_ENABLED = False  # do not wrap wide code-blocks and use scroll
BEGIN_PGP_KEY = "-----BEGIN PGP PUBLIC KEY BLOCK-----"
END_PGP_KEY = "-----END PGP PUBLIC KEY BLOCK-----"
BEGIN_PGP_SIGNED_MSG = "-----BEGIN PGP SIGNED MESSAGE-----"
BEGIN_PGP_SIGNATURE = "-----BEGIN PGP SIGNATURE-----"
END_PGP_SIGNATURE = "-----END PGP SIGNATURE-----"

bPgpKeyTemplate = re.compile(r"^(- )*-----BEGIN PGP PUBLIC KEY BLOCK-----\s*")
ePgpKeyTemplate = re.compile(r"^(- )*-----END PGP PUBLIC KEY BLOCK-----\s*")
bPgpMsgTemplate = re.compile(r"^(- )*-----BEGIN PGP SIGNED MESSAGE-----\s*")
bPgpSignTemplate = re.compile(r"^(- )*-----BEGIN PGP SIGNATURE-----\s*")
ePgpSignTemplate = re.compile(r"^(- )*-----END PGP SIGNATURE-----\s*")
urlSimpleTemplate = re.compile(r"((https?|ftp|file|ii|magnet|gemini):/?"
                               r"[-A-Za-zА-Яа-яЁё0-9+&@#/%?=~_|!:,.;()]+"
                               r"[-A-Za-zА-Яа-яЁё0-9+&@#/%=~_|()])")
urlGeminiTemplate = re.compile(r"^=>\s*(?P<url>[^\s]+)(?P<title>\s.+)*")
urlMdTemplate = re.compile(r"!?\[(?P<title>[^[]*?)]\((?P<url>.*?)\)")
urlMdHintTemplate = re.compile(r"\s+\".*\"")
headerTemplate = re.compile(r"^(={1,3}\s)|(#{1,3}\s)")
psTemplate = re.compile(r"(^\s*)(P+S|(P\.)+S|ps|З+Ы|(З\.)+Ы|//|#)")
quoteTemplate = re.compile(r"^\s*[a-zA-Zа-яА-Я0-9_\-.()]{0,20}>{1,20}")
originTemplate = re.compile(r"^\s*\+\+\+")
echoTemplate = re.compile(r"^[a-z0-9_!.-]{1,60}\.[a-z0-9_!.-]{1,60}$")
codeInlineTemplate = re.compile(r"`[^`]+`(?=$|[\s.,:;'{}@!~_*\\/\-+=&%#()?])")
boldInlineTemplate = re.compile(
    r"(((?<=[\s\[\]()])|(?<=^))__[^\s_]*[^_]+[^\s_]*__(?=$|[\s.,:;'{}@!~_*\\/\-+=&%#()?\[\]]))"
    r"|(((?<=[\s\[\]()])|(?<=^))\*\*[^\s*]*[^*]+[^\s*]*\*\*(?=$|[\s.,:;'{}@!~_*\\/\-+=&%#()?\[\]]))")
italicInlineTemplate = re.compile(
    r"(((?<=[\s\[\]()])|(?<=^))_[^\s_]+[^_]*[^\s_]*_(?=$|[\s.,:;'{}@!~_*\\/\-+=&%#()?\[\]]))"
    r"|(((?<=[\s\[\]()])|(?<=^))\*[^\s*]+[^*]*[^\s*]*\*(?=$|[\s.,:;'{}@!~_*\\/\-+=&%#()?\[\]]))")
filenameSanitize = re.compile(r"\.{2}|^[ .]|[/<>:\"\\|?*]+|[ .]$")
simpleB64 = re.compile(r"^[-A-Za-z0-9+/]*={0,3}$")


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
    lineNum: int  # line number (0-based)
    render: List[str] = None  # soft-wrapped value according to screen width

    url: str = None
    # markdown/gemini-like url with title
    title: str = None
    # file url with attachment
    filename: str = None
    filedata: bytes = None
    pgpKey: bool = None
    searchMatches: any = None

    @staticmethod
    def URL(value, lineNum, url, title=None, filename=None, filedata=None,
            pgpKey=None):
        return Token(TT.URL, value, lineNum,
                     url=url, title=title,
                     filename=filename, filedata=filedata,
                     pgpKey=pgpKey)

    @staticmethod
    def LF(lineNum):
        return Token(TT.LF, "", lineNum)

    @staticmethod
    def CODE(value, lineNum):
        return Token(TT.CODE, value, lineNum)


def isCodeBlock(line):
    return line.rstrip() == "===="


def isCodeBlock2(line):
    return line.startswith("```")


def tokenize(lines: List[str], startLine=0, inCodeBlock=False, endLine=0) -> List[Token]:
    tokens = []
    lineNum = startLine
    while lineNum - startLine < len(lines):
        if startLine < endLine and lineNum == endLine:
            return tokens  #
        line = lines[lineNum - startLine]
        #
        if not inCodeBlock:
            if header := headerTemplate.match(line):
                tokens.extend(_inline(line[header.end():], lineNum,
                                      Token(TT.HEADER, line[0:header.end()],
                                            lineNum)))
                lineNum += 1
                continue  #
            #
            if comment := psTemplate.search(line):
                tokens.extend(_inline(line[comment.end():], lineNum,
                                      Token(TT.COMMENT, line[0:comment.end()],
                                            lineNum)))
                lineNum += 1
                continue  #
            #
            if quote := quoteTemplate.match(line):
                count = line[0:quote.span()[1]].count(">")
                kind = (TT.QUOTE1, TT.QUOTE2)[(count + 1) % 2]
                tokens.extend(_inline(line[quote.end():], lineNum,
                                      Token(kind, line[0:quote.end()],
                                            lineNum)))
                lineNum += 1
                continue  #
            #
            if origin := originTemplate.search(line):
                tokens.extend(_inline(line[origin.end():], lineNum,
                                      Token(TT.ORIGIN, line[0:origin.end()],
                                            lineNum)))
                lineNum += 1
                continue  #
            #
            if line.rstrip() == "----":
                tokens.append(Token(TT.HR, line, lineNum))
                lineNum += 1
                continue  #
            #
            if isCodeBlock(line):
                checkCodeBlock = isCodeBlock
            elif isCodeBlock2(line):
                checkCodeBlock = isCodeBlock2
            else:
                checkCodeBlock = None
            if checkCodeBlock:
                nextLines = lines[lineNum - startLine + 1:]
                code_block_end = None
                for i, l in enumerate(nextLines):
                    if checkCodeBlock(l):
                        code_block_end = i
                        break

                if code_block_end is not None:
                    tokens.append(Token(TT.CODE, line, lineNum))
                    lineNum += 1
                    inCodeBlock = checkCodeBlock
                    continue  # lines
            #
            if line.rstrip() == "/* XPM */":
                nextLines = lines[lineNum - startLine:]
                xpm_tokens, xpm_lines_count = _tokenizeXpm(nextLines, lineNum)
                if xpm_tokens:
                    tokens.extend(xpm_tokens)
                    lineNum += xpm_lines_count
                    continue  # lines
            #
            if line.rstrip().startswith("@base64:"):
                nextLines = lines[lineNum - startLine:]
                b64_tokens, b64_lines_count = _tokenizeBase64(nextLines, lineNum)
                if b64_tokens:
                    tokens.extend(b64_tokens)
                    lineNum += b64_lines_count
                    continue  # lines
        if inCodeBlock and inCodeBlock(line):
            tokens.append(Token(TT.CODE, line, lineNum))
            lineNum += 1
            inCodeBlock = False
            continue  # lines
        #
        if bPgpKeyTemplate.match(line):
            nestingLvl = line.rstrip().count("- ")
            nextLines = lines[lineNum - startLine:]
            endIdx = 0
            for i, nline in enumerate(nextLines):
                if (ePgpKeyTemplate.match(nline)
                        and nline.rstrip().count("- ") == nestingLvl):
                    endIdx = i
                    break
            if endIdx:
                keyTokens, linesCount = _tokenizePgpKeyBlock(
                    nextLines, lineNum, endIdx + 1)
                if keyTokens:
                    tokens.extend(keyTokens)
                    lineNum += linesCount
                    continue  # lines
        #
        if bPgpMsgTemplate.match(line):
            nestingLvl = line.rstrip().count("- ")
            nextLines = lines[lineNum - startLine:]
            signIdx = 0
            endIdx = 0
            for i, nline in enumerate(nextLines):
                if (bPgpSignTemplate.match(nline)
                        and nline.rstrip().count("- ") == nestingLvl
                        and not endIdx and not signIdx):
                    signIdx = i
                if (ePgpSignTemplate.match(nline)
                        and nline.rstrip().count("- ") == nestingLvl
                        and not endIdx and signIdx):
                    endIdx = i
                    break  #

            if signIdx and endIdx:
                signMsgTokens, linesCount = _tokenizePgpSignedMsg(
                    nextLines, lineNum, inCodeBlock, signIdx, endIdx + 1)
                if signMsgTokens:
                    tokens.extend(signMsgTokens)
                    lineNum += linesCount
                    continue  # lines
        #
        if inCodeBlock:
            tokens.extend(_simpleInline(line, lineNum, Token.CODE("", lineNum)))
        else:
            tokens.extend(_inline(line, lineNum, Token(TT.TEXT, "", lineNum)))
        lineNum += 1

    return tokens


def _inline(text: str, lineNum: int, token: Token) -> List[Token]:
    if not INLINE_STYLE_ENABLED:
        return _simpleInline(text, lineNum, token)

    tokens = []
    pos = 0
    while pos < len(text):
        matchUrl = urlSimpleTemplate.search(text, pos)  # type: re.Match
        matchMdUrl = urlMdTemplate.search(text, pos)
        matchGemUrl = urlGeminiTemplate.search(text, pos)
        matchCode = codeInlineTemplate.search(text, pos)
        matchBold = boldInlineTemplate.search(text, pos)
        matchItalic = italicInlineTemplate.search(text, pos)
        match = list(filter(lambda t: t[0],
                            ((matchCode, TT.CODE),
                             (matchItalic, TT.ITALIC_BEGIN),
                             (matchBold, TT.BOLD_BEGIN),  # after italic
                             (matchGemUrl, TT.URL),
                             (matchMdUrl, TT.URL),
                             (matchUrl, TT.URL))))  # type: List[Tuple[re.Match, TT]]
        if match:
            # find nearest matched candidate
            match = min(match, key=lambda t: t[0].start())  # type: Tuple[re.Match, TT]
        if match and match[0].start() == pos:
            subStr = match[0].group()
            if token.value:
                tokens.append(token)
                token = Token(token.type, "", lineNum)
            #
            if match[1] == TT.URL:
                pos = match[0].end()
                # TODO: Inline styles in URL titles???
                if match[0] == matchGemUrl:
                    tokens.append(Token(TT.TEXT, "=> ", lineNum))
                # gemini url
                if match[0] == matchGemUrl:
                    tokens.append(Token.URL(
                        text[match[0].start():match[0].end()], lineNum,
                        url=match[0].group("url").strip(),
                        title=(match[0].group("title") or "").strip()))
                # markdown titled url
                elif match[0] == matchMdUrl:
                    url = match[0].group("url").strip()
                    hint = urlMdHintTemplate.search(url)
                    if hint:
                        start, end = hint.regs[0]
                        hint = url[start:end].strip()[1:-1]
                        url = url[0:start].strip()
                    tokens.append(Token.URL(
                        text[match[0].start():match[0].end()], lineNum,
                        url=url,
                        title=(match[0].group("title") or hint or "").strip()))
                # simple inline url
                else:
                    if subStr.endswith(")") and "(" not in subStr:
                        subStr = subStr[0:-1]
                        pos -= 1
                    tokens.append(Token.URL(subStr, lineNum, subStr))
            elif match[1] == TT.CODE:
                tokens.extend(_inline(subStr[1:-1], lineNum,  # `
                                      Token(TT.CODE, "", lineNum)))
                pos = match[0].end()
            elif match[1] == TT.ITALIC_BEGIN:
                tokens.append(Token(TT.ITALIC_BEGIN, "", lineNum))
                tokens.extend(_inline(subStr[1:-1], lineNum,  # */_
                                      Token(token.type, "", lineNum)))
                tokens.append(Token(TT.ITALIC_END, "", lineNum))
                pos = match[0].end()
            elif match[1] == TT.BOLD_BEGIN:
                tokens.append(Token(TT.BOLD_BEGIN, "", lineNum))
                tokens.extend(_inline(subStr[2:-2], lineNum,  # **/__
                                      Token(token.type, "", lineNum)))
                tokens.append(Token(TT.BOLD_END, "", lineNum))
                pos = match[0].end()
        else:
            urlStart = match[0].start() if match else len(text)
            raw_text = text[pos:urlStart]
            token.value += raw_text
            tokens.append(token)
            pos = urlStart
            token = Token(token.type, "", lineNum)
    if not text:
        tokens.append(token)
    return tokens


def _simpleInline(text: str, line_num: int, token: Token) -> List[Token]:
    # with URL only
    tokens = []
    pos = 0
    while pos < len(text):
        match = urlSimpleTemplate.search(text, pos)  # type: re.Match
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
            urlStart = match.start() if match else len(text)
            rawText = text[pos:urlStart]
            token.value += rawText
            tokens.append(token)
            pos = urlStart
            token = Token(token.type, "", line_num)
    if not text:
        tokens.append(token)
    return tokens


def _tokenizeXpm(lines, line_num):  # type: (List[str], int) -> (List[Token], int)
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
    fname = filenameSanitize.sub("_", fname)

    # filedata
    value = ""
    ok = False
    xpmLinesCount = 0
    for line in lines:
        value += line
        xpmLinesCount += 1
        if line.rstrip().endswith("};"):
            ok = True
            break
        value += "\n"
    if not ok:
        return [], 0  #

    if not INLINE_STYLE_ENABLED:
        return ([Token(TT.CODE, line, line_num + i)
                 for i, line in enumerate(lines[0:xpmLinesCount])],
                xpmLinesCount)

    value = value.encode("utf-8")
    size = utils.msgStrfsize(len(value))
    url = "file:///%s (xpm, %s)" % (fname, size)
    token = Token.URL(url, line_num, url=url,
                      filename=fname, filedata=value)
    return [token], xpmLinesCount


def _tokenizeBase64(lines, line_num):  # type: (List[str], int) -> (List[Token], int)
    if len(lines) < 2 or not lines[0].startswith("@base64:"):
        return [], 0  #

    # filename
    fname = lines[0].split(":", maxsplit=1)[1].strip()
    if not fname:
        return [], 0  #
    fname = filenameSanitize.sub("_", fname)

    # filedata
    value = ""
    b64LinesCount = 1
    for line in lines[1:]:
        line = line.strip()
        if line and simpleB64.match(line):
            value += line + "\n"
            b64LinesCount += 1
        else:
            break  #
    if not value:
        return [], 0  #
    if not INLINE_STYLE_ENABLED:
        return ([Token(TT.CODE, line, line_num + i)
                 for i, line in enumerate(lines[0:b64LinesCount])],
                b64LinesCount)
    try:
        value_bytes = base64.b64decode(value)
    except (TypeError, ValueError):
        return ([Token(TT.CODE, line, line_num + i)
                 for i, line in enumerate(lines[0:b64LinesCount])],
                b64LinesCount)
    size = utils.msgStrfsize(len(value_bytes))

    url = "file:///%s (b64, %s)" % (fname, size)
    token = Token.URL(url, line_num, url=url,
                      filename=fname, filedata=value_bytes)
    return [token], b64LinesCount


# region _tokenizePgpKey
def _tokenizePgpKeyBlock(lines, line_num, lines_count):
    if INLINE_STYLE_ENABLED:
        keyBytes = "\n".join((BEGIN_PGP_KEY,
                              *lines[1:lines_count - 1],
                              END_PGP_KEY)).encode("utf-8")
        size = utils.msgStrfsize(len(keyBytes))

        fname = "pgp-public-key.asc"
        if gpg:
            try:
                fname, keyTokens = _tokenizePgpKey(line_num, keyBytes)
            except Exception as ex:
                keyTokens = [
                    Token.LF(line_num), Token.CODE("Error: " + str(ex), line_num)
                ]
        else:
            keyTokens = []

        url = "file:///%s (PGP key, %s)" % (fname, size)
        token = Token.URL(url, line_num, url=url,
                          filename=fname, filedata=keyBytes, pgpKey=True)
        return [token, *keyTokens], lines_count  #

    return ([Token(TT.CODE, line, line_num + i)
             for i, line in enumerate(lines[0:lines_count])],
            lines_count)  #


def _pgpKeyTokens(key, fingerprint, num):
    return [Token.LF(num),
            Token.CODE("    KeyId: %s (%s)" % (key or "---",
                                               fingerprint or "---"), num)]


def _tokenizePgpKey(num, key_bytes):
    val = gpg.scan_keys_mem(key_bytes)
    if not val:
        raise Exception('Invalid key')
    val = val[0]
    user = val['uids'][0]
    fname = f"{user}-pgp-public-key.asc"
    fname = filenameSanitize.sub("_", fname.replace(",", "_"))
    expires = "---"
    if val['expires']:
        expires = str(datetime.utcfromtimestamp(int(val['expires'])))
    alg = GPG_PUB_KEY_ALGS.get(val['algo'], val['algo'])
    created = str(datetime.utcfromtimestamp(int(val['date'])))
    key_fp = _pgpKeyTokens(val['keyid'], val['fingerprint'], num)
    for k, _, fp, _ in val['subkeys']:
        key_fp.extend(_pgpKeyTokens(k, fp, num))
    keyTokens = [
        *key_fp,
        Token.LF(num), Token.CODE("   UserId: " + user, num),
        Token.LF(num), Token.CODE("  Created: " + created, num),
        Token.LF(num), Token.CODE("  Expires: " + expires, num),
        Token.LF(num), Token.CODE("Algorithm: " + alg, num),
        Token.LF(num), Token.CODE("     Size: " + val['length'], num),
    ]
    return fname, keyTokens
# endregion _tokenizePgpKey


# region _tokenizePgpSignedMsg
def _tokenizePgpSignedMsg(lines, lineNum, inCode, signIdx, linesCount):
    msgBody = lines[1:]
    msgBodyTokens = tokenize(
        msgBody, lineNum + 1, inCode, lineNum + signIdx)
    if INLINE_STYLE_ENABLED and gpg:
        signTokens = _tokenizePgpSignedMsgVerify(
            lines, signIdx, lineNum + signIdx, linesCount)
    else:
        signTokens = [Token(TT.CODE, line, lineNum + signIdx + i)
                      for i, line in enumerate(lines[signIdx:linesCount])]

    tokens = [Token(TT.CODE, lines[0], lineNum),
              *msgBodyTokens,
              *signTokens]

    return tokens, linesCount  #


def _tokenizePgpSignedMsgVerify(lines, signLineIdx, signLine, linesCount):
    nestingLvl = lines[0].rstrip().count("- ")

    def strip_nesting(line):  # type: (str) -> str
        if (bPgpSignTemplate.match(line)
                or bPgpMsgTemplate.match(line)
                or ePgpSignTemplate.match(line)
                or bPgpKeyTemplate.match(line)
                or ePgpKeyTemplate.match(line)):
            return line[nestingLvl * 2:]
        return line

    signed_msg = [BEGIN_PGP_SIGNED_MSG,
                  *[strip_nesting(line) for line in lines[1:signLineIdx]],
                  BEGIN_PGP_SIGNATURE,
                  *lines[signLineIdx + 1:linesCount - 1],
                  END_PGP_SIGNATURE]
    #
    sign = gpg.verify("\n".join(signed_msg).encode("utf-8"))
    ts = "---"
    if sign.timestamp:
        ts = str(datetime.utcfromtimestamp(int(sign.timestamp)))
    sign_tokens = [
        Token.CODE(lines[signLineIdx], signLine),
        Token.LF(signLine),
        Token.CODE("   Status: " + str(sign.status), signLine),
        *_pgpKeyTokens(sign.key_id, sign.fingerprint, signLine),
        Token.LF(signLine),
        Token.CODE("   Signer: " + (sign.username or '---'), signLine),
        Token.LF(signLine),
        Token.CODE("Timestamp: " + ts, signLine),
        Token.CODE(lines[linesCount - 1], signLine + (linesCount - signLineIdx) - 1),
    ]
    return sign_tokens
# endregion _tokenizePgpSignedMsg


def prerender(tokens, width, height=None, reserveHScroll=True, hScroll=False, maxWidth=0):
    # type: (List[Token], int, Optional[int], bool, bool, int) -> Tuple[int, int, int]
    """:return: body height lines count, max width, hScroll"""
    if not tokens:
        return 1, width, hScroll  #
    lineNum = tokens[0].lineNum
    x = 0
    y = 0
    maxWidth = maxWidth or width
    inQuote = False
    for token in tokens:
        if token.lineNum > lineNum:
            y += 1
            x = 0
            lineNum = token.lineNum
            inQuote = False
        if token.type == TT.LF:
            y += 1
            x = 0
            token.render = ["", ""]
            continue  # tokens
        if token.render is None:
            token.render = []
        else:
            token.render.clear()
        # pre-process
        value = token.value.replace("\t", "    ").rstrip("\r")
        if token.type == TT.URL and INLINE_STYLE_ENABLED:
            value = token.title or token.url
        elif token.type in (TT.QUOTE1, TT.QUOTE2):
            if value and value[0] != " " and not inQuote:
                value = " " + value
            inQuote = True  # add space once per line
        elif token.type == TT.HR:
            value = "─" * width

        # render token
        if x + len(value) <= width:
            x += len(value)
            token.render.append(value)
            continue  # tokens
        if token.type == TT.CODE:
            if HORIZONTAL_SCROLL_ENABLED and x == 0:
                token.render.append(value)
                maxWidth = max(maxWidth, len(value))
                continue  # tokens
            # do not split leading spaces
            x = renderChunks(token, "", x, width, value)
            y += len(token.render) - 1
            continue  # tokens

        # too wide, split by words
        words = value.split(" ")
        space = ""
        line = ""
        emptyNewLine = False
        for word in words:
            emptyNewLine = False
            word = space + word
            space = " "
            # insert word
            if x + len(word) <= width:
                line += word
                x += len(word)
                continue  # words
            # insert chunks
            if x + 1 < width < len(word):
                x = renderChunks(token, line, x, width, word)
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
                emptyNewLine = (x == 0)
                continue  # words

            # len(word) > width
            x = renderChunks(token, "", 0, width, word)
            line = token.render.pop(len(token.render) - 1)
        if line or emptyNewLine:
            token.render.append(line)
        y += len(token.render) - 1
    if HORIZONTAL_SCROLL_ENABLED and reserveHScroll and maxWidth > width:
        if height:
            height -= 1
        # reserve scrollbar height
        return prerender(tokens, width=width, height=height,
                         reserveHScroll=False, hScroll=True,
                         maxWidth=maxWidth)
    if height and y + 1 > height:
        # reserve scrollbar width
        return prerender(tokens, width=width - 1, height=None,
                         reserveHScroll=reserveHScroll, hScroll=hScroll,
                         maxWidth=maxWidth - 1)
    return y + 1, maxWidth, hScroll  #


@dataclass
class RangeLines:
    start: int
    end: int


def tokenLineMap(tokens):
    # type: (List[Token]) -> List[RangeLines]
    # token index to line number range
    t2l = []  # type: List[RangeLines]
    #
    lineNum = 0
    tokenLineNum = 0
    for i, t in enumerate(tokens):
        if t.lineNum > tokenLineNum:
            tokenLineNum = t.lineNum
            lineNum += 1
        #
        t2l.append(RangeLines(lineNum, lineNum + len(t.render) - 1))
        lineNum += len(t.render) - 1
    return t2l


def renderChunks(token, line, x, width, word):
    chunk = word[0:width - x]
    word = word[width - x:]
    while chunk:
        token.render.append(line + chunk)
        x = len(line + chunk)
        line = ""
        chunk = word[0:width]
        word = word[width:]
    return x


def findVisibleToken(tokens, scroll):
    # type: (List[Token], int) -> (int, int)
    """
    :return: Token num, offset in token.render
    """
    y = 0
    lineNum = 0
    if scroll < 0:
        scroll = 0
    for i, token in enumerate(tokens):
        if token.lineNum > lineNum:
            lineNum = token.lineNum
            y += 1
        height = len(token.render) - 1
        y += height
        if y >= scroll:
            return i, height - (y - scroll)  #
    #
    if not tokens:
        return 0, 0
    return len(tokens) - 1, len(tokens[-1].render) - 1


def findAnchorPos(tokens, anchor):
    # type: (List[Token], Token) -> int
    y = 0
    lineNum = 0
    for token in tokens:
        if token.lineNum > lineNum:
            lineNum = token.lineNum
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
