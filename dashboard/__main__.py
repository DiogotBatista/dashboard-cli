import curses

from dashboard.tui import run

try:
    curses.wrapper(run)
except KeyboardInterrupt:
    pass
