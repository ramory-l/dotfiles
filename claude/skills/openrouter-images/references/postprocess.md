# Post-processing recipes

Image models have no setting for tiling, grid-true pixels or guaranteed alpha, so these steps happen
after generation. The `gen` subcommands below need Pillow (`python3 -c "import PIL"`). If Pillow is
missing, ask before installing it. Every step writes a new file next to the original and leaves the
original untouched.

## Seamless texture: check and fix seams

Models don't tile by themselves, even when the prompt says "seamless". The 2026-10-18 calibration
texture had a seam ratio of about 3, so plan a fix every time.

1. Check: `gen check <file> --tile` reports `wrap_seam_ratio` (1 means the jump at the wrap looks
   like any other pixel step; above 2 the seam is visible) and writes `<stem>.tile2x2.png`. Look at the
   preview too, because the ratio can't see doubled or repeating shapes.
2. Irregular materials (concrete, rust, grime, dirt, rock, grass): `gen seamless <file>` cross-fades the
   texture with its half-rolled copy. It is free and local, and the calibration texture went from seam
   ratio 3.2 to 0.8. Re-run `check --tile`. A large blotch that now repeats can show up; if it does,
   regenerate with "fine, evenly distributed detail, no large features".
3. Regular patterns (tiles, diamond plate, bricks, grates): this is the hard case, so say so up front.
   - `seamless` removes the seam but leaves faded doubled shapes in the blend zones. That can be fine
     for a floor seen from a distance; show the user a close crop and let them decide.
   - Edit models don't reliably repair the cross. In calibration, FLUX 3 Klein returned the image almost
     unchanged, and Nano Banana 2.1 only softened it (ratio 3.21 → 2.29). If you try one anyway: run
     `gen roll <file>`, then an edit of the rolled image that asks to repaint the strips along the center
     cross (don't add "change nothing else", which makes models do nothing), then
     `gen merge-seam <rolled> <repaired>`. It pastes only the cross band and reports whether the seam
     ratio improved. Finish with `gen roll <merged> --back` and `check --tile`. Make one attempt at most.
   - The reliable route: build the regular pattern procedurally (a Unity Shader Graph or material),
     and use a generated irregular rust or grime layer made tileable with `gen seamless`.

## Pixel art: snap to a grid and palette

Generate at 1K with a prompt like "pixel art sprite, 32x32 grid, limited 16-color palette, crisp square
pixels, 1-px dark outline, no anti-aliasing, no gradients, isolated on a transparent background" and
`--background transparent`. Then run:

```
gen pixelize <file> --size 32 --colors 16
```

It writes the true 32×32 sprite (alpha forced to 0 or 255, transparent pixels don't use palette
slots) and an 8× nearest-neighbor preview. Look at the preview, not the tiny file. If the model's grid
didn't land on 32, the result looks smeared. Regenerate with a stronger grid instruction instead of
fiddling with the downscale.

## Fake transparency: chroma-key fallback

If `gen check` says the background is painted and you can't switch to a transparent-capable model,
regenerate with "on a perfectly flat solid #FF00FF magenta background, no shadows" and key it out:

```python
from PIL import Image, ImageChops
img = Image.open(src).convert("RGBA")
r, g, b, a = img.split()
key = ImageChops.multiply(ImageChops.multiply(r.point(lambda v: 255 if v > 200 else 0),
                                              g.point(lambda v: 255 if v < 80 else 0)),
                          b.point(lambda v: 255 if v > 200 else 0))   # 255 where the pixel is magenta
img.putalpha(ImageChops.subtract(a, key)); img.save(dst)
```

Check the edges at 2–4× zoom. A magenta fringe means the threshold needs tuning.
