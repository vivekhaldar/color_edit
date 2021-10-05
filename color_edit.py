#!/usr/bin/env python3
import math
import sys
from typing import Tuple
from moviepy.editor import AudioClip, VideoFileClip, concatenate_videoclips

# Get average RGB of part of a frame. Frame is H * W * 3 (rgb)
# Assumes x1 < x2, y1 < y2
def avg_rgb(frame, x1: int, y1: int, x2: int, y2: int) -> Tuple[float, float, float]:
    r, g, b = 0, 0, 0
    for x in range(x1, x2):
        for y in range(y1, y2):
            r += frame[x, y, 0]
            g += frame[x, y, 1]
            b += frame[x, y, 2]
    total_pixels = (x2 - x1) * (y2 - y1)
    avg_r = r / total_pixels
    avg_g = g / total_pixels
    avg_b = b / total_pixels
    return avg_r, avg_g, avg_b

# Look for colors in frame, edit based on that.
# Returns list of (start, end) tuples of time intervals we want to keep.
def color_edit_intervals(video):
    intervals_to_keep = []
    frame_marker = [] # 'c': content; 'y': keep prior interval; 'n': drop prior interval.
    # Iterate over every frame.
    for frame in video.iter_frames():
        avg_r, avg_g, avg_b = avg_rgb(frame, 100, 100, 110, 110)
        is_red = (avg_r > 120) and (avg_g < 50) and (avg_b < 50)
        is_green = (avg_r < 80) and (avg_g > 120) and (avg_b < 50)
        marker = 'c'
        if is_red:
            marker = 'n'
        elif is_green:
            marker = 'y'
        frame_marker.append(marker)

    keep_start, keep_end = 0, 0
    keep_intervals = []
    start_of_last_green = 0
    for i in range(1, len(frame_marker)):
        m1 = frame_marker[i - 1]
        m2 = frame_marker[i]
        # Content followed by green, take note.
        if m1 == 'c' and m2 == 'y':
            start_of_last_green = i
        # Green followed by content. Keep previous interval. Start a (possible) new interval.
        if m1 == 'y' and m2 == 'c':
            keep_end = start_of_last_green / video.fps
            keep_intervals.append([keep_start, keep_end])
            keep_start = (i + 1) / video.fps
        # Red followed by content. Drop the previous interval. Start a (possible) new interval.
        if m1 == 'n' and m2 == 'c':
            keep_start = i / video.fps
    
    # Ending on green with no following content.
    last_index = len(frame_marker) - 1
    if frame_marker[last_index] == 'c' or frame_marker[last_index] == 'y':
        keep_end = i / video.fps
        keep_intervals.append([keep_start, keep_end])

    return keep_intervals

def color_edit(vid_file_clip):
    print("---- Looking for color coded editing clips... -----")
    intervals_to_keep = color_edit_intervals(vid_file_clip)
    print("Keeping color edit intervals: " + str(intervals_to_keep))
    keep_clips = [vid_file_clip.subclip(start, end) for [start, end] in intervals_to_keep]
    color_edited_video = concatenate_videoclips(keep_clips)
    return color_edited_video  
# Iterate over audio to find the non-silent parts. Outputs a list of
# (speaking_start, speaking_end) intervals.
# Args:
#  window_size: (in seconds) hunt for silence in windows of this size
#  volume_threshold: volume below this threshold is considered to be silence
#  ease_in: (in seconds) add this much silence around speaking intervals
def find_speaking_intervals(audio_clip, window_size=0.1, volume_threshold=0.05, ease_in=0.1, audio_fps=44100):
    # First, iterate over audio to find all silent windows.
    num_windows = math.floor(audio_clip.end/window_size)
    window_is_silent = []
    for i in range(num_windows):
        s = audio_clip.subclip(i * window_size, (i + 1) * window_size).set_fps(audio_fps)
        v = s.max_volume()
        window_is_silent.append(v < volume_threshold)

    # Find speaking intervals.
    speaking_start = 0
    speaking_end = 0
    speaking_intervals = []
    for i in range(1, len(window_is_silent)):
        e1 = window_is_silent[i - 1]
        e2 = window_is_silent[i]
        # silence -> speaking
        if e1 and not e2:
            speaking_start = i * window_size
        # speaking -> silence, now have a speaking interval
        if not e1 and e2:
            speaking_end = i * window_size
            new_speaking_interval = [max(0, speaking_start - ease_in), speaking_end + ease_in]
            # With tiny windows, this can sometimes overlap the previous window, so merge.
            need_to_merge = len(speaking_intervals) > 0 and speaking_intervals[-1][1] > new_speaking_interval[0]
            if need_to_merge:
                merged_interval = [speaking_intervals[-1][0], new_speaking_interval[1]]
                speaking_intervals[-1] = merged_interval
            else:
                speaking_intervals.append(new_speaking_interval)

    return speaking_intervals

def find_speaking(input_clip, input_audio_fps):
    print("\n\n\n----- Now cutting out dead air... -----")
    speaking_intervals = find_speaking_intervals(input_clip.audio, audio_fps=input_audio_fps)
    print("Keeping speaking intervals: " + str(speaking_intervals))
    speaking_clips = [input_clip.subclip(start, end) for [start, end] in speaking_intervals]
    final_video = concatenate_videoclips(speaking_clips)
    return final_video  

def main():
    # Parse args
    # Input file path
    file_in = sys.argv[1]
    # Output file path
    file_out = sys.argv[2]

    vid = VideoFileClip(file_in)

    # Color edit.
    color_edited_video = color_edit(vid)

    # Cut out dead air.
    no_dead_air_video = find_speaking(color_edited_video, vid.audio.fps)

    print("\n\n\n----- Writing out edited video... -----")
    no_dead_air_video.write_videofile(file_out,
        #fps=60,
        preset='ultrafast',
        codec='libx264',
        temp_audiofile='temp-audio.m4a',
        remove_temp=True,
        audio_codec="aac",
        threads=6
    )

    vid.close()

if __name__ == '__main__':
    main()
