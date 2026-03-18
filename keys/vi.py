from core.cmd import Common as c
from core.cmd import Out as o
from core.cmd import Reader as r
from core.cmd import Selector as s

# @formatter:off
c.QUIT.ks = ["F10", "z", "Z"]  # закрыть клиент

# Клавиши для экрана выбора эхоконференции
s.UP.ks =      ["Up", "k", "K"]    # noqa: E222  курсор вверх
s.DOWN.ks =    ["Down", "j", "J"]  # noqa: E222  курсор вниз
s.PPAGE.ks =   ["PgUp", "l", "L"]  # noqa: E222  страница вверх
s.NPAGE.ks =   ["PgDn", "h", "h"]  # noqa: E222  страница вниз
s.HOME.ks =    ["Home", "^"]       # noqa: E222  в начало
s.END.ks =     ["End", "$"]        # noqa: E222  в конец
s.GET.ks =     ["g", "G"]          # noqa: E222  получить сообщения (свежие по счётчику)
s.FGET.ks =    ["Ctrl+G"]          # noqa: E222  получить сообщения (полный индекс)
s.ARCHIVE.ks = ["Tab"]             # noqa: E222  переключение в архив и обратно
s.ENTER.ks =   ["Enter", "Right", "Space"]  # noqa: E222  открыть эху
s.OUT.ks =     ["o", "O"]          # noqa: E222  исходящие сообщения
s.DRAFTS.ks =  ["d", "D"]          # noqa: E222  черновики
s.NNODE.ks =   ["."]               # noqa: E222  следующая нода
s.PNODE.ks =   [","]               # noqa: E222  предыдущая нода
s.CONFIG.ks =  ["e", "E"]          # noqa: E222  редактировать конфиг
s.OSEARCH.ks = ["s", "S"]          # noqa: E222  быстрый поиск
s.CSEARCH.ks = ["ESC"]             # noqa: E222  закрыть поиск
s.ASEARCH.ks = ["Enter"]           # noqa: E222  закрыть поиск оставив найденные элементы
s.FIND.ks =    ["y", "Y"]          # noqa: E222  открыть окно поиска по БД

# Клавиши для экрана чтения
r.PREV.ks =      ["Left", "h", "H"]   # noqa: E222  предыдущее сообщение
r.NEXT.ks =      ["Right", "l", "L"]  # noqa: E222  следующее сообщение
r.PREP.ks =      ["-"]                # noqa: E222  перейти ниже по цепочке ответов
r.NREP.ks =      ["="]                # noqa: E222  вернуться по цепочке ответов
r.UP.ks =        ["Up", "k", "K"]     # noqa: E222  прокрутка вверх
r.DOWN.ks =      ["Down", "j", "J"]   # noqa: E222  прокрутка вниз
r.PPAGE.ks =     ["PgUp"]             # noqa: E222  страница вверх
r.NPAGE.ks =     ["PgDn"]             # noqa: E222  страница вниз
r.UKEYS.ks =     ["Enter", "Space"]   # noqa: E222  клавиша прокрутки или перехода к следующему сообщению
r.HOME.ks =      ["Home", "^"]        # noqa: E222  в начало сообщения
r.MEND.ks =      ["End", "$"]         # noqa: E222  в конец сообщения
r.BEGIN.ks =     ["<"]                # noqa: E222  в начало эхоконференции
r.END.ks =       [">"]                # noqa: E222  в конце эхоконференции
r.INS.ks =       ["i", "I", "Ins"]    # noqa: E222  добавить сообщение
r.SAVE.ks =      ["w", "W"]           # noqa: E222  сохранить сообщение в файл
r.FAVORITES.ks = ["f", "F"]           # noqa: E222  добавить сообщение в избранные
r.QUOTE.ks =     ["a", "A"]           # noqa: E222  ответить с цитированием
r.INFO.ks =      ["m", "M"]           # noqa: E222  показать msgid, адрес, тему сообщения в отдельном окне
r.LINKS.ks =     ["v", "V"]           # noqa: E222  работа со ссылками
r.GETMSG.ks =    ["g", "G"]           # noqa: E222  получить текущее сообщение с ноды
r.TO_OUT.ks =    ["o", "O"]           # noqa: E222  перенести неотправленное исходящее сообщение в черновики
r.TO_DRAFTS.ks = ["d", "D"]           # noqa: E222  перенести черновик в исходящие сообщения
r.LIST.ks =      []                   # noqa: E222  список сообщений ???
r.INLINES.ks =   ["x", "X"]           # noqa: E222  вкл/выкл поддержку inline-оформления
r.MSUBJ.ks =     ["!"]                # noqa: E222  вкл/выкл просмотр сообщений по теме
r.QUIT.ks =      ["q", "Q", "ESC"]    # noqa: E222  вернуться на экран выбора эхоконференции

# Клавиши для просмотра исходящих
o.EDIT.ks = ["e", "E"]          # редактировать сообщение
o.SIGN.ks = ["Alt+s", "Alt+S"]  # подписать сообщение PGP-ключом
o.DEL.ks = ["Del"]              # удалить черновик/исходящее/избранное
# @formatter:on
