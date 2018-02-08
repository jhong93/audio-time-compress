#!/usr/bin/env python3

import argparse
import curses
import vlc
import sys
import time
import os
import numpy as np
from pynput import keyboard


MIN_RATE = 1.0
ADJ_INCREMENT = 0.1


def get_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('file', type=str, help='File to play')
    return parser.parse_args()


def main(args):
    assert os.path.isfile(args.file), '"{}" is not a file'.format(args.file)

    window = curses.initscr()
    window.clear()
    curses.noecho()
    curses.cbreak()
    window.addstr(0, 0, 'Playing: {}'.format(args.file))
    player = vlc.MediaPlayer(args.file)

    rate = MIN_RATE
    assert player.set_rate(rate) == 0

    def keypress_handler(key):
        nonlocal rate
        old_rate = rate

        if key == keyboard.Key.up:
            rate += ADJ_INCREMENT
        if key == keyboard.Key.down:
            rate = max(rate - ADJ_INCREMENT, MIN_RATE)

        if old_rate != rate:
            assert player.set_rate(rate) == 0

    window.addstr(5, 0, 'Use UP and DOWN keys to adjust playback rate')
    player.play()
    start_time = time.time()
    with keyboard.Listener(on_press=keypress_handler) as listener:
        while not np.isclose(player.get_position(), 1):
            window.addstr(1, 0, 'Position: {:0.2f}%'.format(
                player.get_position() * 100))
            window.addstr(2, 0, 'Playback rate: {:0.1f}x'.format(rate))
            window.addstr(3, 0, 'Wall time: {:0.3f}s'.format(
                time.time() - start_time))
            window.addstr(4, 0, 'Media time: {:0.3f}s'.format(
                player.get_time() / 1000))
            window.refresh()
            time.sleep(0.1)


if __name__ == '__main__':
    main(get_args())
