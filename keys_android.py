import curses

## Клавиши для экрана выбора эхоконференции
# курсор вверх
s_up = [curses.KEY_UP, ord("k")]
# курсор вниз
s_down = [curses.KEY_DOWN, ord("j")]
# страница вверх
s_ppage = [curses.KEY_PPAGE, ord("K")]
# страница вниз
s_npage = [curses.KEY_NPAGE, ord("J")]
# в начало
s_home = [curses.KEY_HOME, ord("H")]
# в конец
s_end = [curses.KEY_END, ord("L")]
# получить сообщения
s_get = [ord("g"), ord("G")]
# переключение в архив и обратно
s_archive = [9, ord("t")]
# открыть эху
s_enter = [10, curses.KEY_RIGHT, ord(" "), ord("l")]
# исходящие сообщения
s_out = [ord("o"), ord("O")]
# черновики
s_drafts = [ord("d"), ord("D")]
# следующая нода
s_nnode = [ord(".")]
# предыдущая нода
s_pnode = [ord(",")]
# клонировать эху
s_clone = [ord("c")]
# редактировать конфиг
s_config = [ord("e"), ord("E")]

## Клавиши для экрана чтения
# предыдущее сообщение
r_prev = [curses.KEY_LEFT, ord("h")]
# следующее сообщение
r_next = [curses.KEY_RIGHT, ord("l")]
# перейти ниже по цепочке ответов
r_prep = [ord("N")]
# вернуться по цепочке ответов
r_nrep = [ord("n")]
# прокрутка вверх
r_up = [curses.KEY_UP, ord("k")]
# прокрутка вниз
r_down = [curses.KEY_DOWN, ord("j")]
# страница вверх
r_ppage = [curses.KEY_PPAGE, ord("B")]
# страница вниз
r_npage = [curses.KEY_NPAGE, ord("F")]
# клавиша прокрутки или перехода к следующему сообщению
r_ukeys = [10, ord(" ")]
# в начало сообщения
r_home = [curses.KEY_HOME, ord("K")]
# в конец сообщения
r_mend = [curses.KEY_END, ord("J")]
# в начало эхоконференции
r_begin = [ord("H")]
# в конец эхоконференции
r_end = [ord("L")]
# добавить сообщение
r_ins = [ord("i"), ord("I")]
# сохранить сообщение в файл
r_save = [ord("w"), ord("W")]
# добавить сообщение в избранные
r_favorites = [ord("f")]
# ответить с цитированием
r_quote = [ord("r"), ord("R")]
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
r_list = [ord("t"), ord("t")]
# вернуться на экран выбора эхоконференции
r_quit = [27, ord("b"), ord("B")]

## Клавиши для просмотра исходящих и черновиков
# редактировать сообщение
o_edit = [ord("e"), ord("E")]

# Клавиши для просмотра избранных сообщений
# удалить из избранных
f_delete = [curses.KEY_DC, ord("x"), ord("X")]

# закрыть клиент
g_quit = [curses.KEY_F10, ord("q"), ord("Q")]
