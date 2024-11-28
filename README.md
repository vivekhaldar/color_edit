# Edit Videos Automatically Based on Color

It's a bit hard to explain, see [this video](https://youtu.be/Bdoi7BDhrWc) for an explanation.

# Invocation

Assuming your raw video is called `input.mp4`:

```
./edit_normalize input.mp4
```

This will leave an edited video in `input.edited.mp4`.

Then transcribe the video using

```
./transcribe.sh input.edited.mp4
```
