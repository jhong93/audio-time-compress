#!/usr/bin/env python3

import argparse
import curses
import hashlib
import math
import os
import numpy as np
import sounddevice as sd
from subprocess import DEVNULL, STDOUT, check_call
from scipy.io import wavfile


TMP_DIR = '/tmp/wav'


def get_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('file', type=str, help='File to play')
    parser.add_argument('--policy', type=str, choices=['aimd'], default='aimd',
                        help='User interaction policy')
    parser.add_argument('--chunk-len', type=float, default=0.1,
                        help='Length of audio chunks in seconds')
    return parser.parse_args()


def get_md5(filename):
    m = hashlib.md5()
    with open(filename, 'rb') as fp:
        m.update(fp.read())
    return m.hexdigest()


def read_audio_file(filename):
    if filename.endswith('.wav'):
        infile = filename
    else:
        if not os.path.isdir(TMP_DIR):
            os.makedirs(TMP_DIR)
        infile = os.path.join(TMP_DIR, '{}.wav'.format(get_md5(filename)))
        if not os.path.exists(infile):
            check_call(['ffmpeg', '-i', filename, infile], stdout=DEVNULL,
                       stderr=STDOUT)
        print ('Converted file to wav:', infile)
    return wavfile.read(infile)


def init_window():
    window = curses.initscr()
    curses.cbreak()
    window.nodelay(True)
    return window


def main(args):
    input_file = args.file

    fs, data = read_audio_file(input_file)
    chunk_size = int(fs * args.chunk_len)
    num_chunks = math.ceil(len(data) / chunk_size)

    print('Frequency', fs)
    print('Data', data)
    print('Chunk size', chunk_size)
    print('Num chunks', num_chunks)

    window = init_window()

    sd.play(data, fs)
    sd.wait()


if __name__ == '__main__':
    main(get_args())
