# Generate test video for the project.
# Don't want to check in the actual video, which would be huge.

from moviepy.editor import *
from moviepy.audio.AudioClip import AudioClip
import numpy as np
import os
import unittest

from color_edit import color_edit, find_speaking

DEFAULT_WIDTH = 1920
DEFAULT_HEIGHT = 1080

# Common colors.
RED = (255, 0, 0)
GREEN = (0, 255, 0)
BLUE = (0, 0, 255)
WHITE = (255, 255, 255)

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

# Unit test for color editing.
# Note that this only tests color editing, not removing silence.
class TestColorEdit(unittest.TestCase):
    TEST_INPUT_FILE = 'test_color_edit_input_video.mp4'
    TEST_OUTPUT_FILE = 'test_color_edit_output_video.mp4'
    EXPECTED_OUTPUT_FILE = 'expected_color_edit_output_video.mp4'

    def _create_test_input_video(self):
        # Create a video with a sequence of colors.
        color_sequence = [
            (WHITE, 1),
            (GREEN, 2),  # Keep WHITE, 1
            (BLUE, 3),
            (RED, 1),    # Drop BLUE, 3
            (BLUE, 2),
            (GREEN, 3),  # Keep BLUE, 2
            (WHITE, 3)   # Keep WHITE, 3
        ]
        test_input_video = generate_color_sequence_video(color_sequence)
        write_video_to_file(test_input_video, self.TEST_INPUT_FILE)
    
    def _create_expected_output_video(self):
        # Create a video with a sequence of colors.
        color_sequence = [
            (WHITE, 1),
            (BLUE, 2),
            (WHITE, 3)
        ]
        expected_output_video = generate_color_sequence_video(color_sequence)
        write_video_to_file(expected_output_video, self.EXPECTED_OUTPUT_FILE)

    def setUp(self) -> None:
        self._create_test_input_video()
        self._create_expected_output_video()

    def test_color_edit(self):
        vid = VideoFileClip(self.TEST_INPUT_FILE)
        color_edited_video, color_intervals = color_edit(vid)
        write_video_to_file(color_edited_video, self.TEST_OUTPUT_FILE)

        # Compare the two video files approximately.
        self.assertTrue(videos_approximately_same(self.TEST_OUTPUT_FILE, self.EXPECTED_OUTPUT_FILE))


    def tearDown(self) -> None:
        os.remove(self.TEST_INPUT_FILE)
        os.remove(self.TEST_OUTPUT_FILE)
        os.remove(self.EXPECTED_OUTPUT_FILE)


# Unit test for finding speaking intervals.
class TestFindSpeaking(unittest.TestCase):
    GOLDEN_INPUT_FILE = 'golden_input_with_silence_lores.mp4'
    GOLDEN_OUTPUT_FILE = 'golden_output_nosilence_lores.mp4'
    TEST_OUTPUT_FILE = 'test_find_speaking_output_video.mp4'

    def test_find_speaking(self):
        vid = VideoFileClip(self.GOLDEN_INPUT_FILE)
        no_dead_air_video, speaking_intervals = find_speaking(vid, vid.audio.fps)
        write_video_to_file(no_dead_air_video, self.TEST_OUTPUT_FILE)

        # Compare the two video files approximately.
        self.assertTrue(videos_approximately_same(self.GOLDEN_OUTPUT_FILE, self.TEST_OUTPUT_FILE))

    def tearDown(self) -> None:
        os.remove(self.TEST_OUTPUT_FILE)


if __name__ == '__main__':
    unittest.main()