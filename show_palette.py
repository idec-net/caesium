#!/usr/bin/env python3
import curses


def main(stdscr):
    curses.start_color()
    curses.use_default_colors()
    for i in range(0, curses.COLORS):
        curses.init_pair(i + 1, i, -1)
    try:
        for i in range(0, curses.COLORS + 1):
            stdscr.addstr(f" {i-1:03} ",
                          curses.color_pair(i) | curses.A_BOLD)
            if i == 16 or (i - 16) % 24 == 0:
                stdscr.addstr(str('\n'))
        stdscr.addstr(str('\n'))
        for i in range(0, curses.COLORS + 1):
            stdscr.addstr(f" {i-1:03} ",
                          curses.color_pair(i) | curses.A_BOLD | curses.A_DIM)
            if i == 16 or (i - 16) % 24 == 0:
                stdscr.addstr(str('\n'))
        stdscr.addstr(str('\n'))
        for i in range(0, curses.COLORS + 1):
            stdscr.addstr(f" {i-1:03} ",
                          curses.color_pair(i))
            if i == 16 or (i - 16) % 24 == 0:
                stdscr.addstr(str('\n'))
        stdscr.addstr(str('\n'))
        for i in range(0, curses.COLORS + 1):
            stdscr.addstr(f" {i-1:03} ",
                          curses.color_pair(i) | curses.A_DIM)
            if i == 16 or (i - 16) % 24 == 0:
                stdscr.addstr(str('\n'))
    except curses.error:
        # End of screen reached
        pass
    stdscr.getch()


curses.wrapper(main)
