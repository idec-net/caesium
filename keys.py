import curses

## Клавиши для экрана выбора эхоконференции
# курсор вверх
s_up = [curses.KEY_UP]
# курсор вниз
s_down = [curses.KEY_DOWN]
# страница вверх
s_ppage = [curses.KEY_PPAGE]
# страница вниз
s_npage = [curses.KEY_NPAGE]
# в начало
s_home = [curses.KEY_HOME]
# в конец
s_end = [curses.KEY_END]
# получить сообщения
s_get = [ord("g"), ord("G")]
# переключение в архив и обратно
s_archive = [9]
# открыть эху
s_enter = [10, curses.KEY_RIGHT, ord(" ")]
# исходящие сообщения
s_out = [ord("o"), ord("O")]
# черновики
s_drafts = [ord("d"), ord("D")]
# следующая нода
s_nnode = [ord(".")]
# предыдущая нода
s_pnode = [ord(",")]
# клонировать эху
s_clone = [ord("c"), ord("C")]
# редактировать конфиг
s_config = [ord("e"), ord("E")]

## Клавиши для экрана чтения
# предыдущее сообщение
r_prev = [curses.KEY_LEFT]
# следующее сообщение
r_next = [curses.KEY_RIGHT]
# перейти ниже по цепочке ответов
r_prep = [ord("-")]
# вернуться по цепочке ответов
r_nrep = [ord("=")]
# прокрутка вверх
r_up = [curses.KEY_UP]
# прокрутка вниз
r_down = [curses.KEY_DOWN]
# страница вверх
r_ppage = [curses.KEY_PPAGE]
# страница вниз
r_npage = [curses.KEY_NPAGE]
# клавиша прокрутки или перехода к следующему сообщению
r_ukeys = [10, ord(" ")]
#в начало сообщения
r_home = [curses.KEY_HOME]
# в конец сообщения
r_mend = [curses.KEY_END]
# в начало эхоконференции
r_begin = [ord("<")]
# в конце эхоконференции
r_end = [ord(">")]
# добавить сообщение
r_ins = [ord("i"), ord("I"), curses.KEY_IC]
# сохранить сообщение в файл
r_save = [ord("w"), ord("W")]
# добавить сообщение в избранные
r_favorites = [ord("f"), ord("F")]
# ответить с цитированием
r_quote = [ord("q"), ord("Q")]
# показать messagebox с темой сообщения
r_subj = [ord("s"), ord("S")]
# показать msgid и адрес
r_info = [ord("m"), ord("M")]
# работа со ссылками
r_links = [ord("v"), ord("V")]
# получить текущее сообщение с ноды
r_getmsg = [ord("g"), ord("G")]
# перенести неотправленное исходящее сообщение в черновики
r_to_out = [ord("o"), ord("O")]
# перенести черновик в исходящие сообщения
r_to_drafts = [ord("d"), ord("D")]
# список сообщений
r_list = [ord("l"), ord("L")]
# вернуться на экран выбора эхоконференции
r_quit = [27]

## Клавиши для просмотра исходящих и черновиков
# редактировать сообщение
o_edit = [ord("e"), ord("E")]

## Клавиши для просмотра избранных сообщений
# удалить из избранных
f_delete = [curses.KEY_DC]

## закрыть клиент
g_quit = [curses.KEY_F10]
