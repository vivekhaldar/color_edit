# Edit a video file and normalize the audio.

# First argument is raw video file.
input_file="$1"

# Construct output file name
output_file="${input_file%.*}.edited.${input_file##*.}"

./color_edit.py --input $input_file --output $output_file

# Using ffmpeg command line, find the max volume in output file and store it in a variable.
max_volume=$(ffmpeg -i $output_file -af "volumedetect"  -vn -sn -dn -f null /dev/null 2>&1 | grep "max_volume" | awk '{print $5}')
echo "=========> Max volume: $max_volume"
mean_volume=$(ffmpeg -i $output_file -af "volumedetect"  -vn -sn -dn -f null /dev/null 2>&1 | grep "mean_volume" | awk '{print $5}')
echo "=========> Mean volume: $mean_volume"

# Construct filename of normalized output file.
normalized_output_file="${input_file%.*}.normalized.${input_file##*.}"

# Using ffmpeg command line, normalize the audio in the output file.
ffmpeg -i $output_file -af "speechnorm=e=12.5:r=0.0001:l=1" $normalized_output_file

echo "=======> Volumes after normalization"
max_volume=$(ffmpeg -i $normalized_output_file -af "volumedetect"  -vn -sn -dn -f null /dev/null 2>&1 | grep "max_volume" | awk '{print $5}')
echo "=========> Max volume: $max_volume"
mean_volume=$(ffmpeg -i $normalized_output_file -af "volumedetect"  -vn -sn -dn -f null /dev/null 2>&1 | grep "mean_volume" | awk '{print $5}')
echo "=========> Mean volume: $mean_volume"
