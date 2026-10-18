# Picking an image model (snapshot 2026-10-17)

Rankings come from the Artificial Analysis (AA) text-to-image and editing arenas and from LMArena (LMA)
as of the snapshot date. The catalog changes weekly: five notable models shipped in the two weeks before
this snapshot. Treat this file as a starting point, and confirm a pick is still listed with
`gen models --search <name>` before using it. If a better or newer model shows up in
`gen models --sort price --long`, use it and update this file.

Prices are for one ~1K image. Token-priced models (OpenAI, Google, Microsoft, Tencent) are estimates;
the real charge is `cost_usd` in the script output.

## Pick by need

| Need | First choice | Also good | Cheap fallback |
|---|---|---|---|
| Fast cheap draft / exploring ideas | `microsoft/mai-image-2.6-flash` (~$0.02; AA top-10, edit #5) | `openai/gpt-image-2.5-flare --quality low` (~$0.006): same model as the final, so the look carries over when you raise quality | `black-forest-labs/flux-3-image-klein` ($0.009), `recraft/recraft-v4.1-flash` ($0.007, ~1.5 s, text-only) |
| Concept art: environments, characters, creatures, mood | `openai/gpt-image-2.5-flare --quality high` (~$0.05; AA's #1 for games and concept art) | `openai/gpt-image-2.5-sunburst` at `xhigh`/`max` for hero shots (#1 overall, finest detail) | `google/gemini-nano-banana-2.1` (~$0.034, AA #4); `krea/krea-2-large` (~$0.06) for a rawer, grittier, painterly look that suits horror |
| Photoreal reference | `openai/gpt-image-2.5-sunburst` (LMA photoreal #1) | `google/gemini-nano-banana-2.1` (photoreal #4, far cheaper) | `microsoft/mai-image-2.6` (~$0.04), `bytedance-seed/seedream-5-0-flash` ($0.018). Avoid FLUX 3: photoreal is its weak spot |
| Readable text: posters, title cards, signage, UI mockups | `openai/gpt-image-2.5-flare` or `-sunburst` (top of the LMA text board) | `qwen/qwen-image-3-pro` (~$0.04): dense layouts, text down to ~10px, multilingual | `qwen/qwen-image-3` ($0.03); `bytedance-seed/seedream-5-0-pro` for multilingual posters |
| Logo mark / scalable icon (vector) | `recraft/recraft-v4.1-vector` (real SVG, $0.08) | `recraft/recraft-v4-styles-vector` + one reference icon to lock a set's style | — . Recraft garbles words, so keep text out of it and add the wordmark separately |
| Sprite / UI icon on transparent background (raster) | `openai/gpt-image-2.5-flare --background transparent` | `sourceful/riverflow-v2.5-pro` (transparent, $0.13) | `openai/gpt-image-1-mini --background transparent` (~$0.01, weak quality). Always run `gen check` afterwards |
| Edit an image / keep a character consistent across shots | `openai/gpt-image-2.5-sunburst` (AA edit #1, up to 16 refs) | `google/gemini-nano-banana-2.1` (edit #3, 14 refs); `black-forest-labs/flux-3-image` when everything outside the edit must stay pixel-identical | `microsoft/mai-image-2.6-flash` (~$0.02), `flux-3-image-klein` ($0.009, 10 refs), `krea/k3-edit` (edit-only, $0.03, under 8 s) |
| Seamless / tileable texture | `openai/gpt-image-2.5-flare --aspect 1:1` | `bytedance-seed/seedream-5-0-lite` (2K/4K, up to 14 style refs) | `flux-3-image-klein --resolution 2K` ($0.014). No model has a tiling switch: check seams with `gen check --tile` (see postprocess.md) |
| Stylized illustration | `openai/gpt-image-2.5-flare` (LMA art board #1) | `google/gemini-3-pro-image` (holds a given art style well, ~$0.13), `gemini-nano-banana-2.1` | `krea/krea-2-medium` (~$0.03; anime, painting); `recraft/recraft-v4-styles` + a reference to keep a whole set in one style |
| Pixel art | `openai/gpt-image-2.5-flare --background transparent` | `recraft/recraft-v4-styles` with a pixel-art reference | `krea/krea-2-medium-turbo`. No model outputs grid-true pixels: downscale and quantize afterwards (postprocess.md) |
| Many variants in one call (mood board) | `openai/gpt-image-2.5-flare --n 4` (n up to 10) | `bytedance-seed/seedream-4.5` (n up to 10, $0.04 each) | `qwen/qwen-image-2.1-turbo` (n up to 6, $0.018 each) |

Most models only allow `n=1`; to get variants from them, run the command several times.

Cyrillic text inside the image works with `openai/gpt-image-2.5-flare --quality medium`. It was
verified letter-perfect on a two-line Russian poster for $0.011. `qwen/qwen-image-3-pro` was also
correct, but cost $0.04 and took 3× longer. Still proofread every letter.

Output size: OpenAI models expose no `resolution` param on OpenRouter. Observed sizes: 1:1 gives
1024² at medium and 1254² at low; 2:3 gives 1024×1536; 16:9 gives 1536×864. When the user needs an
exact 2K/4K output, pick a model whose `resolution` enum has it, such as `gemini-nano-banana-2.1`,
`flux-3-image(-klein)` or `seedream-5-0-*` (Seedream returns JPEG), or say that you'll upscale.

## Current models worth knowing

- **OpenAI GPT Image 2.5** (`-flare`, `-sunburst`): quality `low`…`max`, `n` up to 10, 16 refs,
  native transparency. Flare is faster and the everyday default; Sunburst keeps finer detail and is the
  strongest editor. Cost climbs steeply from `high` to `xhigh` and `max`.
- **`openai/gpt-image-2`**: strong, but has no transparency and costs about 4x more than 2.5 at the same quality. Skip it.
- **Google Nano Banana 2.1** (`google/gemini-nano-banana-2.1`): top-5 quality at ~$0.034 (1K), $0.05 (2K),
  $0.076 (4K). Good editor with mask-based edits and subject consistency. No transparency, `n=1`.
  `gemini-3.1-flash-lite-image` takes ~4 s and only makes 1K images. `gemini-3-pro-image` is pricey but best at holding a style.
- **Microsoft MAI 2.6** (`mai-image-2.6`, `-flash`): very good quality per dollar and a strong editor. No resolution
  control or transparency, at most 5 refs.
- **FLUX 3** (`black-forest-labs/flux-3-image`, `-klein`): the most controllable and the best at leaving
  untouched regions alone during edits, native 4K. Klein is the cheapest capable model (released 2026-10-15, not ranked yet).
  4K on the full model is expensive (~$0.6).
- **xAI `grok-imagine-image-2.0`**: strong prompt adherence and typography, but slow (~60 s) and has no alpha.
- **Seedream 5.0** (`bytedance-seed/seedream-5-0-pro`/`-flash`/`-lite`): lifelike photos, multilingual posters,
  14 refs. `seedream-4.5` is still useful for `n` up to 10.
- **Qwen Image 3** (`qwen/qwen-image-3-pro`, `qwen-image-3`): dense text layouts, UI mockups, storyboards. Proofread the text.
- **Recraft V4.1**: the `-vector` models return true SVG; `-styles*` models need at least one reference and copy its style.
  `-utility` gives flat, predictable mockups.
- **Krea 2** (`krea-2-large`/`-medium`/`-medium-turbo`): expressive, textured looks at 1K only. The API lists no
  price for Krea, so the script asks for confirmation every time.
- **Sourceful Riverflow 2.5 Pro**: plans its edits, crisp typography, transparent output.

## Avoid by default

- Superseded models: `gpt-image-1`, `gpt-5-image*`, `gemini-2.5-flash-image`, `flux.2-*`, `recraft-v3`/`-v4` (non-4.1),
  `riverflow-v2-*`, `mai-image-2.5*`, `grok-imagine-image-quality`.
- `*-preview` ids that have a GA twin.
- LLM wrappers (`gpt-5.4-image-2`, `gpt-5-image*`): they charge for extra LLM tokens, and you already write the prompt.
- `meta/muse-image`: listed, but it had no routable provider at the snapshot date.

## Verified in real runs

- 2026-10-18: `openai/gpt-image-2.5-flare --quality low --background transparent` returned a real alpha PNG
  (1254×1254, 56% transparent pixels) in 12 s for $0.007. Small printed text on it was spelled correctly.
- 2026-10-18 calibration batch. Script estimates for GPT Image 2.5 now match the charges to about 0.1 cent.
  - Flare medium, transparent pixel-art rat: real alpha and clean pixel art, 12 s, $0.014. The model
    used its own ~54-cell grid, and `gen pixelize --size 32` fits it into a true 32×32 sprite.
  - Sunburst max, 16:9 key art: 1536×864, 82 s, $0.130. It is strong at composition and kept the
    upper-left area empty for the logo as asked.
  - Seedream 5.0 Lite, 2K diamond-plate texture: 2048² JPEG, 32 s, $0.035. It looks right but does
    not tile out of the box: the seam ratio was 3.2. Repair edits of the rolled image didn't fix the
    regular pattern: FLUX 3 Klein was a no-op ($0.014), and Nano Banana 2.1 softened it to 2.29
    ($0.057). The free `gen seamless` cross-fade brought it to 0.8, with faded doubled bumps in the
    blend zones. See postprocess.md.
  - Nano Banana 2.1, edit of the transparent keycard (recolor + crack): it kept the text and shape
    and applied both changes for $0.037. It returned an opaque JPEG on white, losing the
    transparency. To edit transparent assets, use GPT Image 2.5 with `--background transparent`.

## Known unknowns

- `sourceful/riverflow-v2.5-fast` advertises transparency but lists only jpeg output, so verify it before relying on it.
  The script rejects transparent requests to it.
- Gemini/MAI token counts are rough. A Nano Banana 2.1 edit with one reference cost 10% more than
  estimated, because reference tokens aren't listed in its pricing.
- Commercial use: if images ship in a commercial product, mention once that the chosen model's terms apply.
