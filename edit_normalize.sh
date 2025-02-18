# Edit a video file and normalize the audio.

# First argument is raw video file.
input_file="$1"

# Check if there is a 2nd argument. If so, it is the volume threshold.

# For desktop mic (FiFine)
volume_threshold=0.002

# For DJI Mic 2
# volume_threshold=0.02
if [ -n "$2" ]; then
    volume_threshold="$2"
fi
# Construct output file name
output_file="${input_file%.*}.edited.${input_file##*.}"

./color_edit.py --input $input_file --output $output_file --volume_threshold $volume_threshold

# Using ffmpeg command line, find the max volume in output file and store it in a variable.
max_volume=$(ffmpeg -i $output_file -af "volumedetect"  -vn -sn -dn -f null /dev/null 2>&1 | grep "max_volume" | awk '{print $5}')
echo "=========> Max volume: $max_volume"
mean_volume=$(ffmpeg -i $output_file -af "volumedetect"  -vn -sn -dn -f null /dev/null 2>&1 | grep "mean_volume" | awk '{print $5}')
echo "=========> Mean volume: $mean_volume"
