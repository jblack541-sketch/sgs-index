#!/usr/bin/env python3
"""Create content/days/<DATE>.json (+ copy media) from a daily video pipeline's data.py.

Usage:
  python3 tools/new_day.py --date 2026-10-28 --data /workspace/sgs/data.py \
      --video /workspace/sgs/sgs_top5_2026-10-28_myvoice.mp4 \
      --thumbnail /workspace/sgs/thumbnail.png --img-dir /workspace/sgs/img \
      [--sources sources.json] [--force]

data.py must define SEGS (same shape as the Top 5 pipeline). Any 'score' field is
DROPPED here — only the verbal 'label' is written. If a story has no label but
has an internal score, the label is derived with the public mapping
(|n|>=8 Extremely, 5-7 Strongly, 3-4 Moderately, 1-2 Slightly, 0 Neutral).

sources.json (optional) maps rank -> [{"name": ..., "url": ...}, ...]; without it,
source names from data.py's 'src' are used with no links (add URLs by hand).
If a story has 'specifics', it is used as the facts text (otherwise the narration
'text' is cleaned up). Optional per-story fields what_it_means, economic_impact and everyday_example are
copied when present (shown as "What this means", "Money impact", "In everyday terms").
Review the generated JSON (summaries especially), then run: python3 build.py
"""
import argparse, json, re, runpy, shutil, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SPOKEN = [("S G S", "SGS"), ("E U", "EU"), ("U A E", "UAE"), ("U K", "UK"), ("U S", "US"),
          ("zero point one percent", "0.1%"), ("three and a half billion", "3.5 billion"),
          ("COP thirty-one", "COP31"), ("October thirty-first", "October 31")]


def label_for(n):
    a = abs(n)
    if a == 0:
        return "Neutral"
    k = "Extremely" if a >= 8 else "Strongly" if a >= 5 else "Moderately" if a >= 3 else "Slightly"
    return f"{k} {'Sovereign' if n > 0 else 'Globalist'}"


def summary_from(text):
    for a, b in SPOKEN:
        text = text.replace(a, b)
    text = re.sub(r"^Number \w+\.\s*", "", text)
    text = re.split(r"\s*(S G S|SGS) (rating|score)\b|\s*Score:", text)[0]  # drop rating + tail
    return text.strip()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", required=True)
    ap.add_argument("--data", required=True)
    ap.add_argument("--video"); ap.add_argument("--thumbnail"); ap.add_argument("--img-dir")
    ap.add_argument("--sources"); ap.add_argument("--force", action="store_true")
    a = ap.parse_args()
    out = ROOT / "content" / "days" / f"{a.date}.json"
    if out.exists() and not a.force:
        sys.exit(f"{out} exists (use --force to overwrite)")
    segs = runpy.run_path(a.data)["SEGS"]
    srcmap = json.loads(Path(a.sources).read_text()) if a.sources else {}
    media = ROOT / "static" / "media" / a.date
    media.mkdir(parents=True, exist_ok=True)
    day = {"date": a.date, "title": "Daily SGS Top 5", "tagline": "Five stories, one question: who's in control?",
           "video_credits": [], "stories": []}
    if a.video:
        shutil.copy(a.video, media / "episode.mp4"); day["video"] = f"media/{a.date}/episode.mp4"
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", "1.5", "-i", str(media / "episode.mp4"), "-frames:v", "1",
                        "-vf", "scale=540:-2", str(media / "poster.jpg")], check=False)
        if (media / "poster.jpg").exists():
            day["poster"] = f"media/{a.date}/poster.jpg"
    if a.thumbnail:
        ext = Path(a.thumbnail).suffix
        shutil.copy(a.thumbnail, media / f"thumbnail{ext}"); day["thumbnail"] = f"media/{a.date}/thumbnail{ext}"
    for s in segs:
        if not s.get("num"):
            continue
        label = s.get("label") or (label_for(s["score"]) if "score" in s else None)
        if not label:
            sys.exit(f"story #{s['num']} has no label")
        story = {"rank": s["num"], "headline": s["head"], "summary": str(s.get("specifics") or "").strip() or summary_from(s.get("text", "")),
                 "label": label, "why": s.get("reason", "").rstrip(".") + ".",
                 "sources": srcmap.get(str(s["num"])) or [{"name": n.strip()} for n in s.get("src", "").split("·") if n.strip()]}
        for k in ("what_it_means", "economic_impact", "everyday_example"):  # optional; skipped when missing
            v = str(s.get(k) or "").strip()
            if v:
                story[k] = v
        if a.img_dir and s.get("bg"):
            src = Path(a.img_dir) / f"{s['bg']}.jpg"
            if src.exists():
                shutil.copy(src, media / src.name); story["image"] = f"media/{a.date}/{src.name}"
        day["stories"].append(story)  # NOTE: 'score' intentionally never copied
    out.write_text(json.dumps(day, indent=2, ensure_ascii=False) + "\n")
    print(f"wrote {out} with {len(day['stories'])} stories — review it, then run: python3 build.py")


if __name__ == "__main__":
    main()
