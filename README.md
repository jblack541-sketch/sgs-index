# SGS Index — website prototype

Static site for CreatorJoe's **Sovereignty–Globalism Spectrum (SGS) Index**: daily news
(the Daily SGS Top 5 countdown), an archive, an investor-newsletter signup, and an About page.
Plain HTML/CSS/JS, built by a stdlib-only Python script. No server, database or paid service needed.

## Public rule: no numeric scores
The site only ever shows verbal labels (`Slightly / Moderately / Strongly / Extremely` +
`Sovereign / Globalist`, or `Neutral`). Numbers stay internal.
- Day files may only contain a `label`. `build.py` **refuses to build** if a story has a `score`
  (or any other unknown or numeric field), or a label outside the allowed list.
- After building, `build.py` scans every HTML/JSON/XML/JS file for score-like patterns
  (`+7`, `−4`, `plus two`, `SGS: 4`, `7/10`, the word "score"). If anything matches, the build
  fails and the live `public/` folder is left untouched.
- Spectrum markers are placed by label (CSS classes like `pos-strongly-sovereign`), not by value.

## Layout
```
build.py                 # regenerates public/ from content/ + static/
content/site.json        # site settings, incl. the newsletter form action (PLACEHOLDER)
content/days/YYYY-MM-DD.json   # one file per day (labels only)
static/                  # copied into public/ as-is: assets/ (css, js), fonts/, media/<date>/
tools/new_day.py         # makes a day file from the video pipeline's data.py (drops scores)
tools/screenshots.py     # full-page screenshots via Playwright + Chrome
public/                  # GENERATED: deploy this folder (GitHub Pages, Netlify, Cloudflare Pages…)
screenshots/             # latest screenshots
```
Generated pages: `index.html`, `news/index.html` (archive), `news/<date>/index.html`,
`newsletter.html`, `about.html`, `mission.html`, plus `days.json` (labels only) and `feed.xml` (RSS).

## Adding a day
**Option A: from the Top 5 video pipeline** (`/workspace/sgs`):
```bash
python3 tools/new_day.py --date 2026-10-28 --data /workspace/sgs/data.py \
  --video /workspace/sgs/sgs_top5_2026-10-28_myvoice.mp4 \
  --thumbnail /workspace/sgs/thumbnail.png --img-dir /workspace/sgs/img \
  --sources sources.json          # optional: {"5": [{"name": "UN Press", "url": "https://…"}], …}
```
Then open `content/days/2026-10-28.json`, check the summaries, add `video_credits`/source URLs, and run
`python3 build.py`.

Use the **label-only (my-voice) episode** for the site. The first `sgs_top5_2026-10-27.mp4` render
still says numeric scores in its narration and on screen, so don't publish it.

**Option B: by hand.** Copy the newest file in `content/days/`, rename it to the new date, edit it, put
media in `static/media/<date>/`, then run `python3 build.py`.

Day file fields: `date`, `title`, `tagline`, `video`, `poster`, `thumbnail`, `video_credits[]`,
`discovery_note`, `stories[]` (`rank`, `headline`, `summary`, `label`, `why`, `story_date`, `image`,
`image_alt`, `sources[]{name,url}`, and optional `what_it_means`, `economic_impact`, `everyday_example`).
The optional three show under each story as "What this means", "Money impact" and "In everyday terms" and are
skipped when missing; `tools/new_day.py` copies them from data.py when present. Media paths are relative to `static/`.

## Writing style
Plain, everyday words for everyone: short sentences, and explain any term (sovereignty, globalism, backtest, UN bodies…)
in a few simple words the first time it appears. Labels only, never numbers.

The newest day goes on the home page automatically, and every day is listed in the archive with
older/newer links.

## Newsletter signup (to wire up)
`content/site.json → newsletter.form_action` is set to `#NEWSLETTER_PROVIDER_FORM_ACTION`. While it
starts with `#`, the form sends nothing and tells the visitor signups aren't live yet. To go live, paste
your provider's form endpoint (Buttondown, Beehiiv, Kit, Mailchimp, …), set `email_field_name` to the
field name it expects, rebuild, and remove the "Placeholder" notes in `build.py`.

## Local preview
```bash
python3 build.py
python3 -m http.server 8765 --bind 127.0.0.1 --directory public    # http://127.0.0.1:8765/
.venv/bin/python tools/screenshots.py                              # optional (pip install playwright)
```

## Placeholders still to fill (marked on the pages with dashed amber boxes)
- How the index is defined (taken from the episode working notes; the bio link returned 404).
- Newsletter name, free vs. paid tiers, and what research it includes. The letter is monthly.
- Legal disclaimer review.
- CreatorJoe's bio on the About page.
