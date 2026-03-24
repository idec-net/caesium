from core.cmd import Common as c
from core.cmd import Out as o
from core.cmd import Reader as r
from core.cmd import Selector as s
from core.cmd import Qs as qs

# Keep in mind a terminal can't handle some combinations.
# Use `show_key.py` tool to check how Caesium translates some key combinations
# to keystroke.
# In general, modifier order is `M-` `C-` `S-`.
#
# Fix Keyboard Input on Terminals - Please
# https://www.leonerd.org.uk/hacks/fixterms/
#
# XTerm Control Sequences - VT100 Mode - Single-character functions
# https://invisible-island.net/xterm/ctlseqs/ctlseqs.html#h2-VT100-Mode

# @formatter:off
c.QUIT.ks = ["F10", "q", "S-q"]  # закрыть клиент

# Клавиши для экрана выбора эхоконференции
s.UP.ks =      ["Up", "k"]  # noqa: E222  курсор вверх
s.DOWN.ks =    ["Down", "j"]  # noqa: E222  курсор вниз
s.PPAGE.ks =   ["PgUp", "S-k"]  # noqa: E222  страница вверх
s.NPAGE.ks =   ["PgDn", "S-j"]  # noqa: E222  страница вниз
s.HOME.ks =    ["Home", "S-h"]  # noqa: E222  в начало
s.END.ks =     ["End", "S-l"]  # noqa: E222  в конец
s.GET.ks =     ["g", "S-g"]  # noqa: E222  получить сообщения (свежие по счётчику)
s.FGET.ks =    ["C-g"]  # noqa: E222  получить сообщения (полный индекс)
s.ARCHIVE.ks = ["Tab", "t"]   # noqa: E222  переключение в архив и обратно
s.ENTER.ks =   ["RET", "Right", "SPC", "l"]  # noqa: E222  открыть эху
s.OUT.ks =     ["o", "S-o"]  # noqa: E222  исходящие сообщения
s.DRAFTS.ks =  ["d", "S-d"]  # noqa: E222  черновики
s.NNODE.ks =   ["."]  # noqa: E222  следующая нода
s.PNODE.ks =   [","]  # noqa: E222  предыдущая нода
s.CONFIG.ks =  ["e", "S-e"]  # noqa: E222  редактировать конфиг
s.FIND.ks =    ["y", "S-y"]  # noqa: E222  открыть окно поиска по БД

# Клавиши для экрана чтения
r.PREV.ks =      ["Left", "h"]  # noqa: E222  предыдущее сообщение
r.NEXT.ks =      ["Right", "l"]  # noqa: E222  следующее сообщение
r.PREP.ks =      ["S-n"]  # noqa: E222  перейти ниже по цепочке ответов
r.NREP.ks =      ["n"]  # noqa: E222  вернуться по цепочке ответов
r.UP.ks =        ["Up", "k"]  # noqa: E222  прокрутка вверх
r.DOWN.ks =      ["Down", "j"]  # noqa: E222  прокрутка вниз
r.PPAGE.ks =     ["PgUp", "S-b"]  # noqa: E222  страница вверх
r.NPAGE.ks =     ["PgDn", "S-f"]  # noqa: E222  страница вниз
r.UKEYS.ks =     ["RET", "SPC"]  # noqa: E222  клавиша прокрутки или перехода к следующему сообщению
r.HOME.ks =      ["Home", "S-k"]  # noqa: E222  в начало сообщения
r.MEND.ks =      ["End", "S-j"]  # noqa: E222  в конец сообщения
r.BEGIN.ks =     ["S-h"]  # noqa: E222  в начало эхоконференции
r.END.ks =       ["S-l"]  # noqa: E222  в конец эхоконференции
r.INS.ks =       ["i", "S-i"]  # noqa: E222  добавить сообщение
r.SAVE.ks =      ["w", "S-w"]  # noqa: E222  сохранить сообщение в файл
r.FAVORITES.ks = ["f"]  # noqa: E222  добавить сообщение в избранные
r.QUOTE.ks =     ["r", "S-r"]  # noqa: E222  ответить с цитированием
r.INFO.ks =      ["m", "S-m"]  # noqa: E222  показать msgid, адрес, тему сообщения в отдельном окне
r.LINKS.ks =     ["v", "S-v"]  # noqa: E222  работа со ссылками
r.GETMSG.ks =    ["g", "S-g"]  # noqa: E222  получить текущее сообщение с ноды
r.TO_OUT.ks =    ["o", "S-o"]  # noqa: E222  перенести неотправленное исходящее сообщение в черновики
r.TO_DRAFTS.ks = ["d", "S-d"]  # noqa: E222  перенести черновик в исходящие сообщения
r.LIST.ks =      ["t", "S-t"]  # noqa: E222  список сообщений
r.INLINES.ks =   ["z", "S-z"]  # noqa: E222  вкл/выкл поддержку inline-оформления
r.MSUBJ.ks =     ["!"]  # noqa: E222  вкл/выкл просмотр сообщений по теме
r.QUIT.ks =      ["b", "S-b", "ESC"]  # noqa: E222  вернуться на экран выбора эхоконференции

# Клавиши для просмотра исходящих и черновиков
o.EDIT.ks = ["e", "S-e"]  # редактировать сообщение
o.SIGN.ks = ["M-s"]  # подписать сообщение PGP-ключом
o.DEL.ks = ["Del", "x", "S-x"]  # удалить черновик/исходящее/избранное

# Клавиши быстрого поиска
qs.OPEN.ks =  ["s", "S-s"]  # noqa: E222  открыть текстовое поле быстрого поиска
qs.CLOSE.ks = ["ESC"]  # noqa: E222  прервать ввод текста
qs.APPLY.ks = ["RET"]  # noqa: E222  закрыть поиск оставив найденное (список сообщений, селектор эх)
qs.LEFT.ks =  ["Left"]  # noqa: E222  курсор на символ влево
qs.RIGHT.ks = ["Right"]  # noqa: E222  курсор на символ вправо
qs.BS.ks =    ["BS"]  # noqa: E222  удалить символ перед курсором
qs.DEL.ks =   ["Del"]  # noqa: E222  удалить символ под курсором
qs.HOME.ks =  ["Home"]  # noqa: E222  первое вхождение
qs.END.ks =   ["End"]  # noqa: E222  последнее вхождение
qs.PREV.ks =  ["Up"]  # noqa: E222  предыдущее вхождение
qs.NEXT.ks =  ["Down"]  # noqa: E222  следующее вхождение
qs.PPAGE.ks = ["PgUp"]  # noqa: E222  вхождение на предыдущей странице
qs.NPAGE.ks = ["PgDn"]  # noqa: E222  вхождение на следующей странице
# @formatter:on
