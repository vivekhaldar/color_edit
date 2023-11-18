#!/bin/bash
#
# Transcribe a video file.

# First argument is raw video file.
input_file="$1"


whisper --model_dir `pwd` --output_dir `pwd` --output_format srt --task transcribe $1
