import curses

# Клавиши для экрана выбора эхоконференции
s_up =        [curses.KEY_UP, ord("k")]    # курсор вверх
s_down =      [curses.KEY_DOWN, ord("j")]  # курсор вниз
s_ppage =     [curses.KEY_PPAGE, ord("K")] # страница вверх
s_npage =     [curses.KEY_NPAGE, ord("J")] # страница вниз
s_home =      [curses.KEY_HOME, ord("H")]  # в начало
s_end =       [curses.KEY_END, ord("L")]   # в конец
s_get =       [ord("g"), ord("G")]         # получить сообщения
s_send =      [ord("s"), ord("S")]         # отправить сообщения
s_archive =   [9, ord("t")]                # переключение в архив и обратно
s_enter =     [10, curses.KEY_RIGHT, ord(" "), ord("l")]         # открыть эху
s_out =       [ord("o"), ord("O")]         # исходящие сообщения
s_drafts =    [ord("d"), ord("D")] # черновики
s_nnode =     [ord(".")]         # следующая нода
s_pnode =     [ord(",")]         # предыдущая нода
s_clone =     [ord("c")]         # клонировать эху
s_config =    [ord("e"), ord("E")] # редактировать конфиг

# Клавиши для экрана чтения
r_prev =      [curses.KEY_LEFT, ord("h")]  # предыдущее сообщение
r_next =      [curses.KEY_RIGHT, ord("l")] # следующее сообщение
r_prep =      [ord("N")]         # перейти ниже по цепочке ответов
r_nrep =      [ord("n")]         # вернуться по цепочке ответов
r_up =        [curses.KEY_UP, ord("k")]    # прокрутка вверх
r_down =      [curses.KEY_DOWN, ord("j")]  # прокрутка вниз
r_ppage =     [curses.KEY_PPAGE, ord("B")] # страница вверх
r_npage =     [curses.KEY_NPAGE, ord("F")] # страница вниз
r_ukeys =     [10, ord(" ")]         # клавиша прокрутки или перехода к следующему сообщению
r_home =      [curses.KEY_HOME, ord("K")]  # в начало сообщения
r_mend =      [curses.KEY_END, ord("J")]   # в конец сообщения
r_begin =     [ord("H")]                   # в начало эхоконференции
r_end =       [ord("L")]                   # в конец эхоконференции
r_ins =       [ord("i"), ord("I")]         # добавить сообщение
r_save =      [ord("w"), ord("W")]         # сохранить сообщение в файл
r_favorites = [ord("f")]         # добавить сообщение в избранные
r_quote =     [ord("r"), ord("R")]         # ответить с цитированием
r_subj =      [ord("s"), ord("S")]         # показать messagebox с темой сообщения
r_info =      [ord("m"), ord("M")]         # показать msgid и адрес
r_links    =  [ord("v"), ord("V")]         # работа со ссылками
r_getmsg =    [ord("g"), ord("G")]         # получить текущее сообщение с ноды
r_to_out =    [ord("o"), ord("O")] # перенести неотправленное исходящее сообщение в черновики
r_to_drafts = [ord("d"), ord("D")] # перенести черновик в исходящие сообщения
r_list =      [ord("t"), ord("t")]
r_quit =      [27, ord("b"), ord("B")]               # вернуться на экран выбора эхоконференции

# Клавиши для просмотра исходящих
o_edit =      [ord("e"), ord("E")]         # редактировать сообщение

# Клавиши для просмотра избранных сообщений
f_delete =    [curses.KEY_DC, ord("x"), ord("X")]    # удалить из избранных

g_quit =      [curses.KEY_F10, ord("q"), ord("Q")]   # закрыть клиент
