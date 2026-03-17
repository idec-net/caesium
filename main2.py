import curses


def main(stdscr):
    curses.start_color()
    curses.use_default_colors()
    for i in range(0, curses.COLORS):
        curses.init_pair(i + 1, i, i)
    try:
        for i in range(0, curses.COLORS):
            stdscr.addstr(str(i), curses.color_pair(i))
        stdscr.addstr(str('\n'))
        for i in range(0, curses.COLORS):
            stdscr.addstr(str(i), curses.color_pair(i) | curses.A_BOLD)
    except curses.ERR:
        # End of screen reached
        pass
    stdscr.getch()


curses.wrapper(main)
