#!/usr/bin/env python3
import math
import random
import os
import argparse
from enum import Enum
from moviepy import VideoFileClip, concatenate_videoclips
from timeit import default_timer as timer
from datetime import timedelta
import numpy as np


# Given a timestamp in seconds, convert to a string in the format HH:MM:SS:FF
def seconds_to_ts(seconds, fps):
    hours = math.floor(seconds / 3600)
    minutes = math.floor((seconds - (hours * 3600)) / 60)
    secs = math.floor(seconds - (hours * 3600) - (minutes * 60))
    frames = math.floor((seconds - math.floor(seconds)) * fps)
    return "{:02d}:{:02d}:{:02d}:{:02d}".format(hours, minutes, secs, frames)


# Export an EDL file given a list of (start, end) time intervals.
def export_edl(intervals, clip_filename, edl_filename, fps):
    print("Exporting EDL file: {}".format(edl_filename))
    with open(edl_filename, "w") as f:
        f.write("TITLE: Timeline 1\n")
        f.write("FCM: NON-DROP FRAME\n")
        timeline_seconds = 60 * 60  # Davinci timeline starts at 1 hr.
        for i, interval in enumerate(intervals):
            start = interval[0]
            end = interval[1]
            duration = end - start
            timeline_start = timeline_seconds
            timeline_end = timeline_seconds + duration
            timeline_seconds = timeline_end
            f.write(
                "{:03d}  AX       V     C        {} {}  {}  {}\n".format(
                    i + 1,
                    seconds_to_ts(start, fps),
                    seconds_to_ts(end, fps),
                    seconds_to_ts(timeline_start, fps),
                    seconds_to_ts(timeline_end, fps),
                )
            )
            f.write("* FROM CLIP NAME: {}\n".format(clip_filename))


# https://chat.openai.com/share/315085b3-d75a-41eb-85c4-57ecfd14fd94
# Get average RGB of n random pixels in a frame.
def sample_average_color(frame, n):
    height, width, _ = frame.shape
    random_coords = [
        (random.randint(0, height - 1), random.randint(0, width - 1)) for _ in range(n)
    ]

    sampled_pixels = np.array([frame[y, x] for y, x in random_coords])
    average_color = np.mean(sampled_pixels, axis=0)

    return average_color


# The following refactor was suggested by ChatGPT (GPT-4)
# https://chat.openai.com/share/53b0cbe4-c651-4cd8-904f-a938593f7662


# Enum to label each frame. 'c': content; 'y': keep prior interval; 'n': drop prior interval.
class FrameMarker(Enum):
    CONTENT = 1
    KEEP = 2
    DROP = 3


def color_edit_intervals(video):
    frame_markers = [
        get_frame_marker(sample_average_color(frame, 10))
        for frame in video.iter_frames()
    ]

    return extract_intervals(frame_markers, video.fps)


def get_frame_marker(avg_colors):
    avg_r, avg_g, avg_b = avg_colors
    is_red = avg_r > 120 and avg_g < 50 and avg_b < 50
    is_green = avg_r < 80 and avg_g > 120 and avg_b < 50

    if is_red:
        return FrameMarker.DROP
    elif is_green:
        return FrameMarker.KEEP
    else:
        return FrameMarker.CONTENT


def extract_intervals(frame_markers, fps):
    keep_intervals = []
    start_of_last_green = keep_start = keep_end = 0

    for i, (prev_marker, curr_marker) in enumerate(
        zip(frame_markers, frame_markers[1:])
    ):
        if prev_marker == FrameMarker.CONTENT and curr_marker == FrameMarker.KEEP:
            start_of_last_green = i

        if prev_marker == FrameMarker.KEEP and curr_marker == FrameMarker.CONTENT:
            keep_end = start_of_last_green / fps
            keep_intervals.append([keep_start, keep_end])
            keep_start = (i + 1) / fps

        if prev_marker == FrameMarker.DROP and curr_marker == FrameMarker.CONTENT:
            keep_start = i / fps

    if frame_markers[-1] in {FrameMarker.CONTENT, FrameMarker.KEEP}:
        keep_end = i / fps
        keep_intervals.append([keep_start, keep_end])

    return keep_intervals


def color_edit(vid_file_clip):
    print("---- Looking for color coded editing clips... -----")

    start = timer()
    intervals_to_keep = color_edit_intervals(vid_file_clip)
    print("Keeping color edit intervals: " + str(intervals_to_keep))
    keep_clips = [
        vid_file_clip.subclipped(start, end) for [start, end] in intervals_to_keep
    ]
    color_edited_video = concatenate_videoclips(keep_clips)
    end = timer()

    color_edit_time = timedelta(seconds=end - start)
    print("Color edit time: " + str(color_edit_time))

    return color_edited_video, intervals_to_keep


# Note: following refactor was suggested by ChatGPT (GPT-4)
# https://chat.openai.com/share/b5a78779-2d97-4526-82d2-69afa05ab43b


# Iterate over audio to find the non-silent parts. Outputs a list of
# (speaking_start, speaking_end) intervals.
# Args:
#  window_size: (in seconds) hunt for silence in windows of this size
#  volume_threshold: volume below this threshold is considered to be silence
#  ease_in: (in seconds) add this much silence around speaking intervals
def find_speaking_intervals(
    audio_clip, window_size=0.1, volume_threshold=0.005, ease_in=0.1, audio_fps=44100
):
    num_windows = math.floor(audio_clip.end / window_size)

    # Find silent windows using list comprehension
    window_is_silent = [
        audio_clip.subclipped(i * window_size, (i + 1) * window_size)
        .with_fps(audio_fps)
        .max_volume()
        < volume_threshold
        for i in range(num_windows)
    ]

    speaking_intervals = []
    speaking_start = 0

    # Iterate over adjacent elements using zip
    for i, (e1, e2) in enumerate(zip(window_is_silent[:-1], window_is_silent[1:])):
        # silence -> speaking
        if e1 and not e2:
            speaking_start = (i + 1) * window_size
        # speaking -> silence, now have a speaking interval
        if not e1 and e2:
            speaking_end = (i + 1) * window_size
            new_interval = [max(0, speaking_start - ease_in), speaking_end + ease_in]
            # With tiny windows, this can sometimes overlap the previous window, so merge.
            if speaking_intervals and speaking_intervals[-1][1] > new_interval[0]:
                speaking_intervals[-1][1] = new_interval[1]
            else:
                speaking_intervals.append(new_interval)

    return speaking_intervals


def find_speaking(input_clip, input_audio_fps, volume_threshold=0.005, window_size=0.1):
    print("\n\n\n----- Now cutting out dead air... -----")

    start = timer()
    speaking_intervals = find_speaking_intervals(
        input_clip.audio, volume_threshold=volume_threshold, audio_fps=input_audio_fps, window_size=window_size
    )
    print("Keeping speaking intervals: " + str(speaking_intervals))
    speaking_clips = [
        input_clip.subclipped(start, end) for [start, end] in speaking_intervals
    ]
    final_video = concatenate_videoclips(speaking_clips)
    end = timer()

    speaking_detection_time = timedelta(seconds=end - start)
    print("Speaking detection time: " + str(speaking_detection_time))

    return final_video, speaking_intervals


def main():
    # Create the parser
    parser = argparse.ArgumentParser(description="Process a video file.")

    # Add the arguments
    parser.add_argument(
        "--input", metavar="input", type=str, help="the path to the input file"
    )
    parser.add_argument(
        "--output", metavar="output", type=str, help="the path to the output file"
    )
    parser.add_argument(
        "--volume_threshold",
        metavar="volume_threshold",
        type=float,
        help="volume threshold for silence detection",
        default=0.005,
    )

    # Color edit.
    parser.add_argument(
        "--skip_color_edit",
        action="store_true",
        default=False,
        help="skip color editing",
    )

    parser.add_argument(
        "--window_size",
        metavar="window_size",
        type=float,
        help="window size (in seconds) for silence detection",
        default=0.1,
    )


    # Parse the arguments
    args = parser.parse_args()

    # Input file path
    file_in = args.input
    # Output file path
    file_out = args.output
    # Volume threshold for silence detection
    volume_threshold = args.volume_threshold
    window_size = args.window_size

    vid = VideoFileClip(file_in)

    skip_color_edit = args.skip_color_edit

    if not skip_color_edit:
        color_edited_video, color_intervals = color_edit(vid)
    else:
        print("Skipping color editing...")
        color_edited_video = vid
        color_intervals = []

    # Cut out dead air.
    no_dead_air_video, speaking_intervals = find_speaking(
        color_edited_video, vid.audio.fps, volume_threshold=volume_threshold, window_size=window_size
    )

    # Write out EDL files with intervals.
    clip_name = os.path.split(file_in)[-1]
    clip_dir = os.path.dirname(file_in)
    color_edl = os.path.join(clip_dir, clip_name + ".color.edl")
    speaking_edl = os.path.join(clip_dir, clip_name + ".speaking.edl")
    export_edl(color_intervals, clip_name, color_edl, fps=vid.fps)
    # The below will not work, because it should be emitting timestamps relative
    # to the color-edited video, but doesn't.
    # export_edl(speaking_intervals, clip_name, speaking_edl)

    print("\n\n\n----- Writing out edited video... -----")
    start = timer()
    no_dead_air_video.write_videofile(
        file_out,
        # fps=60,
        preset="ultrafast",
        codec="libx264",
        # codec='h264_videotoolbox',
        temp_audiofile="temp-audio.m4a",
        remove_temp=True,
        audio_codec="aac",
        # threads=6,
        ffmpeg_params=["-threads", "8"],
    )
    vid.close()
    end = timer()

    render_time = timedelta(seconds=end - start)
    print("Render time: " + str(render_time))


if __name__ == "__main__":
    main()
