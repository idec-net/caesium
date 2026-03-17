import curses

# @formatter:off
# Клавиши для экрана выбора эхоконференции
s_up =      [curses.KEY_UP, ord("k"), ord("K")]     # noqa: E222  курсор вверх
s_down =    [curses.KEY_DOWN, ord("j"), ord("J")]   # noqa: E222  курсор вниз
s_ppage =   [curses.KEY_PPAGE, ord("l"), ord("L")]  # noqa: E222  страница вверх
s_npage =   [curses.KEY_NPAGE, ord("h"), ord("H")]  # noqa: E222  страница вниз
s_home =    [curses.KEY_HOME, ord("^")]             # noqa: E222  в начало
s_end =     [curses.KEY_END, ord("$")]              # noqa: E222  в конец
s_get =     [ord("g"), ord("G")]                    # noqa: E222  получить сообщения (свежие по счётчику)
s_fget =    ["Ctrl+G"]                              # noqa: E222  получить сообщения (полный индекс)
s_archive = [9]                                     # noqa: E222  переключение в архив и обратно
s_enter =   [10, curses.KEY_RIGHT, ord(" ")]        # noqa: E222  открыть эху
s_out =     [ord("o"), ord("O")]                    # noqa: E222  исходящие сообщения
s_drafts =  [ord("d"), ord("D")]                    # noqa: E222  черновики
s_nnode =   [ord(".")]                              # noqa: E222  следующая нода
s_pnode =   [ord(",")]                              # noqa: E222  предыдущая нода
s_clone =   [ord("c"), ord("C")]                    # noqa: E222  клонировать эху
s_config =  [ord("e"), ord("E")]                    # noqa: E222  редактировать конфиг
s_osearch = [ord("s"), ord("S")]                    # noqa: E222  быстрый поиск
s_csearch = [27]                                    # noqa: E222  закрыть поиск
s_asearch = [10]                                    # noqa: E222  закрыть поиск оставив найденные элементы
s_find =    [ord("y"), ord("Y")]                    # noqa: E222  открыть окно поиска по БД

# Клавиши для экрана чтения
r_prev =    [curses.KEY_LEFT, ord("h"), ord("H")]   # noqa: E222  предыдущее сообщение
r_next =    [curses.KEY_RIGHT, ord("l"), ord("L")]  # noqa: E222  следующее сообщение
r_prep =    [ord("-")]                              # noqa: E222  перейти ниже по цепочке ответов
r_nrep =    [ord("=")]                              # noqa: E222  вернуться по цепочке ответов
r_up =      [curses.KEY_UP, ord("k"), ord("K")]     # noqa: E222  прокрутка вверх
r_down =    [curses.KEY_DOWN, ord("j"), ord("J")]   # noqa: E222  прокрутка вниз
r_ppage =   [curses.KEY_PPAGE]                      # noqa: E222  страница вверх
r_npage =   [curses.KEY_NPAGE]                      # noqa: E222  страница вниз
r_ukeys =   [10, ord(" ")]                          # noqa: E222  клавиша прокрутки или перехода к следующему сообщению
r_home =    [curses.KEY_HOME, ord("^")]             # noqa: E222  в начало сообщения
r_mend =    [curses.KEY_END, ord("$")]              # noqa: E222  в конец сообщения
r_begin =   [ord("<")]                              # noqa: E222  в начало эхоконференции
r_end =     [ord(">")]                              # noqa: E222  в конце эхоконференции
r_ins =     [ord("i"), ord("I"), curses.KEY_IC]     # noqa: E222  добавить сообщение
r_save =    [ord("w"), ord("W")]                    # noqa: E222  сохранить сообщение в файл
r_favorites = [ord("f"), ord("F")]                  # noqa: E222  добавить сообщение в избранные
r_quote =   [ord("a"), ord("A")]                    # noqa: E222  ответить с цитированием (answer)
r_info =    [ord("m"), ord("M")]                    # noqa: E222  показать msgid, адрес, тему сообщения в отдельном окне
r_links =   [ord("v"), ord("V")]                    # noqa: E222  работа со ссылками
r_getmsg =  [ord("g"), ord("G")]                    # noqa: E222  получить текущее сообщение с ноды
r_to_out =  [ord("o"), ord("O")]                    # noqa: E222  перенести неотправленное исходящее сообщение в черновики
r_to_drafts = [ord("d"), ord("D")]                  # noqa: E222  перенести черновик в исходящие сообщения
r_list =    []                                      # noqa: E222  список сообщений
r_inlines = [ord("z"), ord("Z")]                    # noqa: E222  вкл/выкл поддержку inline-оформления
r_msubj =   [ord("!")]                              # noqa: E222  вкл/выкл просмотр сообщений по теме
r_quit =    [ord("q"), ord("Q"), 27]                # noqa: E222  вернуться на экран выбора эхоконференции

# Клавиши для просмотра исходящих
o_edit = [ord("e"), ord("E")]  # редактировать сообщение
o_sign = ["Alt+s", "Alt+S"]    # подписать черновик PGP-ключом

# Клавиши для просмотра избранных сообщений
f_delete = [curses.KEY_DC]  # удалить из избранных

g_quit = [ord("z"), ord("Z"), curses.KEY_F10]  # закрыть клиент
# @formatter:on
