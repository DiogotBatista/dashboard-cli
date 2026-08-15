import curses

from dashboard.tui import run

curses.wrapper(run)
