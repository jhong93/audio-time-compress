#!/bin/bash

infile=$1
outfile="${infile%.*}.wav"

ffmpeg -i $infile $outfile
