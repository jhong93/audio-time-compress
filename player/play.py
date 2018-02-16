#!/usr/bin/env python3

import argparse
import curses
import vlc
import sys
import time
import os
import numpy as np


MIN_RATE = 1.0
ADJ_INCREMENT = 0.1


def get_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('file', type=str, help='File to play')
    return parser.parse_args()


def refresh_screen(filename, start_time, window, player, rate):
    window.clear()
    line_count = 0

    def addstr(s):
        nonlocal line_count
        window.addstr(line_count, 0, s)
        line_count += 1

    addstr('Playing: {}'.format(filename))
    addstr('Position: {:0.2f}%'.format(player.get_position() * 100))
    addstr('Playback rate: {:0.1f}x'.format(rate))
    addstr('Wall time: {:0.3f}s'.format(time.time() - start_time))
    addstr('Media time: {:0.3f}s'.format(player.get_time() / 1000))
    addstr('Use UP and DOWN keys to adjust playback rate')
    window.refresh()


def main(args):
    assert os.path.isfile(args.file), '"{}" is not a file'.format(args.file)

    window = curses.initscr()
    curses.noecho()
    curses.cbreak()
    window.clear()
    window.keypad(True)
    window.nodelay(True)
    player = vlc.MediaPlayer(args.file)

    rate = MIN_RATE
    assert player.set_rate(rate) == 0

    player.play()
    start_time = time.time()

    while not np.isclose(player.get_position(), 1):
        k = window.getch()
        old_rate = rate
        if k == curses.KEY_UP:
            rate += ADJ_INCREMENT
        if k == curses.KEY_DOWN:
            rate = max(rate - ADJ_INCREMENT, MIN_RATE)
        if rate != old_rate:
            assert player.set_rate(rate) == 0

        refresh_screen(args.file, start_time, window, player, rate)
        time.sleep(0.1)


if __name__ == '__main__':
    main(get_args())
