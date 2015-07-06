#!/usr/bin/env python3

import curses
from time import sleep
from datetime import datetime

echoes = [ ["ii.14", "Обсуждение вопросов, связанных с ii"], ["pipe.2032", "Болталка"], ["mlp.15", "Уголок дружбомагии"], ["ii.test.15", "Тестовые сообщения"], ["younglinux.info.14", "Статьи с сайта younlinux.info"] ]
echo_cursor = 0

def get_term_size():
    global width, height
    height, width = stdscr.getmaxyx()

def draw_title(y, x, title):
    stdscr.addstr(y, x, "[", curses.color_pair(1) + curses.A_BOLD)
    stdscr.addstr(y, x + 1, " " + title + " ", curses.color_pair(2) + curses.A_BOLD)
    stdscr.addstr(y, x + 3 + len(title), "]", curses.color_pair(1) + curses.A_BOLD)

def draw_cursor(y, color):
    for i in range (1, width - 1):
        stdscr.addstr(y + 1, i, " ", color)

def draw_echo_selector(start):
    stdscr.attron(curses.color_pair(1))
    stdscr.attron(curses.A_BOLD)
    stdscr.border()
    draw_title(0, 1, "Выбор эхоконференции")
    y = 0
    for echo in echoes:
        if y - start < height - 2:
            if y == echo_cursor:
                if y >= start:
                    draw_cursor(y - start, curses.color_pair(3))
                stdscr.attron (curses.color_pair(3) + curses.A_BOLD)
            else:
                if y >= start:
                    draw_cursor(y - start, curses.color_pair(4))
                stdscr.attron (curses.color_pair(4))
                stdscr.attroff (curses.A_BOLD)
            if y + 1 >= start + 1:
                stdscr.addstr(y + 1 - start, 2, echo[0])
                if width - 26 >= len(echo[1]):
                    stdscr.addstr(y + 1 - start, 25, echo[1])
                else:
                    cut_index = width - 26 - len(echo[1])
                    stdscr.addstr(y + 1 - start, 25, echo[1][:cut_index])
        y = y + 1
    draw_title (height - 1, width - 10, datetime.now().strftime("%H:%M"))
    stdscr.refresh()

def echo_selector():
    global echo_cursor
    key = 0
    start = 0
    while not key == curses.KEY_F10:
        draw_echo_selector(start)
        key = stdscr.getch()
        if key == curses.KEY_RESIZE:
            get_term_size()
            stdscr.clear()
        elif key == curses.KEY_UP and echo_cursor > 0:
            echo_cursor = echo_cursor - 1
            if echo_cursor - start < 0 and start > 0:
                start = start - 1
        elif key == curses.KEY_DOWN and echo_cursor < len(echoes) - 1:
            echo_cursor = echo_cursor + 1
            if echo_cursor - start > height - 3 and start < len(echoes) - height + 2:
                start = start + 1

stdscr = curses.initscr()
curses.start_color()
curses.noecho()
curses.curs_set(False)
stdscr.keypad(True)
curses.init_pair(1, 4, 0)
curses.init_pair(2, 3, 0)
curses.init_pair(3, 7, 4)
curses.init_pair(4, 7, 0)
get_term_size()
echo_selector()

#sleep(5)
curses.echo()
curses.curs_set(True)
curses.endwin()
