---
name: openrouter-images
description: Generate or edit raster/SVG images through OpenRouter's Images API, choosing the best image model for the job (concept art, sprites and icons with transparent background, posters and logos with readable text, photoreal references, seamless textures, pixel art, edits of an existing image with reference images), then look at the result and iterate. Use this whenever the user wants Claude to create, draw, render, generate, redraw, restyle or edit a picture, illustration, concept, mood board, texture, sprite, icon, logo, poster, cover, thumbnail, banner, avatar, mockup or any other image, in any language (e.g. "нарисуй", "сгенерируй картинку", "сделай концепт"), even if OpenRouter isn't mentioned. Not for charts, diagrams, UI built in code, or pure image transforms like resize/crop/convert.
---

# OpenRouter images

You can't draw, but you can call image models and then look at what they made. This skill covers
the whole loop: work out what the image is for, pick the model that is best at that, write a strong
prompt, generate, inspect the result with the Read tool, and iterate.

All API work goes through one stdlib-only script that prints JSON. Below it is written as
`gen <subcommand>`. In real commands, write out
`python3 <this skill's base directory>/scripts/gen_image.py <subcommand>` every time. A shell variable
such as `$gen` breaks because zsh doesn't word-split it and Bash calls don't share variables.

It needs `OPENROUTER_API_KEY` in the environment for `generate` and `balance`. `models`, `info`,
`check`, `sheet`, `pixelize`, `roll`, `seamless`, `merge-seam` and `generate --dry-run` work without a key. If the key is
missing, tell the user. Never go looking for it in files, keychains or other credential stores.

## 1. Work out the need

Before you pick a model, settle these from the request and its context, such as the project you're in
or earlier messages:

- **Purpose**: concept art, photoreal reference, text-heavy design (poster, sign, title card),
  vector logo or icon, transparent sprite or UI icon, edit of an existing image, tileable texture,
  stylized illustration, pixel art, or a batch of variants for a mood board.
- **Tier**: a quick draft to explore an idea, or a polished final. Drafts should cost about a cent;
  finals are worth 5–20 cents.
- **Format**: aspect ratio (what will it be used for?), resolution, transparent background, SVG.
- **Inputs**: reference images or an image to edit (local paths or URLs).

Decide on your own when the request makes these clear. Ask only when the answer would change the
model or multiply the cost. Good reasons to ask: "a logo" could be a vector mark or a raster
wordmark; "an icon" could be a transparent PNG sprite or an SVG; "a monster" could be a quick
sketch or a portfolio piece. Use the AskUserQuestion tool if it's available, with 1–2 concrete
options that each name a model and its approximate price. Don't ask about things that have a
sensible default:

- aspect 1:1, or whatever the use implies (16:9 for a key art banner, 9:16 for a phone wallpaper)
- one image, or 2–4 when the user is exploring
- a mid tier (Flare at `--quality medium`/`high`)

## 2. Pick the model

Read `references/models.md`. It has a "pick by need" table and short notes on each current model.
The catalog changes weekly, so confirm your pick still exists and supports the parameters you need:

```bash
gen models --search flare          # or: --edit, --transparent, --sort price, --long
gen info openai/gpt-image-2.5-flare  # params, enum values, per-provider pricing
```

If the pick is gone or a clearly better model has appeared, choose from the live list, then update
`references/models.md` so the next run benefits. Tell the user your choice in one line: the model,
why it fits, and the approximate price. For example: "Using GPT Image 2.5 Flare (best at game
concept art), about 5 cents."

## 3. Write the prompt

- Write the prompt in English, whatever language the user speaks. Most models follow English best.
- Describe the subject, setting, composition or camera, lighting, medium or style, mood and palette.
  For game assets, name the use: "top-down tileable floor texture", or "UI icon that reads at 64px
  with a strong silhouette".
- For text in the image, quote the exact words, give the font style and placement, keep the text
  short, and proofread it in the result.
- For edits, say what to change and also what must stay the same ("keep the face, outfit and pose
  unchanged; replace only the background with ...").
- For a transparent sprite, ask for an "isolated object, no background, no ground shadow", and pass
  `--background transparent`.
- Put long prompts in a file and pass them with `--prompt-file`, which avoids shell-quoting trouble.

## 4. Generate

```bash
gen generate --model <id> --prompt "<prompt>" --name <short-english-slug> \
  [--aspect 16:9] [--resolution 2K] [--quality high] [--background transparent] \
  [--n 4] [--ref path/or/url.png ...] [--format png|jpeg|webp|svg] [--seed 42]
```

Give each `generate` call a Bash timeout of 600000 ms. Generations take from a few seconds to two
minutes, and the default 2-minute timeout can kill the script after the image is paid for but before
it is saved. When you need several images, start the calls in parallel, as several Bash calls in one
message.

The script checks every parameter against the model's live capabilities before it spends any money,
and estimates the cost. Pass only the flags the model lists in `info`. For example, OpenAI models don't
list `output_format`, so `--format png` is rejected; they return PNG by default. Images land in `<project root>/generated-images/`, where the project root is
the git top level or else the current directory. Files are named `YYYYMMDD-HHMMSS-<slug>[-i].<ext>`,
and each image has a `.json` sidecar with the prompt, model, params and cost, so you can reproduce or
iterate on it later. Use `--out-dir` only when the user asks for another place. If the project is a
git repo that doesn't ignore `generated-images/`, mention it once; don't edit `.gitignore` unless asked.

Handle the `status` field in the output:

- `ok`: `files` lists the saved images, and `cost_usd` is the real charge.
- `needs_confirmation` (exit 3): the estimate is above the limit (25 cents per request by default;
  set it with `--max-cost` or `OPENROUTER_IMAGES_MAX_COST`), or the model has no listed price. Ask the
  user and show the estimate. Rerun with `--yes` only after the user approves. This guard exists
  because the user asked for it; never pass `--yes` without their approval. The limit applies per
  request. When you plan several requests at once, such as four poses as four calls or a set of
  finals, dry-run each one, add up the estimates, and ask once up front if the total is over the
  limit. Offer a cheaper path in the same question, for example drafts at `--quality low` first and
  finals only for the picks.
- `error` with `problems`: the parameters don't fit the model. Fix them using `supported_parameters`
  or pick another model.
- `error` with `http_status`: follow the `hint`. A 403 is moderation: rephrase once, or switch
  model. A 402 means credits ran out: tell the user. A timeout may still have been billed, so check
  `gen balance` before you retry. The script never resends a request that timed out.
- `empty`: usually a silent moderation refusal. Rephrase or switch model.

`--dry-run` shows the exact request, the cost estimate and where files would be saved, without
calling the API. Use it when you're unsure about parameters.

## 5. Look, then iterate

Open every generated image with the Read tool before you report back. You are the user's eyes on the
first pass. Check the subject, composition, anatomy and artifacts, the spelling of any text, and
whether the style matches the request.

- Several images: `gen sheet <files...>` builds one numbered contact sheet, with transparent areas
  shown over a checkerboard. Look at the sheet instead of opening each file; that is one image in
  context instead of many. Give the user its path so they can pick by number. Open a single image at
  full size only when details matter, such as text, faces or edges.
- Transparent assets: run `gen check <file>`. Many models paint a fake checkerboard or white
  background. If the verdict says the background is painted, switch to a transparent-capable model, or
  use the chroma-key fallback in `references/postprocess.md`.
- Textures: run `gen check <file> --tile`. It reports `wrap_seam_ratio` (above 2 means a visible seam)
  and writes a 2×2 preview. Models don't tile by themselves, even when asked for "seamless".
  - For irregular materials (concrete, rust, dirt, rock), `gen seamless <file>` fixes the seam for free.
  - For regular patterns (tiles, diamond plate, bricks), say up front that AI repair is unreliable.
    Follow the options in `references/postprocess.md`.
- Pixel art: `gen pixelize <file> --size 32 --colors 16` snaps the image to a true grid and palette,
  and writes an enlarged preview. Look at the preview.
- SVG output: the Read tool shows SVG as markup. To see the picture, rasterize it first with
  `qlmanage -t -s 1024 -o <dir> <file.svg>` on macOS.
- Assets for Unity: compressed texture formats need sizes that are multiples of 4, and OpenAI models
  sometimes return 1254 px squares. Offer a resized 1024 or 512 copy.

If the result misses, change the prompt (be more specific about what went wrong) or switch to a model
that is stronger at the failing aspect, then regenerate. After two misses on the same point, stop.
Show the user the best attempt and ask how to proceed rather than burning credits.

To iterate on a good image, pass it back with `--ref` and an edit prompt. That keeps the parts that
work, where a fresh generation would reroll everything.

## 6. Report

Keep it short:

- the file path(s), plus the contact sheet if you made one, as `path` so they're clickable
- the model used and the real cost
- one line on what you'd tweak next, if anything

Don't paste the JSON.
