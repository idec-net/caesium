import base64
import textwrap

import curses
import pytest

from core import parser, ui
from core.parser import Token, TT


def _color_pair_mock(num):
    return num


curses.color_pair = _color_pair_mock


def token_url(url, line_num, title=None, filename=None, filedata=None,
              pgp_key=None):
    return Token.URL(url, line_num,
                     url=title or url, title=title,
                     filename=filename, filedata=filedata,
                     pgp_key=pgp_key)


@pytest.mark.parametrize("ends", " .,:;!@#%&*(){}_=+\\/?")
def test_inline_ends(ends):
    assert parser.italic_inline_template.match("_italic_" + ends)
    assert parser.italic_inline_template.match("*italic*" + ends)
    assert parser.bold_inline_template.match("**bold**" + ends)
    assert parser.bold_inline_template.match("__bold__" + ends)
    assert parser.code_inline_template.match("`code`" + ends)


@pytest.mark.parametrize("ends", "aA09")
def test_not_inline_ends(ends):
    assert not parser.italic_inline_template.match("_italic_" + ends)
    assert not parser.italic_inline_template.match("*italic*" + ends)
    assert not parser.bold_inline_template.match("**bold**" + ends)
    assert not parser.bold_inline_template.match("__bold__" + ends)
    assert not parser.code_inline_template.match("`code`" + ends)


def test_ps_template():
    assert parser.ps_template.match("PS")
    assert parser.ps_template.match("PPS")
    assert parser.ps_template.match("P.P.P.S")
    assert not parser.ps_template.match("PP.P.S")
    assert parser.ps_template.match("ЗЫ")
    assert parser.ps_template.match("ЗЗЗЫ")
    assert parser.ps_template.match("З.З.З.Ы")
    assert not parser.ps_template.match("ЗЗЗ.З.Ы")
    assert not parser.ps_template.match("POST")
    assert not parser.ps_template.match("ЗЛЫ")


def test_url_template():
    match = parser.url_simple_template.match("https://ru.wikipedia.org/wiki/Вайб-кодинг")
    assert match.string[match.span()[1] - 1] == "г"

    match = parser.url_simple_template.match("https://ru.wikipedia.org/wiki/Вайб-кодинг,")
    assert match.string[match.span()[1] - 1] == "г"

    match = parser.url_simple_template.match(
        "https://wiki.archlinux.org/index.php/Ppp_(%D0%A0%D1%83%D1%81%D1%81%D0%BA%D0%B8%D0%B9)")
    assert match.string[match.span()[1] - 1] == ")"

    assert parser.url_md_template.match("[title](http://url)")
    assert parser.url_md_template.match("[qwe.qwe](ii://qwe)")
    assert not parser.url_md_template.match("title [http://url]")

    assert parser.url_gemini_template.match("=> gemini://url title")
    assert parser.url_gemini_template.match("=> gemini://url")
    assert parser.url_gemini_template.match("=>gemini://url")
    assert not parser.url_gemini_template.match("-> http://url title")


def test_filename_sanitize():
    assert parser.filename_sanitize.sub("_", "/etc/passwd") == "_etc_passwd"
    assert parser.filename_sanitize.sub("_", "../.htaccess") == "__.htaccess"


BASE_TOKENS = """Test
== Header
 * List item
 Quoter2>> Quote2
 Quoter1> Quote1
Regular text
http://url
====
Code
====
----
PS: PostScript
+++ Origin
#Comment
// Comment
"""


def test_base_tokens():
    tokens = parser.tokenize(BASE_TOKENS.splitlines())
    assert tokens[0] == Token(TT.TEXT, "Test", 0)
    assert tokens[1] == Token(TT.HEADER, "== Header", 1)
    assert tokens[2] == Token(TT.TEXT, " * List item", 2)
    assert tokens[3] == Token(TT.QUOTE2, " Quoter2>> Quote2", 3)
    assert tokens[4] == Token(TT.QUOTE1, " Quoter1> Quote1", 4)
    assert tokens[5] == Token(TT.TEXT, "Regular text", 5)
    assert tokens[6] == token_url("http://url", 6)
    assert tokens[7] == Token(TT.CODE, "====", 7)
    assert tokens[8] == Token(TT.CODE, "Code", 8)
    assert tokens[9] == Token(TT.CODE, "====", 9)
    assert tokens[10] == Token(TT.HR, "----", 10)
    assert tokens[11] == Token(TT.COMMENT, "PS: PostScript", 11)
    assert tokens[12] == Token(TT.ORIGIN, "+++ Origin", 12)
    assert tokens[13] == Token(TT.COMMENT, "#Comment", 13)
    assert tokens[14] == Token(TT.COMMENT, "// Comment", 14)
    assert len(tokens) == 15


EMPTY_LINES = """
Regular text

with empty lines
====
code

with empty lines
+++ Origin in Code
====

====
Unclosed code

"""


def test_empty_lines():
    tokens = parser.tokenize(EMPTY_LINES.splitlines())
    assert tokens[0] == Token(TT.TEXT, "", 0)
    assert tokens[1] == Token(TT.TEXT, "Regular text", 1)
    assert tokens[2] == Token(TT.TEXT, "", 2)
    assert tokens[3] == Token(TT.TEXT, "with empty lines", 3)
    assert tokens[4] == Token(TT.CODE, "====", 4)
    assert tokens[5] == Token(TT.CODE, "code", 5)
    assert tokens[6] == Token(TT.CODE, "", 6)
    assert tokens[7] == Token(TT.CODE, "with empty lines", 7)
    assert tokens[8] == Token(TT.CODE, "+++ Origin in Code", 8)
    assert tokens[9] == Token(TT.CODE, "====", 9)
    assert tokens[10] == Token(TT.TEXT, "", 10)
    assert tokens[11] == Token(TT.TEXT, "====", 11)
    assert tokens[12] == Token(TT.TEXT, "Unclosed code", 12)
    assert tokens[13] == Token(TT.TEXT, "", 13)
    assert len(tokens) == 14


URL_INLINE = """Regular text w http://inline-url in the middle.
== Header w http://header-inline-url in the middle.
 Quoter2>> Quote2 w http://quote2-inline-url in the middle.
 Quoter1> Quote1 w http://quote1-inline-url in the middle.
====
Code w http://code-inline-url in the middle.
====
----
PS: PostScript w http://ps-inline-url in the middle.
+++ Origin w http://origin-inline-url in the middle.
=> http://gem-url Url Title
"""


def test_url_inline():
    parser.INLINE_STYLE_ENABLED = False
    tokens = parser.tokenize(URL_INLINE.splitlines())
    assert tokens[0] == Token(TT.TEXT, "Regular text w ", 0)
    assert tokens[1] == token_url("http://inline-url", 0)
    assert tokens[2] == Token(TT.TEXT, " in the middle.", 0)
    assert tokens[3] == Token(TT.HEADER, "== Header w ", 1)
    assert tokens[4] == token_url("http://header-inline-url", 1)
    assert tokens[5] == Token(TT.HEADER, " in the middle.", 1)
    assert tokens[6] == Token(TT.QUOTE2, " Quoter2>> Quote2 w ", 2)
    assert tokens[7] == token_url("http://quote2-inline-url", 2)
    assert tokens[8] == Token(TT.QUOTE2, " in the middle.", 2)
    assert tokens[9] == Token(TT.QUOTE1, " Quoter1> Quote1 w ", 3)
    assert tokens[10] == token_url("http://quote1-inline-url", 3)
    assert tokens[11] == Token(TT.QUOTE1, " in the middle.", 3)
    assert tokens[12] == Token(TT.CODE, "====", 4)
    assert tokens[13] == Token(TT.CODE, "Code w ", 5)
    assert tokens[14] == token_url("http://code-inline-url", 5)
    assert tokens[15] == Token(TT.CODE, " in the middle.", 5)
    assert tokens[16] == Token(TT.CODE, "====", 6)
    assert tokens[17] == Token(TT.HR, "----", 7)
    assert tokens[18] == Token(TT.COMMENT, "PS: PostScript w ", 8)
    assert tokens[19] == token_url("http://ps-inline-url", 8)
    assert tokens[20] == Token(TT.COMMENT, " in the middle.", 8)
    assert tokens[21] == Token(TT.ORIGIN, "+++ Origin w ", 9)
    assert tokens[22] == token_url("http://origin-inline-url", 9)
    assert tokens[23] == Token(TT.ORIGIN, " in the middle.", 9)
    assert tokens[24] == Token(TT.TEXT, "=> ", 10)
    assert tokens[25] == token_url("http://gem-url", 10)
    assert tokens[26] == Token(TT.TEXT, " Url Title", 10)
    assert len(tokens) == 27


def test_url_gem_md():
    parser.INLINE_STYLE_ENABLED = True
    tokens = parser.tokenize(["Regular text w [url title](http://inline-url).",
                              "=> gemini://gem-url Url with Title"])
    assert tokens[0] == Token(TT.TEXT, "Regular text w ", 0)
    assert tokens[1] == Token(TT.URL, "[url title](http://inline-url)", 0,
                              url="http://inline-url", title="url title")
    assert tokens[2] == Token(TT.TEXT, ".", 0)
    assert tokens[3] == Token(TT.TEXT, "=> ", 1)
    assert tokens[4] == Token(TT.URL, "=> gemini://gem-url Url with Title", 1,
                              url="gemini://gem-url", title="Url with Title")
    assert len(tokens) == 5
    assert parser.prerender(tokens, width=25, height=10) == 2
    scr = ScrMock(w=25, h=10)
    # noinspection PyTypeChecker
    ui.render_body(scr, tokens, 0)
    assert tokens[0].render == ["Regular text w "]
    assert tokens[1].render == ["url title"]
    assert tokens[2].render == ["."]
    assert tokens[3].render == ["=> "]
    assert tokens[4].render == ["Url with Title"]
    text = scr.to_str()
    assert text[4:8] == ["",
                         "Regular text w url title.",
                         "=> Url with Title        ",
                         "                         "]


SOFT_WRAP = """==     long-long-long-long-header
New line with many words.

Long http://url-with-many-words/and?query.
----
"""


def test_soft_wrap():
    tokens = parser.tokenize(SOFT_WRAP.splitlines())
    assert tokens[0] == Token(TT.HEADER, "==     long-long-long-long-header", 0)
    assert tokens[1] == Token(TT.TEXT, "New line with many words.", 1)
    assert tokens[2] == Token(TT.TEXT, "", 2)
    assert tokens[3] == Token(TT.TEXT, "Long ", 3)
    assert tokens[4] == token_url("http://url-with-many-words/and?query", 3)
    assert tokens[5] == Token(TT.TEXT, ".", 3)
    assert tokens[6] == Token(TT.HR, "----", 4)

    assert parser.prerender(tokens, width=10) == 14
    assert tokens[0].render == ["==     lon",
                                "g-long-lon",
                                "g-long-hea",
                                "der"]
    assert tokens[1].render == ["New line",
                                "with many",
                                "words."]
    assert tokens[2].render == [""]
    assert tokens[3].render == ["Long "]
    # @formatter:off
    assert tokens[4].render == [     "http:",  # noqa
                                "//url-with",
                                "-many-word",
                                "s/and?quer",
                                "y"]
    # @formatter:on
    assert tokens[5].render == ["."]
    assert tokens[6].render == ["──────────"]


SOFT_WRAP_TRAILING = """http://url and text in one line.
http://url long-word in other line
"""


def test_soft_wrap_trailing():
    tokens = parser.tokenize(SOFT_WRAP_TRAILING.splitlines())
    assert tokens[0] == token_url("http://url", 0)
    assert tokens[1] == Token(TT.TEXT, " and text in one line.", 0)
    assert tokens[2] == token_url("http://url", 1)
    assert tokens[3] == Token(TT.TEXT, " long-word in other line", 1)
    #
    assert parser.prerender(tokens, width=14) == 6
    # @formatter:off
    assert tokens[0].render == ["http://url"]
    assert tokens[1].render == [          " and",  # noqa
                                "text in one",
                                "line."]
    assert tokens[2].render == ["http://url"]
    assert tokens[3].render == [          "",  # noqa
                                "long-word in",
                                "other line"]
    # @formatter:on


def test_find_visible_token():
    tokens = parser.tokenize(SOFT_WRAP.splitlines())
    parser.prerender(tokens, width=10)
    #
    y, offset = parser.find_visible_token(tokens, 0)
    assert (y, offset) == (0, 0)
    #
    y, offset = parser.find_visible_token(tokens, 1)
    assert (y, offset) == (0, 1)
    #
    y, offset = parser.find_visible_token(tokens, 3)
    assert (y, offset) == (0, 3)
    assert tokens[y].render[offset] == "der"
    #
    y, offset = parser.find_visible_token(tokens, 4)
    assert (y, offset) == (1, 0)
    assert tokens[y].render[offset] == "New line"
    #
    y, offset = parser.find_visible_token(tokens, 9)
    assert (y, offset) == (4, 1)
    assert tokens[y].render[offset] == "//url-with"


def test_scrollable_size():
    tokens = parser.tokenize([""])
    assert parser.prerender(tokens, width=10) == 1

    tokens = parser.tokenize(["", ""])
    assert parser.prerender(tokens, width=10) == 2

    tokens = parser.tokenize(SOFT_WRAP.splitlines())
    assert parser.prerender(tokens, width=10) == 14

    tokens = parser.tokenize(SOFT_WRAP_TRAILING.splitlines())
    assert parser.prerender(tokens, width=14) == 6


def test_scrollable_last_token():
    tokens = parser.tokenize(["1234 5678 9012 3456"])
    parser.prerender(tokens, width=4, height=2)
    #
    line_num = 0
    body = ""
    for t in tokens:
        if t.line_num > line_num:
            body += "\n"
            line_num = t.line_num
        body += "\n".join(t.render)
    #
    b_width = max([len(line) for line in body.split("\n")])
    assert b_width == 3


def test_render_tabs():
    tokens = parser.tokenize([
        "====",
        "\tpublic {",
        "\t\tprint;",
        "\t}",
        "===="
    ])
    b_height = parser.prerender(tokens, width=10, height=1)
    assert tokens[0].render == ["===="]
    assert tokens[1].render == ["    publi",
                                "c {"]
    assert tokens[2].render == ["        p",
                                "rint;"]
    assert tokens[3].render == ["    }"]
    assert tokens[4].render == ["===="]
    assert b_height == 7


def test_headers():
    tokens = parser.tokenize(["= Header1",
                              "== Header2",
                              "=== Header3",
                              "# Header1",
                              "## Header2",
                              "### Header3",
                              "#Just comment"])
    assert tokens[0] == Token(TT.HEADER, "= Header1", 0)
    assert tokens[1] == Token(TT.HEADER, "== Header2", 1)
    assert tokens[2] == Token(TT.HEADER, "=== Header3", 2)
    assert tokens[3] == Token(TT.HEADER, "# Header1", 3)
    assert tokens[4] == Token(TT.HEADER, "## Header2", 4)
    assert tokens[5] == Token(TT.HEADER, "### Header3", 5)
    assert tokens[6] == Token(TT.COMMENT, "#Just comment", 6)


def test_quote_url():
    tokens = parser.tokenize([">http://in-quote"])
    b_height = parser.prerender(tokens, width=20)
    assert tokens[0].render == [" >"]
    assert tokens[1].render == ["http://in-quote"]
    assert b_height == 1


def test_quote_parenthesis():
    tokens = parser.tokenize(["Quote(r)> quote"])
    parser.prerender(tokens, width=20)
    assert tokens[0].render == [" Quote(r)> quote"]


def test_url_parenthesis():
    tokens = parser.tokenize(["(http://url)"])
    assert tokens[0] == Token(TT.TEXT, "(", 0)
    assert tokens[1] == token_url("http://url", 0)
    assert tokens[2] == Token(TT.TEXT, ")", 0)
    #
    tokens = parser.tokenize(["http://url/with_(parenthesis)"])
    assert tokens[0] == token_url("http://url/with_(parenthesis)", 0)


def test_code_block2():
    tokens = parser.tokenize(["Text ```not a code",
                              "```",
                              "\ta code",
                              "```",
                              "```not a code"])
    assert tokens[0] == Token(TT.TEXT, "Text ```not a code", 0)
    assert tokens[1] == Token(TT.CODE, "```", 1)
    assert tokens[2] == Token(TT.CODE, "\ta code", 2)
    assert tokens[3] == Token(TT.CODE, "```", 3)
    assert tokens[4] == Token(TT.TEXT, "```not a code", 4)
    #
    parser.prerender(tokens, width=100)
    assert tokens[2].render[0] == "    a code"


def test_disable_inline_styles():
    parser.INLINE_STYLE_ENABLED = False
    tokens = parser.tokenize(["_italic_ **bold** `code`"])
    assert tokens[0] == Token(TT.TEXT, "_italic_ **bold** `code`", 0)


def test_code_block_wo_italic():
    parser.INLINE_STYLE_ENABLED = True
    tokens = parser.tokenize(["```",
                              "a code _not italic_",
                              "and **not bold**",
                              "```"])
    assert tokens[0] == Token(TT.CODE, "```", 0)
    assert tokens[1] == Token(TT.CODE, "a code _not italic_", 1)
    assert tokens[2] == Token(TT.CODE, "and **not bold**", 2)
    assert tokens[3] == Token(TT.CODE, "```", 3)


def test_inline_code_block():
    parser.INLINE_STYLE_ENABLED = True
    tokens = parser.tokenize(["Text `a code`, and `a code with http://url`."])
    assert tokens[0] == Token(TT.TEXT, "Text ", 0)
    assert tokens[1] == Token(TT.CODE, "a code", 0)
    assert tokens[2] == Token(TT.TEXT, ", and ", 0)
    assert tokens[3] == Token(TT.CODE, "a code with ", 0)
    assert tokens[4] == token_url("http://url", 0)
    assert tokens[5] == Token(TT.TEXT, ".", 0)


def test_inline_italic():
    parser.INLINE_STYLE_ENABLED = True
    tokens = parser.tokenize(["Text _`an italic code`_.",
                              "",
                              "/* XPM */\r",
                              "/* XPM */",
                              "static char * akspmst1_xpm[] = {"])
    assert tokens[0] == Token(TT.TEXT, "Text ", 0)
    assert tokens[1] == Token(TT.ITALIC_BEGIN, "", 0)
    assert tokens[2] == Token(TT.CODE, "an italic code", 0)
    assert tokens[3] == Token(TT.ITALIC_END, "", 0)
    assert tokens[4] == Token(TT.TEXT, ".", 0)
    assert tokens[5] == Token(TT.TEXT, "", 1)
    # Do not modify source values due to GPG signature
    assert tokens[6] == Token(TT.TEXT, "/* XPM */\r", 2)
    assert tokens[7] == Token(TT.TEXT, "/* XPM */", 3)

    parser.prerender(tokens, width=100)
    assert tokens[6].render == ["/* XPM */"]  # No \r in render

    tokens = parser.tokenize(["Text filename_with_underscore.log."])
    assert tokens[0] == Token(TT.TEXT, "Text filename_with_underscore.log.", 0)

    tokens = parser.tokenize(["*aaaaaa."])
    assert tokens[0] == Token(TT.TEXT, "*aaaaaa.", 0)


def test_inline_bold():
    parser.INLINE_STYLE_ENABLED = True
    tokens = parser.tokenize(["And some _**`bold italic code http://url`**_."])
    assert tokens[0] == Token(TT.TEXT, "And some ", 0)
    assert tokens[1] == Token(TT.ITALIC_BEGIN, "", 0)
    assert tokens[2] == Token(TT.BOLD_BEGIN, "", 0)
    assert tokens[3] == Token(TT.CODE, "bold italic code ", 0)
    assert tokens[4] == token_url("http://url", 0)
    assert tokens[5] == Token(TT.BOLD_END, "", 0)
    assert tokens[6] == Token(TT.ITALIC_END, "", 0)
    assert tokens[7] == Token(TT.TEXT, ".", 0)

    tokens = parser.tokenize(["Not**bold**."])
    assert tokens[0] == Token(TT.TEXT, "Not**bold**.", 0)

    tokens = parser.tokenize(["**bold**. without period."])
    assert tokens[0] == Token(TT.BOLD_BEGIN, "", 0)
    assert tokens[1] == Token(TT.TEXT, "bold", 0)
    assert tokens[2] == Token(TT.BOLD_END, "", 0)
    assert tokens[3] == Token(TT.TEXT, ". without period.", 0)


def test_inline_italic_quote():
    parser.INLINE_STYLE_ENABLED = True
    tokens = parser.tokenize(["> Quote w **bold** and _italic_ and `code`."])
    assert tokens[0] == Token(TT.QUOTE1, "> Quote w ", 0)
    assert tokens[1] == Token(TT.BOLD_BEGIN, "", 0)
    assert tokens[2] == Token(TT.QUOTE1, "bold", 0)
    assert tokens[3] == Token(TT.BOLD_END, "", 0)
    assert tokens[4] == Token(TT.QUOTE1, " and ", 0)
    assert tokens[5] == Token(TT.ITALIC_BEGIN, "", 0)
    assert tokens[6] == Token(TT.QUOTE1, "italic", 0)
    assert tokens[7] == Token(TT.ITALIC_END, "", 0)
    assert tokens[8] == Token(TT.QUOTE1, " and ", 0)
    assert tokens[9] == Token(TT.CODE, "code", 0)
    assert tokens[10] == Token(TT.QUOTE1, ".", 0)
    #
    parser.prerender(tokens, width=100)
    assert tokens[0].render == [" > Quote w "]  # w extra space
    assert tokens[1].render == [""]
    assert tokens[2].render == ["bold"]  # no extra space
    assert tokens[3].render == [""]
    assert tokens[4].render == [" and "]
    assert tokens[5].render == [""]
    assert tokens[6].render == ["italic"]
    assert tokens[7].render == [""]
    assert tokens[8].render == [" and "]
    assert tokens[9].render == ["code"]
    assert tokens[10].render == ["."]


def test_attachments_xpm():
    parser.INLINE_STYLE_ENABLED = True
    xpm = ["/* XPM */",
           "static char *file_xpm[] = {",
           "};"]
    tokens = parser.tokenize([*xpm,
                              "Non-XPM"])
    assert tokens[0] == token_url("file:///file.xpm (xpm, 40 B)", 0,
                                  filename="file.xpm",
                                  filedata="\n".join(xpm).encode("utf-8"))
    assert tokens[1] == Token(TT.TEXT, "Non-XPM", 3)
    assert len(tokens) == 2


def test_attachments_xpm_code():
    parser.INLINE_STYLE_ENABLED = False
    xpm = ["/* XPM */",
           "static char *file_xpm[] = {",
           "};"]
    tokens = parser.tokenize([*xpm,
                              "Non-XPM"])
    assert tokens[0] == Token(TT.CODE, "/* XPM */", 0)
    assert tokens[1] == Token(TT.CODE, "static char *file_xpm[] = {", 1)
    assert tokens[2] == Token(TT.CODE, "};", 2)
    assert tokens[3] == Token(TT.TEXT, "Non-XPM", 3)


def test_attachments_base64():
    parser.INLINE_STYLE_ENABLED = True
    text = textwrap.fill(base64.b64encode("test data".encode("utf-8"))
                         .decode("utf-8"), 5).split("\n")
    tokens = parser.tokenize(["@base64: file.png",
                              *text,  # 3 lines
                              "String w Non base64 chars ...."])
    assert tokens[0] == token_url("file:///file.png (b64, 9 B)", 0,
                                  filename="file.png",
                                  filedata="test data".encode("utf-8"))
    assert tokens[1] == Token(TT.TEXT, "String w Non base64 chars ....", 4)
    assert len(tokens) == 2


def test_attachments_base64_code():
    parser.INLINE_STYLE_ENABLED = False
    text = textwrap.fill(base64.b64encode("test data".encode("utf-8"))
                         .decode("utf-8"), 5).split("\n")
    tokens = parser.tokenize(["@base64: file.png",
                              *text,  # 3 lines
                              "String w Non base64 chars ...."])
    assert tokens[0] == Token(TT.CODE, "@base64: file.png", 0)
    assert tokens[1] == Token(TT.CODE, text[0], 1)
    assert tokens[2] == Token(TT.CODE, text[1], 2)
    assert tokens[3] == Token(TT.CODE, text[2], 3)
    assert tokens[4] == Token(TT.TEXT, "String w Non base64 chars ....", 4)


def test_attachments_base64_filename():
    parser.INLINE_STYLE_ENABLED = True
    text = textwrap.fill(base64.b64encode("test data".encode("utf-8"))
                         .decode("utf-8"), 5).split("\n")
    tokens = parser.tokenize(["@base64: /etc/passwd",
                              *text,  # 3 lines
                              "String w Non base64 chars ...."])
    assert tokens[0] == token_url("file:///_etc_passwd (b64, 9 B)", 0,
                                  filename="_etc_passwd",
                                  filedata="test data".encode("utf-8"))


def test_attachments_pgp_key_code():
    parser.INLINE_STYLE_ENABLED = False
    tokens = parser.tokenize([parser.BEGIN_PGP_KEY, "11111", parser.END_PGP_KEY])
    assert tokens[0] == Token.CODE(parser.BEGIN_PGP_KEY, 0)
    assert tokens[1] == Token.CODE("11111", 1)
    assert tokens[2] == Token.CODE(parser.END_PGP_KEY, 2)


def test_attachments_pgp_key_filename():
    parser.INLINE_STYLE_ENABLED = True
    lines = [parser.BEGIN_PGP_KEY, "11111", parser.END_PGP_KEY]
    tokens = parser.tokenize(lines)
    assert tokens[0] == token_url("file:///pgp-public-key.asc (PGP key, 77 B)", 0,
                                  filename="pgp-public-key.asc",
                                  filedata="\n".join(lines).encode("latin-1"),
                                  pgp_key=True)
    assert tokens[1] == Token.LF(0)
    assert tokens[2] == Token.CODE("Error: Invalid key", 0)


def test_attachments_pgp_key_filename_in_code_block():
    parser.INLINE_STYLE_ENABLED = True
    lines = ["====", parser.BEGIN_PGP_KEY, "11111", parser.END_PGP_KEY, "===="]
    tokens = parser.tokenize(lines)
    assert tokens[0] == Token.CODE("====", 0)
    assert tokens[1] == token_url("file:///pgp-public-key.asc (PGP key, 77 B)", 1,
                                  filename="pgp-public-key.asc",
                                  filedata="\n".join(lines[1:-1]).encode("latin-1"),
                                  pgp_key=True)
    assert tokens[2] == Token.LF(1)
    assert tokens[3] == Token.CODE("Error: Invalid key", 1)
    assert tokens[4] == Token.CODE("====", 4)


PGP_SIGNED_MSG = [parser.BEGIN_PGP_SIGNED_MSG,
                  "11111",
                  parser.BEGIN_PGP_SIGNATURE,
                  "22222",
                  parser.END_PGP_SIGNATURE]


def test_pgp_sign_code():
    parser.INLINE_STYLE_ENABLED = False
    tokens = parser.tokenize(PGP_SIGNED_MSG)
    assert tokens[0] == Token.CODE(parser.BEGIN_PGP_SIGNED_MSG, 0)
    assert tokens[1] == Token(TT.TEXT, "11111", 1)
    assert tokens[2] == Token.CODE(parser.BEGIN_PGP_SIGNATURE, 2)
    assert tokens[3] == Token.CODE("22222", 3)
    assert tokens[4] == Token.CODE(parser.END_PGP_SIGNATURE, 4)


def test_pgp_sign_inline():
    parser.INLINE_STYLE_ENABLED = True
    tokens = parser.tokenize(PGP_SIGNED_MSG)
    assert tokens[0] == Token.CODE(parser.BEGIN_PGP_SIGNED_MSG, 0)
    assert tokens[1] == Token(TT.TEXT, "11111", 1)
    assert tokens[2] == Token.CODE(parser.BEGIN_PGP_SIGNATURE, 2)
    assert tokens[3] == Token.LF(2)
    assert tokens[4] == Token.CODE("   Status: error - gpg-exit 33554433", 2)
    assert tokens[5] == Token.LF(2)
    assert tokens[6] == Token.CODE("    KeyId: --- (---)", 2)
    #
    assert tokens[11] == Token.CODE(parser.END_PGP_SIGNATURE, 4)


def test_pgp_sign_inline_in_code_block():
    parser.INLINE_STYLE_ENABLED = True
    lines = [
        "====",
        "-----BEGIN PGP SIGNED MESSAGE----- \r",
        "====\r",
        "Text",
        "- - -----BEGIN PGP PUBLIC KEY BLOCK----- \r",
        "=pQC6",
        "- - -----END PGP PUBLIC KEY BLOCK----- \r",
        "Text",
        "====",
        "-----BEGIN PGP SIGNATURE-----\r",
        "=SLkw",
        "-----END PGP SIGNATURE----- \r",
        "====",
    ]
    tokens = parser.tokenize(lines)
    assert tokens[0] == Token.CODE("====", 0)
    assert tokens[1] == Token.CODE(parser.BEGIN_PGP_SIGNED_MSG + " \r", 1)
    assert tokens[2] == Token.CODE("====\r", 2)
    assert tokens[3] == Token(TT.TEXT, "Text", 3)
    assert tokens[4] == token_url(
        "file:///pgp-public-key.asc (PGP key, 77 B)", 4,
        filename="pgp-public-key.asc",
        filedata="\n".join(["-----BEGIN PGP PUBLIC KEY BLOCK-----",
                            "=pQC6",
                            "-----END PGP PUBLIC KEY BLOCK-----"]).encode("latin-1"),
        pgp_key=True)
    assert tokens[5] == Token.LF(4)
    assert tokens[6] == Token.CODE("Error: Invalid key", 4)
    assert tokens[7] == Token(TT.TEXT, "Text", 7)
    assert tokens[8] == Token.CODE("====", 8)
    assert tokens[9] == Token.CODE(parser.BEGIN_PGP_SIGNATURE + "\r", 9)
    assert tokens[10] == Token.LF(9)
    assert tokens[11] == Token.CODE("   Status: error - gpg-exit 33554433", 9)
    #
    assert tokens[18] == Token.CODE(parser.END_PGP_SIGNATURE + " \r", 11)
    assert tokens[19] == Token.CODE("====", 12)


class ScrMock:
    def __init__(self, h, w):
        self.height = h
        self.width = w
        self.text = [["" for _ in range(w)]
                     for _ in range(h)]

    def getmaxyx(self):
        return self.height, self.width

    def to_str(self):
        return list(map(lambda line: "".join(line), self.text))

    def addstr(self, y, x, line, attr=None):
        assert attr is None or isinstance(attr, int)
        assert y < self.height
        assert x < self.width
        assert x + len(line) <= self.width
        for i, ch in enumerate(line):
            self.text[y][x + i] = ch


def test_render_token_right_border_new_line():
    tokens = parser.tokenize([
        "aaaaaa> aaa-aa aaaaa aaa aaaaaaaaaa https://aaaa.aaaaaaaa.aa/. ",
        "aaaaaa> aaaaa aaaaaaaa aaaa https://aaaaaa.com/aaaaaaaaaa/aaaaaaaaaaaa-aaa",
        "",
    ])
    parser.prerender(tokens, width=62, height=30)
    scr = ScrMock(w=62, h=30)
    # noinspection PyTypeChecker
    ui.render_body(scr, tokens, 0)
    text = scr.to_str()
    assert text[6] == ". " + " " * 60


def test_render_token_bottom_inline_overlapped():
    tokens = parser.tokenize([
        "1234567890 234 678 http://a.",
    ])
    parser.prerender(tokens, width=10, height=30)
    scr = ScrMock(8, 10)  # 8 = 5 header + 2 body + 1 status line
    # noinspection PyTypeChecker
    ui.render_body(scr, tokens, 0)
    text = scr.to_str()
    assert text[5] == "1234567890"
    assert text[6] == "234 678   "
    assert text[7] == ""  # status line


def test_render_token_new_line_at_last_space():
    tokens = parser.tokenize([
        "aaaa.aa aaaaaaaa aaaaaa aaaaa. aaaaaaaa aaa aaaaaaaaaaa a aaa: "
        "https://aaaaaa\r"])

    parser.prerender(tokens, width=62, height=30)
    scr = ScrMock(30, 62)
    # noinspection PyTypeChecker
    ui.render_body(scr, tokens, 0)
    text = scr.to_str()
    assert text[5] == "aaaa.aa aaaaaaaa aaaaaa aaaaa. aaaaaaaa aaa aaaaaaaaaaa a aaa:"
    assert text[6] == "https://aaaaaa                                                "
    assert text[7] == " " * 62


def test_find_pos_by_anchor():
    tokens = parser.tokenize(["= H 1",
                              "== 1.1. H 2",
                              "=== H 3"])
    parser.prerender(tokens, width=62)
    #
    assert parser.find_pos_by_anchor(tokens, Token.URL("", 0, "#", "Unknown")) == -1

    assert parser.find_pos_by_anchor(tokens, Token.URL("", 0, "#11-h-2")) == 1
    assert parser.find_pos_by_anchor(tokens, Token.URL("", 0, "#", " 1.1. H 2 ")) == 1

    assert parser.find_pos_by_anchor(tokens, Token.URL("", 0, "#h-3")) == 2
    assert parser.find_pos_by_anchor(tokens, Token.URL("", 0, "#", " h 3 ")) == 2
