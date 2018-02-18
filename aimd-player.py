#!/usr/bin/env python3

import argparse
import hashlib
import math
import os
import sys
import time
import numpy as np
import sounddevice as sd
from collections import namedtuple
from pynput.keyboard import Listener, Key
from subprocess import DEVNULL, STDOUT, check_call
from scipy.io import wavfile


TMP_DIR = '/tmp/wav'

MIN_PLAY_RATE = 1.0
MAX_PLAY_RATE = 4.0

DROP_KEY = Key.alt_r
LOCK_KEY = Key.ctrl_r

OUTPUT_FS = 44100

DropEvent = namedtuple('DropEvent', ['chunk', 'rate'])

def get_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('filename', type=str, help='File to play')
    parser.add_argument('-up', '--additive-increase', type=float,
                        default=0.05, dest= 'add_inc',
                        help='Increase in playback rate for each window len')
    parser.add_argument('-down', '--multiplicative-decrease', type=float,
                        default=0.8, dest='mult_dec',
                        help='Decrease in playback rate on user input')
    parser.add_argument('-c', '--chunk-len', type=float, default=1.0,
                        dest='chunk_len',
                        help='Processing length of audio chunks in seconds')
    parser.add_argument('-w', '--window-len', type=float, default=1.0,
                        dest='window_len',
                        help='Window length in seconds for rate increases')
    parser.add_argument('-a', '--algorithm', type=str, dest='algorithm',
                        choices=['fixed', 'random', 'nopause'],
                        default='nopause',
                        help='Algorithm to increase playback rate')
    parser.add_argument('--initial-rate', type=float, default=1.5,
                        dest='init_rate',
                        help='Initial playback rate')
    parser.add_argument('--save', type=str, dest='save_file',
                        help='Save resulting file')
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
            check_call(['ffmpeg', '-i', filename, '-ac', '1', infile],
                        stdout=DEVNULL, stderr=STDOUT)
        print ('Converted file to wav:', infile)
    return wavfile.read(infile)


def fixed_sample(chunk, expected_result_len):
    rate_inv = len(chunk) / expected_result_len
    result = np.zeros(expected_result_len, dtype=np.int16)
    for i in range(expected_result_len):
        result[i] = chunk[math.floor(i * rate_inv)]
    return result


def random_sample(chunk, expected_result_len):
    if expected_result_len == len(chunk):
        return chunk
    if expected_result_len < len(chunk):
        choice_idxs = np.sort(np.random.choice(len(chunk),
                              expected_result_len, replace=False))
    else:
        choice_idxs = np.random.choice(len(chunk),
                                       expected_result_len - len(chunk),
                                       replace=True)
        choice_idxs = np.concatenate(choice_idxs, np.arange(len(chunk)))
        choice_idxs = np.sort(choice_idxs)
    return chunk[choice_idxs]


def remove_pauses(chunk, min_thresh=25, std_thresh=2):
    magnitudes = np.abs(chunk)
    mean_magnitude = np.mean(magnitudes)
    std_magnitude = np.std(magnitudes)
    threshold = max(min_thresh, mean_magnitude - std_thresh * std_magnitude)
    selected_idxs = np.argwhere(magnitudes > threshold)
    return chunk[selected_idxs]


def speed_up_chunk(chunk, expected_result_len, algorithm):
    if algorithm == 'fixed':
        return fixed_sample(chunk, expected_result_len)
    elif algorithm == 'random':
        return random_sample(chunk, expected_result_len)
    elif algorithm == 'nopause':
        chunk_nopause = remove_pauses(chunk)
        return fixed_sample(chunk_nopause, math.ceil(
                            expected_result_len * len(chunk_nopause) / len(chunk)))
    else:
        raise Exception('Invalid algorithm: {}'.format(algorithm))


def print_info(curr_chunk, num_chunks, rate):
    sys.stdout.write('\r[{:6.2f}%] @ {:6.4f}x'.format(
                     curr_chunk / num_chunks * 100, rate))
    sys.stdout.flush()


def main(filename, add_inc, mult_dec, chunk_len, window_len, init_rate,
         algorithm, save_file):
    fs, raw_audio = read_audio_file(filename)
    if len(raw_audio.shape) != 1:
        raise Exception('Only mono wav files are supported')
    chunk_size = int(fs * chunk_len)
    num_chunks = math.ceil(len(raw_audio) / chunk_size)

    print ('Original frequency {}Hz'.format(fs))
    print ('Chunk size: {} samples'.format(chunk_size))
    print ('Chunk count: {}'.format(num_chunks))
    print ('Press {} to reduce playback speed'.format(DROP_KEY))
    print ('Press {} to lock playback speed'.format(LOCK_KEY))

    curr_rate = init_rate
    curr_chunk = 0
    lock_rate = False

    def get_chunk(i):
        return raw_audio[i * chunk_size:(i + 1) * chunk_size]

    def play_audio():
        nonlocal curr_rate
        nonlocal curr_chunk
        window_time = 0.0
        processed_chunks = []

        next_chunk = speed_up_chunk(get_chunk(curr_chunk),
                                    math.ceil(chunk_len * OUTPUT_FS / curr_rate),
                                    algorithm)
        processed_chunks.append(next_chunk)

        while curr_chunk < num_chunks:
            window_time += len(next_chunk) / OUTPUT_FS
            sd.play(next_chunk, OUTPUT_FS)
            curr_chunk += 1

            next_chunk = speed_up_chunk(get_chunk(curr_chunk),
                                        math.ceil(chunk_len * OUTPUT_FS / curr_rate),
                                        algorithm)
            processed_chunks.append(next_chunk)

            print_info(curr_chunk, num_chunks, curr_rate)
            sd.wait()

            while window_time > window_len:
                if not lock_rate:
                    curr_rate = min(curr_rate + add_inc, MAX_PLAY_RATE)
                window_time -= window_len

        return np.concatenate(processed_chunks)

    drop_events = []

    def key_handler(key):
        nonlocal curr_rate
        nonlocal lock_rate
        if key == DROP_KEY:
            drop_events.append(DropEvent(chunk=curr_chunk, rate=curr_rate))
            curr_rate = max(curr_rate * mult_dec, MIN_PLAY_RATE)
        elif key == LOCK_KEY:
            lock_rate = not lock_rate

    with Listener(on_press=key_handler) as listener:
        processed_audio = play_audio()

    print ('Mean rate: {:0.4f}x'.format(len(raw_audio) / float(len(processed_audio))))
    print ('Mean rate (at drop): {:0.4f}x'.format(
        0 if len(drop_events) == 0 else np.mean([x.rate for x in drop_events])))
    print ('Drop count: {}'.format(len(drop_events)))

    if save_file is not None:
        wavfile.write(save_file, OUTPUT_FS, processed_audio)


if __name__ == '__main__':
    main(**vars(get_args()))
