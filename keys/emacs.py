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

# TODO: Emacs keystrokes
# @formatter:off
c.QUIT.ks =  []  # noqa: E222  закрыть клиент
c.UP.ks =    []  # noqa: E222  курсор вверх
c.DOWN.ks =  []  # noqa: E222  курсор вниз
c.LEFT.ks =  []  # noqa: E222  курсор влево
c.RIGHT.ks = []  # noqa: E222  курсор вправо
c.BS.ks =    []  # noqa: E222  удалить символ перед курсором
c.DEL.ks =   []  # noqa: E222  удалить символ под курсором
c.HOME.ks =  []  # noqa: E222  в начало
c.END.ks =   []  # noqa: E222  в конец

# Клавиши для экрана выбора эхоконференции
s.UP.ks =      []  # noqa: E222  курсор вверх
s.DOWN.ks =    []  # noqa: E222  курсор вниз
s.PPAGE.ks =   []  # noqa: E222  страница вверх
s.NPAGE.ks =   []  # noqa: E222  страница вниз
s.HOME.ks =    []  # noqa: E222  в начало
s.END.ks =     []  # noqa: E222  в конец
s.GET.ks =     []  # noqa: E222  получить сообщения (свежие по счётчику)
s.FGET.ks =    []  # noqa: E222  получить сообщения (полный индекс)
s.ARCHIVE.ks = []  # noqa: E222  переключение в архив и обратно
s.ENTER.ks =   []  # noqa: E222  открыть эху
s.OUT.ks =     []  # noqa: E222  исходящие сообщения
s.DRAFTS.ks =  []  # noqa: E222  черновики
s.NNODE.ks =   []  # noqa: E222  следующая нода
s.PNODE.ks =   []  # noqa: E222  предыдущая нода
s.CONFIG.ks =  []  # noqa: E222  редактировать конфиг
s.FIND.ks =    []  # noqa: E222  открыть окно поиска по БД

# Клавиши для экрана чтения
r.PREV.ks =      []  # noqa: E222  предыдущее сообщение
r.NEXT.ks =      []  # noqa: E222  следующее сообщение
r.PREP.ks =      []  # noqa: E222  перейти ниже по цепочке ответов
r.NREP.ks =      []  # noqa: E222  вернуться по цепочке ответов
r.UP.ks =        []  # noqa: E222  прокрутка вверх
r.DOWN.ks =      []  # noqa: E222  прокрутка вниз
r.LEFT.ks =      []  # noqa: E222  прокрутка влево
r.LEFTP.ks =     []  # noqa: E222  страница влево
r.RIGHT.ks =     []  # noqa: E222  прокрутка вправо
r.RIGHTP.ks =    []  # noqa: E222  страница вправо
r.PPAGE.ks =     []  # noqa: E222  страница вверх
r.NPAGE.ks =     []  # noqa: E222  страница вниз
r.UKEYS.ks =     []  # noqa: E222  клавиша прокрутки или перехода к следующему сообщению
r.HOME.ks =      []  # noqa: E222  в начало сообщения
r.MEND.ks =      []  # noqa: E222  в конец сообщения
r.BEGIN.ks =     []  # noqa: E222  в начало эхоконференции
r.END.ks =       []  # noqa: E222  в конец эхоконференции
r.INS.ks =       []  # noqa: E222  добавить сообщение
r.SAVE.ks =      []  # noqa: E222  сохранить сообщение в файл
r.FAVORITES.ks = []  # noqa: E222  добавить сообщение в избранные
r.QUOTE.ks =     []  # noqa: E222  ответить с цитированием
r.QUOTE_NOT.ks = []  # noqa: E222  ответить с цитированием (старый формат)
r.INFO.ks =      []  # noqa: E222  показать msgid, адрес, тему сообщения в отдельном окне
r.LINKS.ks =     []  # noqa: E222  работа со ссылками
r.GETMSG.ks =    []  # noqa: E222  получить текущее сообщение с ноды
r.TO_OUT.ks =    []  # noqa: E222  перенести неотправленное исходящее сообщение в черновики
r.TO_DRAFTS.ks = []  # noqa: E222  перенести черновик в исходящие сообщения
r.LIST.ks =      []  # noqa: E222  список сообщений
r.INLINES.ks =   []  # noqa: E222  вкл/выкл поддержку inline-оформления
r.HSCROLL.ks =   []  # noqa: E222  вкл/выкл горизонтальный скролл
r.MSUBJ.ks =     []  # noqa: E222  вкл/выкл просмотр сообщений по теме
r.QUIT.ks =      []  # noqa: E222  вернуться на экран выбора эхоконференции

# Клавиши для просмотра исходящих и черновиков
o.EDIT.ks = []  # редактировать сообщение
o.SIGN.ks = []  # подписать сообщение PGP-ключом
o.DEL.ks = []  # удалить черновик/исходящее/избранное

# Клавиши быстрого поиска
qs.OPEN.ks =  []  # noqa: E222  открыть текстовое поле быстрого поиска
qs.CLOSE.ks = []  # noqa: E222  прервать ввод текста
qs.APPLY.ks = []  # noqa: E222  закрыть поиск оставив найденное (список сообщений, селектор эх)
qs.LEFT.ks =  []  # noqa: E222  курсор на символ влево
qs.RIGHT.ks = []  # noqa: E222  курсор на символ вправо
qs.BS.ks =    []  # noqa: E222  удалить символ перед курсором
qs.DEL.ks =   []  # noqa: E222  удалить символ под курсором
qs.HOME.ks =  []  # noqa: E222  первое вхождение
qs.END.ks =   []  # noqa: E222  последнее вхождение
qs.PREV.ks =  []  # noqa: E222  предыдущее вхождение
qs.NEXT.ks =  []  # noqa: E222  следующее вхождение
qs.PPAGE.ks = []  # noqa: E222  вхождение на предыдущей странице
qs.NPAGE.ks = []  # noqa: E222  вхождение на следующей странице
# @formatter:on
