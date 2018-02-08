#!/usr/bin/env python3

import argparse
import numpy as np
from scipy.io import wavfile


def get_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('file', type=str, help='File to play')
    return parser.parse_args()


def main(args):
    if not args.file.endswith('.wav'):
        print('Warning: only wav is supported')

    sample_rate, data = wavfile.read(args.file)

    print(sample_rate)
    print(data)
    print('Max', max(data))
    print('Min', min(data))
    print('Mean', np.mean(data))
    print('Median', np.median(data))


if __name__ == '__main__':
    main(get_args())
