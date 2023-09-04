from moviepy.editor import *
from moviepy.audio.AudioClip import AudioClip
import numpy as np
import os
import pytest

from color_edit import color_edit, find_speaking


DEFAULT_WIDTH = 1920
DEFAULT_HEIGHT = 1080

# Common colors.
WHITE = (255, 255, 255)
GREEN = (0, 255, 0)
BLUE = (0, 0, 255)
RED = (255, 0, 0)


# Take a list of (color, duration) tuples and generate a video.
def generate_color_sequence_video(color_sequence, size=(DEFAULT_WIDTH, DEFAULT_HEIGHT)):
    clips = []
    for color, duration in color_sequence:
        clips.append(ColorClip(size=size, color=color, duration=duration))
    return concatenate_videoclips(clips)

# Convenience routine for writing a video to a file, with all its messy params.
def write_video_to_file(video, filename):
    video.write_videofile(filename,
        fps=30,
        preset='ultrafast',
        codec='libx264',
        #codec='h264_videotoolbox',
        temp_audiofile='temp-audio.m4a',
        remove_temp=True,
        audio_codec="aac",
        #threads=6,
        ffmpeg_params = ['-threads', '8'],
    )

# Rough comparison of two videos.
# Returns 'True' if the two videos are /rougly/ the same.
def videos_approximately_same(video_file1, video_file2):
    # Load the videos
    clip1 = VideoFileClip(video_file1)
    clip2 = VideoFileClip(video_file2)

    duration1 = clip1.duration
    duration2 = clip2.duration

    print('Duration difference: ' + str(abs(duration1 - duration2)))
    print('Duration difference %: ' + str(abs(duration1 - duration2)/100))

    # Compare difference of durations. 1% diff is OK.
    if abs(duration1 - duration2)/100 > 0.01:
        return False

    min_duration = min(duration1, duration2)

    # Compare the frames of the videos
    diff_frames = 0   # Count of frames that differ.
    for t in range(int(min_duration * clip1.fps)):
        frame1 = clip1.get_frame(t / clip1.fps)
        frame2 = clip2.get_frame(t / clip2.fps)
        # Look at a small 5x5 square of the frame.
        diff_pixels = 0
        for x in range(5):
            for y in range(5):
                f1 = frame1[x][y]
                f2 = frame2[x][y]
                color_diff = np.abs(np.subtract(f1, f2, dtype=np.int8))
                if sum(color_diff) > 10:
                    diff_pixels += 1
        if diff_pixels > 0:
            diff_frames += 1

    # Calculate fraction of frames that differ.
    print('Number of differing frames: ' + str(diff_frames) + ' out of ' + str(min_duration * clip1.fps) + ' total frames.')
    diff_fraction = diff_frames / (min_duration * clip1.fps)
    if diff_fraction > 0.01:
        return False

    return True


# Fixture to create the input and expected output videos
@pytest.fixture
def setup_test_data():
    test_input_file = 'test_color_edit_input_video.mp4'
    expected_output_file = 'expected_color_edit_output_video.mp4'

    # Create a video with a sequence of colors.
    test_color_sequence = [
        (WHITE, 1),
        (GREEN, 2),  # Keep WHITE, 1
        (BLUE, 3),
        (RED, 1),    # Drop BLUE, 3
        (BLUE, 2),
        (GREEN, 3),  # Keep BLUE, 2
        (WHITE, 3)   # Keep WHITE, 3
    ]
    expected_color_sequence = [
        (WHITE, 1),
        (BLUE, 2),
        (WHITE, 3)
    ]

    test_input_video = generate_color_sequence_video(test_color_sequence)
    expected_output_video = generate_color_sequence_video(expected_color_sequence)
    
    write_video_to_file(test_input_video, test_input_file)
    write_video_to_file(expected_output_video, expected_output_file)

    yield test_input_file, expected_output_file

    os.remove(test_input_file)
    os.remove(expected_output_file)

# Test function
def test_color_edit(setup_test_data):
    test_input_file, expected_output_file = setup_test_data

    vid = VideoFileClip(test_input_file)
    color_edited_video, color_intervals = color_edit(vid)
    
    test_output_file = 'test_color_edit_output_video.mp4'
    write_video_to_file(color_edited_video, test_output_file)

    # Compare the two video files approximately.
    assert videos_approximately_same(test_output_file, expected_output_file)

    os.remove(test_output_file)

# Test find_speaking.
GOLDEN_INPUT_FILE = 'golden/input_with_silence_lores.mp4'
GOLDEN_OUTPUT_FILE = 'golden/output_nosilence_lores.mp4'
TEST_OUTPUT_FILE = 'test_find_speaking_output_video.mp4'

# This is the pytest test function.
def test_find_speaking():
    vid = VideoFileClip(GOLDEN_INPUT_FILE)
    no_dead_air_video, speaking_intervals = find_speaking(vid, vid.audio.fps)
    write_video_to_file(no_dead_air_video, TEST_OUTPUT_FILE)

    # Use assert keyword instead of self.assertTrue
    assert videos_approximately_same(GOLDEN_OUTPUT_FILE, TEST_OUTPUT_FILE)

    os.remove(TEST_OUTPUT_FILE)

