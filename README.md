# gif_speed

Change speed of animated GIFs without rerendering, so the quality doesn't deteriorate. Modifies only the frame delay bytes.

Only tested against Photoshop GIFs.

Requires Python 3.7+.

```shell
python3 -m gif_speed <path to gif> <speed modifier> [<specials>]
```

* `<speed modifier>`: absolute frame delay value, e.g. `0.07`, or speed factor, e.g. `2x` (=twice as fast). Applied to all frames.
* `<specials>`: comma-separated list of `<frame index>:<speed modifier>` to give specific frames different speeds.
  Frame index starts at 1. For example, to set 1st frame to 0.5s delay and 37th frame to twice the speed: `1:0.5,37:2x`.

References:

* <https://en.wikipedia.org/wiki/GIF#Animated_GIF>
* <https://archimedespalimpsest.net/Documents/External/XMP/XMPSpecificationPart3.pdf>
