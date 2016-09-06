import curses

# Клавиши для экрана выбора эхоконференции
s_up =        [curses.KEY_UP]    # курсор вверх
s_down =      [curses.KEY_DOWN]  # курсор вниз
s_ppage =     [curses.KEY_PPAGE] # страница вверх
s_npage =     [curses.KEY_NPAGE] # страница вниз
s_home =      [curses.KEY_HOME]  # в начало
s_end =       [curses.KEY_END]   # в конец
s_get =       [ord("g"), ord("G")]         # получить сообщения
s_send =      [ord("s"), ord("S")]         # отправить сообщения
s_archive =   [9]                # переключение в архив и обратно
s_enter =     [10, curses.KEY_RIGHT, ord(" ")]         # открыть эху
s_out =       [ord("o"), ord("O")]         # исходящие сообщения
s_drafts =    [ord("d"), ord("D")] # черновики
s_nnode =     [ord(".")]         # следующая нода
s_pnode =     [ord(",")]         # предыдущая нода
s_clone =     [ord("c"), ord("C")] # клонировать эху
s_config =    [ord("e"), ord("E")] # редактировать конфиг

# Клавиши для экрана чтения
r_prev =      [curses.KEY_LEFT]  # предыдущее сообщение
r_next =      [curses.KEY_RIGHT] # следующее сообщение
r_prep =      [ord("-")]         # перейти ниже по цепочке ответов
r_nrep =      [ord("=")]         # вернуться по цепочке ответов
r_up =        [curses.KEY_UP]    # прокрутка вверх
r_down =      [curses.KEY_DOWN]  # прокрутка вниз
r_ppage =     [curses.KEY_PPAGE] # страница вверх
r_npage =     [curses.KEY_NPAGE] # страница вниз
r_ukeys =     [10, ord(" ")]     # клавиша прокрутки или перехода к следующему сообщению
r_home =      [curses.KEY_HOME]  # в начало сообщения
r_mend =      [curses.KEY_END]   # в конец сообщения
r_begin =     [ord("<")]         # в начало эхоконференции
r_end =       [ord(">")]         # в конце эхоконференции
r_ins =       [ord("i"), ord("I"), curses.KEY_IC]         # добавить сообщение
r_save =      [ord("w"), ord("W")]         # сохранить сообщение в файл
r_favorites = [ord("f"), ord("F")]         # добавить сообщение в избранные
r_quote =     [ord("q"), ord("Q")]         # ответить с цитированием
r_subj =      [ord("s"), ord("S")]         # показать messagebox с темой сообщения
r_info =      [ord("m"), ord("M")]         # показать msgid и адрес
r_links    =  [ord("v"), ord("V")]         # работа со ссылками
r_getmsg =    [ord("g"), ord("G")]         # получить текущее сообщение с ноды
r_to_out =    [ord("o"), ord("O")] # перенести неотправленное исходящее сообщение в черновики
r_to_drafts = [ord("d"), ord("D")] # перенести черновик в исходящие сообщения
r_quit =      [27]               # вернуться на экран выбора эхоконференции

# Клавиши для просмотра исходящих
o_edit =      [ord("e"), ord("E")]         # редактировать сообщение

# Клавиши для просмотра избранных сообщений
f_delete =    [curses.KEY_DC]    # удалить из избранных

g_quit =      [curses.KEY_F10]   # закрыть клиент
