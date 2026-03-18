from core.cmd import Common as c
from core.cmd import Out as o
from core.cmd import Reader as r
from core.cmd import Selector as s

# @formatter:off
c.QUIT.ks = ["F10", "q", "Q"]  # закрыть клиент

# Клавиши для экрана выбора эхоконференции
s.UP.ks =      ["Up", "k"]    # noqa: E222  курсор вверх
s.DOWN.ks =    ["Down", "j"]  # noqa: E222  курсор вниз
s.PPAGE.ks =   ["PgUp", "K"]  # noqa: E222  страница вверх
s.NPAGE.ks =   ["PgDn", "J"]  # noqa: E222  страница вниз
s.HOME.ks =    ["Home", "H"]  # noqa: E222  в начало
s.END.ks =     ["End", "L"]   # noqa: E222  в конец
s.GET.ks =     ["g", "G"]     # noqa: E222  получить сообщения (свежие по счётчику)
s.FGET.ks =    ["Ctrl+G"]     # noqa: E222  получить сообщения (полный индекс)
s.ARCHIVE.ks = ["Tab", "t"]   # noqa: E222  переключение в архив и обратно
s.ENTER.ks =   ["Enter", "Right", "Space", "l"]  # noqa: E222  открыть эху
s.OUT.ks =     ["o", "O"]     # noqa: E222  исходящие сообщения
s.DRAFTS.ks =  ["d", "D"]     # noqa: E222  черновики
s.NNODE.ks =   ["."]          # noqa: E222  следующая нода
s.PNODE.ks =   [","]          # noqa: E222  предыдущая нода
s.CONFIG.ks =  ["e", "E"]     # noqa: E222  редактировать конфиг
s.OSEARCH.ks = ["s", "S"]     # noqa: E222  быстрый поиск
s.CSEARCH.ks = ["ESC"]        # noqa: E222  закрыть поиск
s.ASEARCH.ks = ["Enter"]      # noqa: E222  закрыть поиск оставив найденные элементы
s.FIND.ks =    ["y", "Y"]     # noqa: E222  открыть окно поиска по БД

## Клавиши для экрана чтения
r.PREV.ks =      ["Left", "h"]       # noqa: E222  предыдущее сообщение
r.NEXT.ks =      ["Right", "l"]      # noqa: E222  следующее сообщение
r.PREP.ks =      ["N"]               # noqa: E222  перейти ниже по цепочке ответов
r.NREP.ks =      ["n"]               # noqa: E222  вернуться по цепочке ответов
r.UP.ks =        ["Up", "k"]         # noqa: E222  прокрутка вверх
r.DOWN.ks =      ["Down", "j"]       # noqa: E222  прокрутка вниз
r.PPAGE.ks =     ["PgUp", "B"]       # noqa: E222  страница вверх
r.NPAGE.ks =     ["PgDn", "F"]       # noqa: E222  страница вниз
r.UKEYS.ks =     ["Enter", "Space"]  # noqa: E222  клавиша прокрутки или перехода к следующему сообщению
r.HOME.ks =      ["Home", "K"]       # noqa: E222  в начало сообщения
r.MEND.ks =      ["End", "J"]        # noqa: E222  в конец сообщения
r.BEGIN.ks =     ["H"]               # noqa: E222  в начало эхоконференции
r.END.ks =       ["L"]               # noqa: E222  в конце эхоконференции
r.INS.ks =       ["i", "I"]          # noqa: E222  добавить сообщение
r.SAVE.ks =      ["w", "W"]          # noqa: E222  сохранить сообщение в файл
r.FAVORITES.ks = ["f"]               # noqa: E222  добавить сообщение в избранные
r.QUOTE.ks =     ["r", "R"]          # noqa: E222  ответить с цитированием
r.INFO.ks =      ["m", "M"]          # noqa: E222  показать msgid, адрес, тему сообщения в отдельном окне
r.LINKS.ks =     ["v", "V"]          # noqa: E222  работа со ссылками
r.GETMSG.ks =    ["g", "G"]          # noqa: E222  получить текущее сообщение с ноды
r.TO_OUT.ks =    ["o", "O"]          # noqa: E222  перенести неотправленное исходящее сообщение в черновики
r.TO_DRAFTS.ks = ["t", "T"]          # noqa: E222  перенести черновик в исходящие сообщения
r.LIST.ks =      []                  # noqa: E222  список сообщений ???
r.INLINES.ks =   ["z", "Z"]          # noqa: E222  вкл/выкл поддержку inline-оформления
r.MSUBJ.ks =     ["!"]               # noqa: E222  вкл/выкл просмотр сообщений по теме
r.QUIT.ks =      ["b", "B", "ESC"]   # noqa: E222  вернуться на экран выбора эхоконференции

# Клавиши для просмотра исходящих и черновиков
o.EDIT.ks = ["e", "E"]          # редактировать сообщение
o.SIGN.ks = ["Alt+s", "Alt+S"]  # подписать сообщение PGP-ключом
o.DEL.ks = ["Del", "x", "X"]    # удалить черновик/исходящее/избранное
# @formatter:on
