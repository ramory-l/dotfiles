#!/usr/bin/env python3
"""Generate and edit images through the OpenRouter Images API (POST /api/v1/images).

Stdlib only. Subcommands:
  models    list image models with capabilities and rough prices (cached for 24h)
  info      show one model's description, parameters and per-provider pricing
  generate  generate or edit images; saves them to <project root>/generated-images/
  check     inspect saved images: real transparency, optional 2x2 tile preview (needs Pillow)
  sheet     combine several images into one numbered contact sheet (needs Pillow)
  pixelize  snap an image to a true pixel grid and a limited palette (needs Pillow)
  roll      shift an image by half its size so tiling seams meet in the center, or back (needs Pillow)
  seamless  make an irregular texture tile by cross-fading it with its half-roll (needs Pillow)
  merge-seam paste only the repaired center cross of a rolled texture back in (needs Pillow)
  balance   show the remaining credit of the API key

The API key is read from $OPENROUTER_API_KEY.
Every command prints JSON (or a table for `models`) to stdout. Exit codes: 0 ok or dry run,
1 API/network error, 2 bad arguments, 3 estimated cost needs confirmation (rerun with --yes).
"""

import argparse
import base64
import concurrent.futures
import datetime
import difflib
import http.client
import json
import math
import mimetypes
import os
import pathlib
import re
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

API = "https://openrouter.ai/api/v1"
HOME = pathlib.Path.home()
CACHE_DIR = pathlib.Path(os.environ.get("XDG_CACHE_HOME", HOME / ".cache")) / "openrouter-images"
CACHE_TTL = 24 * 3600
OUT_DIR_NAME = "generated-images"
DEFAULT_MAX_COST = float(os.environ.get("OPENROUTER_IMAGES_MAX_COST", "0.25"))
GENERATE_TIMEOUT = 300  # generations can take 90+ s
# Failed generations are not billed, so these are safe to retry. Timeouts (504/524) are not: the
# generation may still finish and be charged, so only GETs retry them.
RETRY_STATUSES = {429, 502, 503, 529}
GET_RETRY_STATUSES = RETRY_STATUSES | {504, 524}

# Approximate pixel area per resolution tier, in megapixels.
RES_MP = {"512": 0.26, "768": 0.59, "1K": 1.05, "1.5K": 2.36, "2K": 4.19, "4K": 16.8}
# Grid side per quality for OpenAI's GPT Image 2/2.5 output-token formula (see _grid_tokens).
# Verified against real OpenRouter charges on 2026-10-18 (exact to 0.1 cent at low/medium/max).
GRID_SIDES = [
    ("openai/gpt-image-2.5", {"low": 16, "medium": 24, "high": 48, "xhigh": 64, "max": 96}),
    ("openai/gpt-image-2", {"low": 16, "medium": 48, "high": 96}),
    ("openai/gpt-5.4-image-2", {"low": 16, "medium": 48, "high": 96}),
]
# Output tokens per ~1 MP image for older OpenAI models (gpt-image-1 family); "auto" counts as "high".
QUALITY_TOKENS = {"low": 272, "medium": 1056, "high": 4160}
# Output tokens per image for token-priced models without `quality` (Gemini-style), by max megapixels.
AREA_TOKENS = [(0.3, 747), (1.1, 1120), (4.5, 1680), (float("inf"), 2520)]

# CLI flag -> API field, for the image parameters that are validated against the model.
PARAM_FLAGS = {
    "n": "n",
    "aspect": "aspect_ratio",
    "resolution": "resolution",
    "size": "size",
    "quality": "quality",
    "background": "background",
    "format": "output_format",
    "compression": "output_compression",
    "seed": "seed",
}


class ApiError(Exception):
    def __init__(self, status, message, payload=None):
        super().__init__(message)
        self.status = status
        self.payload = payload or {}


def emit(obj, code=0):
    print(json.dumps(obj, indent=2, ensure_ascii=False))
    sys.exit(code)


def fail(message, code=2, **extra):
    emit({"status": "error", "message": message, **extra}, code)


def load_key():
    return os.environ.get("OPENROUTER_API_KEY", "").strip() or None


def require_key():
    key = load_key()
    if not key:
        fail("OPENROUTER_API_KEY is not set in this shell.",
             hint="Export it from the shell profile (e.g. ~/.zshrc) and restart Claude Code so new shells inherit it.")
    if not key.startswith("sk-or-"):
        # OpenRouter answers any malformed key with a misleading 401 "Missing Authentication header".
        looks_hex = all(c in "0123456789abcdefABCDEF" for c in key)
        fail("OPENROUTER_API_KEY doesn't look like an OpenRouter key (expected it to start with sk-or-).",
             hint=("It is a hex string: macOS `security ... -w` prints a stored password as hex when it contains a "
                   "newline or non-ASCII character. Re-save the key without a trailing newline." if looks_hex else
                   "Check for surrounding quotes, spaces or a different service's key."))
    return key


def _retry_delay(retry_after, attempt):
    try:
        delay = float(retry_after)
    except (TypeError, ValueError):  # missing, or an HTTP date
        delay = float("nan")
    if not math.isfinite(delay) or delay < 0:
        return 5.0 * (attempt + 1)
    return min(delay, 60.0)


def api(method, path, body=None, key=None, timeout=60, retries=0):
    data = json.dumps(body).encode() if body is not None else None
    headers = {"Accept": "application/json", "X-OpenRouter-Title": "claude-code-openrouter-images"}
    if data is not None:
        headers["Content-Type"] = "application/json"
    if key:
        headers["Authorization"] = f"Bearer {key}"
    for attempt in range(retries + 1):
        req = urllib.request.Request(API + path, data=data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                raw = resp.read()
            try:
                return json.loads(raw)
            except ValueError:
                raise ApiError(200, "the response body was not valid JSON")
        except urllib.error.HTTPError as e:
            raw = e.read().decode("utf-8", "replace")
            try:
                payload = json.loads(raw)
            except ValueError:  # some 404s are plain text
                payload = None
            err = payload.get("error") if isinstance(payload, dict) else None
            if not isinstance(err, dict):  # normalize so callers can rely on payload["error"] being a dict
                err = {"message": str(err) if err else raw.strip()[:500]}
            retry_after = e.headers.get("Retry-After")
            statuses = GET_RETRY_STATUSES if method == "GET" else RETRY_STATUSES
            retryable = e.code in statuses or (e.code == 402 and retry_after)
            if retryable and attempt < retries:
                time.sleep(_retry_delay(retry_after, attempt))
                continue
            raise ApiError(e.code, err.get("message") or f"HTTP {e.code}", {"error": err})
        except (urllib.error.URLError, TimeoutError, ConnectionError, http.client.HTTPException) as e:
            # A POST that timed out client-side may still be generating (and billed): never resend it.
            if method == "GET" and attempt < retries:
                time.sleep(5.0 * (attempt + 1))
                continue
            raise ApiError(None, f"network error: {e}")


def cached(name, fetch, refresh=False):
    path = CACHE_DIR / name
    if not refresh and path.is_file() and time.time() - path.stat().st_mtime < CACHE_TTL:
        return json.loads(path.read_text())
    data = fetch()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f"{path.name}.{os.getpid()}.tmp")  # atomic: parallel runs never read half a file
    tmp.write_text(json.dumps(data))
    os.replace(tmp, path)
    return data


def list_models(refresh=False):
    return cached("models.json", lambda: api("GET", "/images/models", retries=2)["data"], refresh)


def model_endpoints(model_id, refresh=False):
    path = f"/images/models/{urllib.parse.quote(model_id, safe='/:')}/endpoints"
    name = "endpoints/" + model_id.replace("/", "__") + ".json"
    return cached(name, lambda: api("GET", path, retries=2).get("endpoints") or [], refresh)


def find_model(models, model_id):
    for m in models:
        if m["id"] == model_id:
            return m
    close = difflib.get_close_matches(model_id, [m["id"] for m in models], n=5, cutoff=0.4)
    fail(f"Unknown image model: {model_id}", did_you_mean=close,
         hint="Run the `models` subcommand to see current ids (the catalog changes often).")


# ---------- cost estimate ----------

def _megapixels(params):
    size = str(params.get("size") or "")
    m = re.fullmatch(r"(\d+)x(\d+)", size)
    if m:
        return int(m.group(1)) * int(m.group(2)) / 1e6
    tier = params.get("resolution") or (size if size in RES_MP else None) or "1K"
    return RES_MP.get(tier, RES_MP["1K"])


def _openai_size(params):
    """Output pixel size OpenAI models return on OpenRouter (observed: 1:1 → 1024², 16:9 → 1536×864)."""
    m = re.fullmatch(r"(\d+)x(\d+)", str(params.get("size") or ""))
    if m:
        return int(m.group(1)), int(m.group(2))
    aspect = params.get("aspect_ratio")
    if not aspect or aspect in ("1:1", "auto"):
        return 1024, 1024
    a, b = (float(x) for x in aspect.split(":"))
    if a >= b:
        return 1536, max(16, round(1536 * b / a / 16) * 16)
    return max(16, round(1536 * a / b / 16) * 16), 1536


def _grid_tokens(side, width, height):
    """Port of OpenAI's GptImageTokenCalculator: output tokens for one GPT Image 2/2.5 image."""
    s = side / (max(width, height) / min(width, height))
    floor = math.floor(s)
    short = floor + floor % 2 if s - floor == 0.5 else round(s)
    cells = (side * short) if width >= height else (short * side)
    return math.ceil(cells * (2e6 + width * height) / 4e6)


def _output_tokens(model, params):
    """Output-token count per image for token-priced models (exact for GPT Image 2/2.5, rough otherwise)."""
    quality = params.get("quality") or "high"
    quality = "high" if quality == "auto" else quality
    for prefix, sides in GRID_SIDES:
        if model["id"].startswith(prefix):
            side = sides.get(quality, max(sides.values()))
            return _grid_tokens(side, *_openai_size(params))
    mp = _megapixels(params)
    if "quality" in (model.get("supported_parameters") or {}):  # gpt-image-1 family
        tokens = QUALITY_TOKENS.get(quality, QUALITY_TOKENS["high"])
        aspect = params.get("aspect_ratio")
        wide = 1.5 if aspect and aspect not in ("1:1", "auto") else 1.0
        return tokens * max(mp / RES_MP["1K"], 1.0) * wide
    return next(tokens for limit, tokens in AREA_TOKENS if mp <= limit)


def _pick_entries(entries, params):
    """Choose the pricing entries that match the requested resolution/quality variant."""
    if not any(p.get("variant") for p in entries):
        return entries
    res = str(params.get("resolution") or params.get("size") or "1K").lower()
    quality = str(params.get("quality") or "").lower()
    for wanted in [w for w in (quality and f"{quality}_{res}", res, quality) if w]:
        hit = [p for p in entries if str(p.get("variant", "")).lower() == wanted]
        if hit:
            return hit
    explicit = any(params.get(k) for k in ("resolution", "size", "quality"))
    plain = [p for p in entries if not p.get("variant")]
    if plain and not explicit:
        return plain
    # An explicit size/quality with no matching variant: assume the priciest tier rather than under-ask.
    return [max(entries, key=lambda p: float(p.get("cost_usd") or 0))]


def estimate_cost(model, endpoints, params, n_refs=0, prompt=""):
    """Upper-bound-ish USD estimate for one request, or None when the price is unknown."""
    n = int(params.get("n") or 1)
    estimates = []
    for ep in endpoints:
        pricing = ep.get("pricing")
        if not isinstance(pricing, list):
            continue
        pricing = [p for p in pricing if isinstance(p, dict)]
        outputs = [p for p in pricing if p.get("billable") == "output_image"]
        if not outputs:
            continue
        total, known = 0.0, True
        for p in _pick_entries(outputs, params):
            cost, unit = float(p.get("cost_usd") or 0), p.get("unit")
            if unit == "image":
                total += cost * n
            elif unit == "megapixel":
                total += cost * _megapixels(params) * n
            elif unit == "request":
                total += cost
            elif unit == "token":
                total += cost * _output_tokens(model, params) * n
            else:  # a unit we can't price: treat the endpoint as unknown so the guard asks
                known = False
        if not known:
            continue
        for p in pricing:
            cost, unit, billable = float(p.get("cost_usd") or 0), p.get("unit"), p.get("billable")
            if billable in ("input_image", "input_reference") and n_refs:
                total += cost * n_refs * (1000 if unit == "token" else 1)
            elif billable == "input_text" and unit == "token":
                total += cost * (len(prompt) / 4 + 50)
        estimates.append(total)
    return round(max(estimates), 4) if estimates else None


# ---------- models / info ----------

def summarize(model, endpoints):
    sp = model.get("supported_parameters") or {}
    refs = sp.get("input_references")
    entry = {
        "id": model["id"],
        "est_usd": estimate_cost(model, endpoints, {}),
        "refs": "-" if not refs else (f"{refs.get('min')}-{refs.get('max')}" if refs.get("min") else f"<={refs.get('max')}"),
        "n_max": (sp.get("n") or {}).get("max", 1),
        "transparent": "transparent" in (sp.get("background") or {}).get("values", []),
        "quality": (sp.get("quality") or {}).get("values", []),
        "resolution": (sp.get("resolution") or {}).get("values", []),
        "formats": (sp.get("output_format") or {}).get("values", []),
        "seed": "seed" in sp,
        "description": (model.get("description") or "").strip(),
    }
    if "quality" in sp:
        entry["est_usd_low"] = estimate_cost(model, endpoints, {"quality": "low"})
    return entry


def cmd_models(args):
    models = list_models(args.refresh)
    # Filter on catalog data first so pricing is fetched only for the models that will be shown.
    if args.search:
        needle = args.search.lower()
        models = [m for m in models if needle in m["id"].lower() or needle in (m.get("description") or "").lower()]
    if args.edit:
        models = [m for m in models if "input_references" in (m.get("supported_parameters") or {})]
    if args.transparent:
        models = [m for m in models
                  if "transparent" in ((m.get("supported_parameters") or {}).get("background") or {}).get("values", [])]

    def fetch(m):
        try:
            return m, model_endpoints(m["id"], args.refresh)
        except ApiError:
            return m, []

    with concurrent.futures.ThreadPoolExecutor(max_workers=16) as pool:
        rows = [summarize(m, eps) for m, eps in pool.map(fetch, models)]

    if args.max_price is not None:
        def cheapest(r):
            prices = [v for v in (r["est_usd"], r.get("est_usd_low")) if v is not None]
            return min(prices) if prices else None
        rows = [r for r in rows if cheapest(r) is not None and cheapest(r) <= args.max_price]
    if args.sort == "price":
        rows.sort(key=lambda r: (r["est_usd"] is None, r["est_usd"] or 0))
    else:
        rows.sort(key=lambda r: r["id"])

    if args.json:
        print(json.dumps(rows, indent=2, ensure_ascii=False))
        return

    def money(v):
        return "?" if v is None else f"{v:.3f}"

    header = f"{'model':<44} {'~$/img':>17}  {'refs':<6} {'n':>2}  {'transp':<6} {'quality':<30} resolution / formats"
    print(header)
    print("-" * len(header))
    for r in rows:
        price = money(r["est_usd"]) + (f" (lo {money(r['est_usd_low'])})" if "est_usd_low" in r else "")
        extras = ",".join(r["resolution"]) + (" / " + ",".join(r["formats"]) if r["formats"] else "")
        print(f"{r['id']:<44} {price:>17}  {r['refs']:<6} {r['n_max']:>2}  {'yes' if r['transparent'] else '-':<6} "
              f"{','.join(r['quality']) or '-':<30} {extras}")
        if args.long and r["description"]:
            print(f"    {r['description'][:300]}")
    print(f"\n{len(rows)} models. ~$/img is a rough 1-image estimate at default settings "
          "(token-priced models assume quality auto~high; 'lo' = quality low). refs = reference images accepted "
          "('-' text-only, '1-N' edit-only).")


def cmd_info(args):
    model = find_model(list_models(args.refresh), args.model)
    endpoints = model_endpoints(model["id"], args.refresh)
    emit({
        "id": model["id"],
        "name": model.get("name"),
        "description": model.get("description"),
        "input_modalities": (model.get("architecture") or {}).get("input_modalities"),
        "supported_parameters": model.get("supported_parameters"),
        "estimated_usd_default_request": estimate_cost(model, endpoints, {}),
        "endpoints": [{
            "provider": ep.get("provider_slug"),
            "pricing": ep.get("pricing"),
            "passthrough": ep.get("allowed_passthrough_parameters"),
            "supported_parameters": ep.get("supported_parameters"),
        } for ep in endpoints],
    })


# ---------- generate ----------

def validate(model, params, n_refs):
    sp = model.get("supported_parameters") or {}
    problems = []
    for key, value in params.items():
        desc = sp.get(key)
        if desc is None:
            problems.append(f"`{key}` is not supported by {model['id']}")
        elif desc.get("type") == "enum" and str(value) not in [str(v) for v in desc.get("values", [])]:
            problems.append(f"`{key}={value}` is not allowed; options: {desc.get('values')}")
        elif desc.get("type") == "range" and not (desc.get("min", value) <= value <= desc.get("max", value)):
            problems.append(f"`{key}={value}` is out of range {desc.get('min')}..{desc.get('max')}")
    refs = sp.get("input_references")
    if n_refs and not refs:
        problems.append(f"{model['id']} does not accept reference images")
    elif refs:
        if n_refs < refs.get("min", 0):
            problems.append(f"{model['id']} is edit-only: it needs at least {refs['min']} reference image(s)")
        if n_refs > refs.get("max", n_refs):
            problems.append(f"{model['id']} accepts at most {refs['max']} reference images")
    if params.get("background") == "transparent":
        fmt = params.get("output_format")
        formats = (sp.get("output_format") or {}).get("values") or []
        if fmt and fmt not in ("png", "webp"):
            problems.append(f"`background=transparent` needs png or webp output, not {fmt}")
        elif not fmt and formats and not {"png", "webp"} & set(formats):
            problems.append(f"{model['id']} only returns {formats} here, which can't hold transparency")
    return problems


def reference_part(ref):
    if re.match(r"https?://", ref):
        url = ref
    else:
        path = pathlib.Path(ref).expanduser()
        if not path.is_file():
            fail(f"Reference image not found: {ref}")
        mime = mimetypes.guess_type(path.name)[0] or "image/png"
        url = f"data:{mime};base64," + base64.b64encode(path.read_bytes()).decode()
    return {"type": "image_url", "image_url": {"url": url}}


def project_root():
    try:
        out = subprocess.run(["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True, timeout=5)
        if out.returncode == 0 and out.stdout.strip():
            return pathlib.Path(out.stdout.strip())
    except (OSError, subprocess.SubprocessError):
        pass
    return pathlib.Path.cwd()


def slugify(text, limit=48):
    words = re.findall(r"[a-z0-9]+", text.lower())
    slug = "-".join(words[:6])[:limit].strip("-")
    return slug or "image"


def extension(media_type, blob):
    by_type = {"image/png": "png", "image/jpeg": "jpg", "image/webp": "webp", "image/svg+xml": "svg",
               "image/gif": "gif"}
    if media_type in by_type:
        return by_type[media_type]
    if blob.startswith(b"\x89PNG"):
        return "png"
    if blob.startswith(b"\xff\xd8"):
        return "jpg"
    if blob[:4] == b"RIFF" and blob[8:12] == b"WEBP":
        return "webp"
    if blob.startswith(b"GIF8"):
        return "gif"
    if blob.lstrip(b"\xef\xbb\xbf \t\r\n")[:1] == b"<":
        return "svg"
    return "png"


def error_hint(err):
    meta = (err.payload.get("error") or {}).get("metadata") or {}
    if err.status == 200:
        return "The response could not be read, but the request may have been billed. Check balance before retrying."
    if err.status == 401:
        if "Missing Authentication header" in str(err):
            return "The key is malformed (quotes, spaces, hex-encoded?). OpenRouter keys look like sk-or-v1-..."
        return "The API key is invalid or revoked."
    if err.status == 402:
        return f"Out of credits or key limit ({meta.get('limit_source', 'unknown')}). Top up at https://openrouter.ai/credits."
    if err.status == 403:
        return "Refused by moderation/guardrails. Rephrase the prompt or try another model; don't retry the same request."
    if err.status == 400:
        return "Bad request: check the parameters with `info <model>`."
    if err.status == 404:
        return "Unknown model or resource: refresh the list with `models --refresh`."
    if err.status in (408, 504, 524) or err.status is None:
        return "Timed out. The generation may still finish and be billed; check balance before retrying."
    return None


def cmd_generate(args):
    if bool(args.prompt) == bool(args.prompt_file):
        fail("Pass exactly one of --prompt or --prompt-file.")
    if args.prompt_file:
        prompt_path = pathlib.Path(args.prompt_file).expanduser()
        if not prompt_path.is_file():
            fail(f"Prompt file not found: {args.prompt_file}")
        prompt = prompt_path.read_text().strip()
    else:
        prompt = args.prompt.strip()
    if not prompt:
        fail("The prompt is empty.")
    key = None if args.dry_run else require_key()

    model = find_model(list_models(), args.model)
    params = {}
    for flag, field in PARAM_FLAGS.items():
        value = getattr(args, flag)
        if value is not None:
            params[field] = value
    if params.get("background") == "transparent" and "output_format" not in params:
        formats = ((model.get("supported_parameters") or {}).get("output_format") or {}).get("values", [])
        if "png" in formats:
            params["output_format"] = "png"

    refs = args.ref or []
    problems = validate(model, params, len(refs))
    if problems:
        fail("Parameters don't fit this model.", problems=problems,
             supported_parameters=model.get("supported_parameters"))

    body = {"model": model["id"], "prompt": prompt, **params}
    if refs:
        body["input_references"] = [reference_part(r) for r in refs]

    try:
        endpoints = model_endpoints(model["id"])
    except ApiError:
        endpoints = []
    if args.passthrough:
        options = {}
        for item in args.passthrough:
            name, sep, value = item.partition("=")
            if not sep or not name:
                fail(f"--passthrough expects key=value, got `{item}`")
            try:
                value = json.loads(value)  # numbers, booleans, arrays and objects keep their type
            except ValueError:
                pass
            slugs = [ep.get("provider_slug") for ep in endpoints if name in (ep.get("allowed_passthrough_parameters") or [])]
            if not slugs:
                fail(f"No provider of {model['id']} accepts passthrough `{name}`.")
            for slug in slugs:
                options.setdefault(slug, {})[name] = value
        body["provider"] = {"options": options}

    estimate = estimate_cost(model, endpoints, params, len(refs), prompt)
    max_cost = DEFAULT_MAX_COST if args.max_cost is None else args.max_cost
    over_budget = estimate is None or estimate > max_cost
    out_dir = pathlib.Path(args.out_dir).expanduser() if args.out_dir else project_root() / OUT_DIR_NAME
    stem = datetime.datetime.now().strftime("%Y%m%d-%H%M%S-") + slugify(args.name or prompt)

    if args.dry_run:
        shown = json.loads(json.dumps(body))
        for part in shown.get("input_references", []):
            url = part["image_url"]["url"]
            if url.startswith("data:"):
                part["image_url"]["url"] = url[:40] + f"...<{len(url)} chars>"
        emit({"status": "dry_run", "request": shown, "estimated_cost_usd": estimate, "max_cost_usd": max_cost,
              "would_need_confirmation": over_budget, "out_dir": str(out_dir), "file_stem": stem})

    if over_budget and not args.yes:
        reason = "price unknown for this model" if estimate is None else f"estimate ${estimate} > limit ${max_cost}"
        emit({"status": "needs_confirmation", "model": model["id"], "estimated_cost_usd": estimate,
              "max_cost_usd": max_cost, "reason": reason,
              "hint": "Ask the user; if they agree, rerun the same command with --yes."}, 3)

    started = time.time()
    try:
        result = api("POST", "/images", body, key=key, timeout=GENERATE_TIMEOUT, retries=2)
    except ApiError as e:
        err = e.payload.get("error") or {}
        emit({"status": "error", "http_status": e.status, "message": str(e),
              "error_type": (err.get("metadata") or {}).get("error_type") or err.get("code"),
              "metadata": err.get("metadata"), "hint": error_hint(e)}, 1)
    elapsed = round(time.time() - started, 1)

    images = result.get("data") or []
    cost = (result.get("usage") or {}).get("cost")
    if not images:
        emit({"status": "empty", "model": model["id"], "cost_usd": cost, "elapsed_s": elapsed,
              "hint": "No image returned (often a silent moderation refusal). Rephrase or try another model."}, 1)

    out_dir.mkdir(parents=True, exist_ok=True)
    files, errors = [], []
    for i, item in enumerate(images, 1):
        # The request is already paid for: never let one bad item lose the others or the cost report.
        try:
            b64 = item.get("b64_json") if isinstance(item, dict) else None
            if not b64:
                raise ValueError("no b64_json in the response item")
            if b64.startswith("data:"):
                b64 = b64.split(",", 1)[1]
            blob = base64.b64decode(b64)
        except ValueError as e:
            errors.append(f"image {i}: {e}")
            continue
        suffix = f"-{i}" if len(images) > 1 else ""
        ext = extension(item.get("media_type"), blob)
        path = out_dir / f"{stem}{suffix}.{ext}"
        dup = 2
        while path.exists() or path.with_suffix(".json").exists():  # parallel runs, same --name, same second
            path = out_dir / f"{stem}{suffix}-v{dup}.{ext}"
            dup += 1
        path.write_bytes(blob)
        path.with_suffix(".json").write_text(json.dumps({
            "file": path.name,
            "model": model["id"],
            "prompt": prompt,
            "params": params,
            "references": refs,
            "request_cost_usd": cost,
            "images_in_request": len(images),
            "created": datetime.datetime.now().isoformat(timespec="seconds"),
        }, indent=2, ensure_ascii=False))
        files.append(str(path))

    result_out = {"status": "ok" if files else "error", "model": model["id"], "files": files,
                  "requested": params.get("n", 1), "returned": len(images), "cost_usd": cost,
                  "estimated_cost_usd": estimate, "elapsed_s": elapsed}
    if errors:
        result_out["errors"] = errors
    emit(result_out, 0 if files else 1)


def wrap_seams(img):
    """How much brighter the jump across the tiling wrap is than a normal neighbor step (1 = invisible)."""
    px = img.convert("L").load()
    w, h = img.size

    def ratio(edge, normal):
        e = sum(edge) / len(edge)
        n = sum(normal) / len(normal)
        return round(e / max(n, 1e-6), 2)

    ys, xs = range(0, h, 4), range(0, w, 4)
    horizontal = ratio([abs(px[w - 1, y] - px[0, y]) for y in ys], [abs(px[w // 2 - 1, y] - px[w // 2, y]) for y in ys])
    vertical = ratio([abs(px[x, h - 1] - px[x, 0]) for x in xs], [abs(px[x, h // 2 - 1] - px[x, h // 2]) for x in xs])
    worst = max(horizontal, vertical)
    verdict = ("tiles cleanly" if worst <= 1.5 else "faint seam, check the preview" if worst <= 2.2
               else "visible seam when tiled")
    return {"wrap_seam_ratio": {"left_right": horizontal, "top_bottom": vertical}, "tiling": verdict}


def cmd_seamless(args):
    try:
        from PIL import Image, ImageChops
    except ImportError:
        fail("`seamless` needs Pillow: python3 -m pip install pillow")
    src = pathlib.Path(args.file).expanduser()
    with Image.open(src) as img:
        base = img.convert("RGB")
    w, h = base.size
    rolled = ImageChops.offset(base, w // 2, h // 2)
    # Classic cross-fade: keep the original in the middle (no seam there) and the half-rolled copy at the
    # borders (its edges come from the original's interior, so they wrap continuously).
    ramp_x = [1 - abs(2 * x / (w - 1) - 1) for x in range(w)]
    ramp_y = [1 - abs(2 * y / (h - 1) - 1) for y in range(h)]
    weight = Image.new("L", (w, h))
    weight.putdata([round(255 * min(1.0, 2.5 * min(rx, ry))) for ry in ramp_y for rx in ramp_x])
    out_img = Image.composite(base, rolled, weight)
    out = pathlib.Path(args.out).expanduser() if args.out else src.with_name(f"{src.stem}.seamless.png")
    out_img.save(out)
    emit({"status": "ok", "file": str(out), "before": wrap_seams(base), "after": wrap_seams(out_img),
          "hint": ("Works for irregular materials (concrete, rust, dirt, rock). On regular patterns "
                   "(tiles, diamond plate, bricks) the blend zones show doubled shapes: look at "
                   "`check --tile` before using it.")})


def cmd_check(args):
    try:
        from PIL import Image
    except ImportError:
        fail("`check` needs Pillow: python3 -m pip install pillow")
    results = []
    for name in args.files:
        path = pathlib.Path(name).expanduser()
        if path.suffix.lower() == ".svg":
            results.append({"file": str(path), "verdict": "vector (SVG): transparent wherever no shape is drawn. "
                            "To look at it, rasterize first, e.g. `qlmanage -t -s 1024 -o <dir> <file.svg>` on macOS."})
            continue
        with Image.open(path) as img:
            w, h = img.size
            rgba = img.convert("RGBA")
            alpha = rgba.getchannel("A")
            hist = alpha.histogram()
            edges = [alpha.crop(box) for box in ((0, 0, w, 1), (0, h - 1, w, h), (0, 0, 1, h), (w - 1, 0, w, h))]
            border_clear = sum(sum(e.histogram()[:16]) for e in edges) / (2 * w + 2 * h)
            info = {
                "file": str(path),
                "size": [w, h],
                "mode": img.mode,
                "has_alpha_channel": img.mode in ("RGBA", "LA", "PA") or "transparency" in img.info,
                "transparent_ratio": round(sum(hist[:16]) / (w * h), 3),
                "border_transparent_ratio": round(border_clear, 3),
            }
            # Judge by the border, not single corners: a cut-out sprite may touch one edge.
            if info["transparent_ratio"] < 0.005:
                info["verdict"] = ("opaque: no transparent pixels. Expected for textures and full-frame art; "
                                   "for a cut-out sprite it means the background is painted (look for a fake checkerboard)")
            elif border_clear >= 0.5:
                info["verdict"] = "real transparency: the background is cut out"
            else:
                info["verdict"] = ("partial transparency: some pixels are clear but most of the border is opaque. "
                                   "Fine for a full-bleed or rounded-corner icon; for a cut-out sprite the "
                                   "background is probably painted. Look at it.")
            if args.tile:
                info.update(wrap_seams(rgba))
                tile = Image.new(rgba.mode, (w * 2, h * 2))
                for dx in (0, w):
                    for dy in (0, h):
                        tile.paste(rgba, (dx, dy))
                tile_path = path.with_name(path.stem + ".tile2x2.png")
                tile.save(tile_path)
                info["tile_preview"] = str(tile_path)
        results.append(info)
    emit({"status": "ok", "results": results})


def cmd_sheet(args):
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        fail("`sheet` needs Pillow: python3 -m pip install pillow")
    all_paths = [pathlib.Path(f).expanduser() for f in args.files]
    skipped = [str(p) for p in all_paths if p.suffix.lower() == ".svg"]
    paths = [p for p in all_paths if p.suffix.lower() != ".svg"]
    if not paths:
        fail("No raster images to put on a sheet (SVG files are skipped).")
    if args.cols is not None and args.cols < 1:
        fail("--cols must be at least 1.")
    if args.cell < 32:
        fail("--cell must be at least 32 px.")
    cell, pad = args.cell, 12
    cols = args.cols or min(len(paths), 2 if len(paths) == 4 else 3)
    rows = -(-len(paths) // cols)
    sheet = Image.new("RGB", (cols * (cell + pad) + pad, rows * (cell + pad) + pad), (32, 32, 36))
    try:
        font = ImageFont.load_default(size=max(cell // 12, 14))
    except TypeError:  # Pillow < 10.1
        font = ImageFont.load_default()
    draw = ImageDraw.Draw(sheet)
    for i, path in enumerate(paths):
        with Image.open(path) as img:
            thumb = img.convert("RGBA")
        scale = min(cell / thumb.size[0], cell / thumb.size[1])
        new_size = (max(1, round(thumb.size[0] * scale)), max(1, round(thumb.size[1] * scale)))
        # Nearest-neighbor when enlarging keeps pixel art crisp.
        resample = Image.Resampling.NEAREST if scale > 1 else Image.Resampling.LANCZOS
        thumb = thumb.resize(new_size, resample)
        # A checkerboard behind each image keeps transparent areas visible.
        board = Image.new("RGBA", thumb.size, (200, 200, 200, 255))
        bd = ImageDraw.Draw(board)
        step = max(cell // 32, 8)
        for y in range(0, thumb.size[1], step):
            for x in range((y // step) % 2 * step, thumb.size[0], step * 2):
                bd.rectangle((x, y, x + step - 1, y + step - 1), fill=(150, 150, 150, 255))
        board.alpha_composite(thumb)
        x0 = pad + (i % cols) * (cell + pad) + (cell - thumb.size[0]) // 2
        y0 = pad + (i // cols) * (cell + pad) + (cell - thumb.size[1]) // 2
        sheet.paste(board.convert("RGB"), (x0, y0))
        label, origin = str(i + 1), (x0 + 6, y0 + 4)
        _, _, right, bottom = draw.textbbox(origin, label, font=font)
        draw.rectangle((x0, y0, right + 6, bottom + 4), fill=(0, 0, 0))
        draw.text(origin, label, fill=(255, 255, 255), font=font)
    out = pathlib.Path(args.out).expanduser() if args.out else paths[0].with_name(paths[0].stem + ".sheet.png")
    if out.suffix.lower() not in (".png", ".jpg", ".jpeg", ".webp"):
        out = out.with_name(out.name + ".png")
    sheet.save(out)
    result = {"status": "ok", "sheet": str(out), "order": [str(p) for p in paths]}
    if skipped:
        result["skipped_svg"] = skipped
    emit(result)


def cmd_pixelize(args):
    try:
        from PIL import Image, ImageStat
    except ImportError:
        fail("`pixelize` needs Pillow: python3 -m pip install pillow")
    src = pathlib.Path(args.file).expanduser()
    width, height = args.size, args.height or args.size
    with Image.open(src) as img:
        full = img.convert("RGBA")
    # Models draw pixel art on their own grid and leave margins: fit the sprite's bounding box to the
    # target grid (minus a margin) instead of shrinking the whole canvas.
    mask = full.getchannel("A").point(lambda a: 255 if a > 127 else 0)
    box = mask.getbbox() if mask.getextrema()[0] == 0 else None
    if box and not args.keep_canvas:
        full = full.crop(box)
        inner_w, inner_h = max(1, width - 2 * args.margin), max(1, height - 2 * args.margin)
        scale = min(inner_w / full.width, inner_h / full.height)
        fit = (max(1, round(full.width * scale)), max(1, round(full.height * scale)))
    else:
        fit = (width, height)
    opaque = full.getchannel("A").point(lambda a: 255 if a > 127 else 0)
    rgb_full = full.convert("RGB")
    if opaque.getextrema() == (0, 255):
        # Fill clear pixels with the average opaque color so they don't use up a palette slot.
        fill = Image.new("RGB", rgb_full.size, tuple(int(c) for c in ImageStat.Stat(rgb_full, opaque).mean))
        rgb_full = Image.composite(rgb_full, fill, opaque)
    # Palette from the full-resolution art, then average each target cell (robust to a grid that
    # doesn't line up with ours) and snap it back to that palette.
    palette = rgb_full.quantize(colors=args.colors, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE)
    cells = rgb_full.resize(fit, Image.Resampling.BOX)
    quantized = cells.quantize(palette=palette, dither=Image.Dither.NONE)
    cell_alpha = full.getchannel("A").resize(fit, Image.Resampling.BOX).point(lambda a: 255 if a > 127 else 0)
    sprite = quantized.convert("RGBA")
    sprite.putalpha(cell_alpha)
    out_img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    out_img.paste(sprite, ((width - fit[0]) // 2, (height - fit[1]) // 2))
    out = pathlib.Path(args.out).expanduser() if args.out else src.with_name(f"{src.stem}.px{width}x{height}.png")
    out_img.save(out)
    preview = out.with_name(out.stem + f".x{args.preview_scale}.png")
    out_img.resize((width * args.preview_scale, height * args.preview_scale), Image.Resampling.NEAREST).save(preview)
    emit({"status": "ok", "sprite": str(out), "preview": str(preview), "size": [width, height],
          "palette_colors": len(quantized.getcolors(maxcolors=4096) or []),
          "hint": "Look at the preview, not the tiny sprite."})


def cmd_roll(args):
    try:
        from PIL import Image, ImageChops
    except ImportError:
        fail("`roll` needs Pillow: python3 -m pip install pillow")
    src = pathlib.Path(args.file).expanduser()
    with Image.open(src) as img:
        img.load()
        w, h = img.size
        dx, dy = (-(w // 2), -(h // 2)) if args.back else (w // 2, h // 2)
        rolled = ImageChops.offset(img, dx, dy)
    tag = "unrolled" if args.back else "rolled"
    out = pathlib.Path(args.out).expanduser() if args.out else src.with_name(f"{src.stem}.{tag}{src.suffix or '.png'}")
    rolled.save(out)
    emit({"status": "ok", "file": str(out), "offset": [dx, dy],
          "hint": ("Seams now meet in the center cross; repair them with an edit model, then roll --back."
                   if not args.back else "Back to the original alignment; re-check with `check --tile`.")})


def cmd_merge_seam(args):
    try:
        from PIL import Image, ImageDraw, ImageFilter
    except ImportError:
        fail("`merge-seam` needs Pillow: python3 -m pip install pillow")
    rolled_path = pathlib.Path(args.rolled).expanduser()
    with Image.open(rolled_path) as img:
        base = img.convert("RGB")
    with Image.open(pathlib.Path(args.repaired).expanduser()) as img:
        fix = img.convert("RGB")
    if fix.size != base.size:
        fix = fix.resize(base.size, Image.Resampling.LANCZOS)
    w, h = base.size
    band = args.band or max(16, min(w, h) // 16)
    # Take only a feathered band around the center cross from the repaired image. Everything else
    # stays pixel-identical, so the tile edges (already continuous after the roll) can't break.
    mask = Image.new("L", base.size, 0)
    draw = ImageDraw.Draw(mask)
    draw.rectangle((w // 2 - band, 0, w // 2 + band, h), fill=255)
    draw.rectangle((0, h // 2 - band, w, h // 2 + band), fill=255)
    mask = mask.filter(ImageFilter.GaussianBlur(band / 3))
    merged = Image.composite(fix, base, mask)

    def seam_step(img):  # mean brightness jump across the center line vs. a normal neighbor step
        px = img.convert("L").load()
        across = sum(abs(px[w // 2 - 1, y] - px[w // 2, y]) for y in range(0, h, 4)) / len(range(0, h, 4))
        normal = sum(abs(px[w // 4 - 1, y] - px[w // 4, y]) for y in range(0, h, 4)) / len(range(0, h, 4))
        return round(across / max(normal, 1e-6), 2)

    out = pathlib.Path(args.out).expanduser() if args.out else rolled_path.with_name(rolled_path.stem + ".merged.png")
    merged.save(out)
    emit({"status": "ok", "file": str(out), "band_px": band,
          "seam_ratio_before": seam_step(base), "seam_ratio_after": seam_step(merged),
          "repair_changed_center": seam_step(fix) < seam_step(base) * 0.7,
          "hint": "A seam ratio near 1 means no visible jump. Next: `roll --back`, then `check --tile`."})


def cmd_balance(_args):
    key = require_key()
    out = {}
    try:
        data = api("GET", "/key", key=key, retries=1).get("data") or {}
        out["key"] = {k: data.get(k) for k in ("label", "limit", "limit_remaining", "limit_reset", "usage", "usage_daily", "usage_monthly")}
    except ApiError as e:
        out["key_error"] = str(e)
    try:
        data = api("GET", "/credits", key=key).get("data") or {}
        out["account_balance_usd"] = round(data["total_credits"] - data["total_usage"], 4)
    except (ApiError, KeyError, TypeError):
        out["account_balance_usd"] = None  # /credits may require a management key on some accounts
    emit(out, 0)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("models", help="list image models")
    p.add_argument("--search", help="substring of id or description")
    p.add_argument("--edit", action="store_true", help="only models that accept reference images")
    p.add_argument("--transparent", action="store_true", help="only models with transparent background")
    p.add_argument("--max-price", type=float, help="only models with a ~$/img estimate at or below this")
    p.add_argument("--sort", choices=["id", "price"], default="id")
    p.add_argument("--long", action="store_true", help="include descriptions")
    p.add_argument("--json", action="store_true")
    p.add_argument("--refresh", action="store_true", help="ignore the 24h cache")
    p.set_defaults(func=cmd_models)

    p = sub.add_parser("info", help="show one model in detail")
    p.add_argument("model")
    p.add_argument("--refresh", action="store_true")
    p.set_defaults(func=cmd_info)

    p = sub.add_parser("generate", help="generate or edit images")
    p.add_argument("--model", required=True)
    p.add_argument("--prompt")
    p.add_argument("--prompt-file", help="read the prompt from a file (for long prompts)")
    p.add_argument("--ref", action="append", help="reference/edit image: local path or https URL; repeatable")
    p.add_argument("--n", type=int, help="number of images (an upper bound)")
    p.add_argument("--aspect", help="aspect ratio, e.g. 16:9")
    p.add_argument("--resolution", help="512, 768, 1K, 1.5K, 2K or 4K")
    p.add_argument("--size", help="tier like 2K or explicit WxH")
    p.add_argument("--quality", help="auto, low, medium, high, xhigh, max")
    p.add_argument("--background", help="auto, transparent or opaque")
    p.add_argument("--format", help="png, jpeg, webp or svg")
    p.add_argument("--compression", type=int, help="0-100 for jpeg/webp")
    p.add_argument("--seed", type=int)
    p.add_argument("--passthrough", action="append", help="provider-specific key=value, e.g. moderation=low")
    p.add_argument("--name", help="short English slug for the file name")
    p.add_argument("--out-dir", help=f"default: <project root>/{OUT_DIR_NAME}")
    p.add_argument("--max-cost", type=float, help=f"confirmation threshold in USD (default {DEFAULT_MAX_COST})")
    p.add_argument("--yes", action="store_true", help="the user approved a cost above the threshold")
    p.add_argument("--dry-run", action="store_true", help="validate and estimate without calling the API")
    p.set_defaults(func=cmd_generate)

    p = sub.add_parser("check", help="inspect saved images: real alpha? (needs Pillow)")
    p.add_argument("files", nargs="+")
    p.add_argument("--tile", action="store_true", help="also write a 2x2 tiled preview to inspect seams")
    p.set_defaults(func=cmd_check)

    p = sub.add_parser("sheet", help="numbered contact sheet of several images (needs Pillow)")
    p.add_argument("files", nargs="+")
    p.add_argument("--cols", type=int)
    p.add_argument("--cell", type=int, default=512, help="max cell size in px")
    p.add_argument("--out", help="default: <first file>.sheet.png")
    p.set_defaults(func=cmd_sheet)

    p = sub.add_parser("pixelize", help="snap to a true pixel grid and palette (needs Pillow)")
    p.add_argument("file")
    p.add_argument("--size", type=int, required=True, help="target width in pixels, e.g. 32")
    p.add_argument("--height", type=int, help="target height (default: same as --size)")
    p.add_argument("--colors", type=int, default=16, help="palette size")
    p.add_argument("--margin", type=int, default=1, help="empty pixels kept around the sprite")
    p.add_argument("--keep-canvas", action="store_true", help="shrink the whole canvas instead of fitting the sprite")
    p.add_argument("--preview-scale", type=int, default=8)
    p.add_argument("--out", help="default: <file>.px<W>x<H>.png")
    p.set_defaults(func=cmd_pixelize)

    p = sub.add_parser("roll", help="shift by half the size so tiling seams meet in the center (needs Pillow)")
    p.add_argument("file")
    p.add_argument("--back", action="store_true", help="undo a previous roll")
    p.add_argument("--out", help="default: <file>.rolled.<ext> (or .unrolled with --back)")
    p.set_defaults(func=cmd_roll)

    p = sub.add_parser("seamless", help="make an irregular texture tile by cross-fading with its half-roll (needs Pillow)")
    p.add_argument("file")
    p.add_argument("--out", help="default: <file>.seamless.png")
    p.set_defaults(func=cmd_seamless)

    p = sub.add_parser("merge-seam", help="paste only the repaired center cross into a rolled texture (needs Pillow)")
    p.add_argument("rolled", help="the output of `roll`")
    p.add_argument("repaired", help="the edit model's repair of the rolled image")
    p.add_argument("--band", type=int, help="half-width of the pasted band in px (default: size/16)")
    p.add_argument("--out", help="default: <rolled>.merged.png")
    p.set_defaults(func=cmd_merge_seam)

    p = sub.add_parser("balance", help="remaining credit")
    p.set_defaults(func=cmd_balance)

    args = parser.parse_args()
    try:
        args.func(args)
    except ApiError as e:
        fail(str(e), code=1, http_status=e.status)


if __name__ == "__main__":
    main()
