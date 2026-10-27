#!/usr/bin/env python3
"""Build the SGS Index static site.

Reads:   content/site.json, content/days/YYYY-MM-DD.json, static/
Writes:  public/   (serve or deploy this folder as-is)

Stdlib only. Run:  python3 build.py
PUBLIC RULE: numeric SGS index values never ship. Day files may only carry a
verbal `label`; the build refuses any numeric field and scans the output.
"""
import json, re, shutil, sys, datetime as dt
from html import escape as e
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CONTENT, STATIC, OUT = ROOT / "content", ROOT / "static", ROOT / "public"

INTENSITY = ["Slightly", "Moderately", "Strongly", "Extremely"]
LABELS = ["Neutral"] + [f"{k} {s}" for s in ("Sovereign", "Globalist") for k in INTENSITY]
DAY_KEYS = {"date", "title", "tagline", "video", "poster", "thumbnail", "video_credits",
            "discovery_note", "stories", "notes"}
STORY_KEYS = {"rank", "headline", "summary", "label", "why", "story_date", "image", "image_alt", "sources"}
BANNED_KEYS = {"score", "scores", "value", "sgs", "sgs_score", "raw", "num_score"}


def slug(label):
    return label.lower().replace(" ", "-")


def x_url(site):
    return site.get("x_url") or f"https://x.com/{site['x_handle']}"


def link_x(site, text):
    """Escape text, then link a standalone X and @handle. Wording stays verbatim."""
    url = e(x_url(site))
    handle = site["x_handle"]
    out = e(text).replace(e("@" + handle), f'<a href="{url}" rel="noopener">@{e(handle)}</a>')
    return re.sub(r"(?<![\w])X(?![\w])", f'<a href="{url}" rel="noopener">X</a>', out)


# ---------------------------------------------------------------- data
def load_days():
    days = []
    for f in sorted((CONTENT / "days").glob("*.json")):
        d = json.loads(f.read_text())
        problems = validate_day(d, f.name)
        if problems:
            sys.exit("Refusing to build:\n  " + "\n  ".join(problems))
        d["stories"] = sorted(d["stories"], key=lambda s: -s["rank"])  # countdown 5..1
        days.append(d)
    return sorted(days, key=lambda d: d["date"], reverse=True)


def validate_day(d, name):
    p = []
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(d.get("date", ""))):
        p.append(f"{name}: missing/invalid 'date' (YYYY-MM-DD)")
    if name != f"{d.get('date')}.json":
        p.append(f"{name}: file name must equal <date>.json")
    for k in set(d) - DAY_KEYS:
        p.append(f"{name}: unknown top-level key '{k}'" + (" (numeric scores are internal only!)" if k in BANNED_KEYS else ""))
    for i, s in enumerate(d.get("stories", [])):
        for k in set(s) - STORY_KEYS:
            p.append(f"{name} story {i}: unknown key '{k}'" + (" (numeric scores are internal only!)" if k in BANNED_KEYS else ""))
        if s.get("label") not in LABELS:
            p.append(f"{name} story {i}: label must be one of {LABELS}, got {s.get('label')!r}")
        for k, v in s.items():
            if k != "rank" and isinstance(v, (int, float)):
                p.append(f"{name} story {i}: numeric value in '{k}' not allowed")
    return p


# ---------------------------------------------------------------- layout
NAV = [("index.html", "Home"), ("news/index.html", "Daily News"),
       ("how-it-works.html", "How It Works"), ("newsletter.html", "Newsletter"),
       ("about.html", "About")]


def site_base(site):
    return str(site.get("base_url") or "").rstrip("/")


def abs_url(site, rel=""):
    """Production absolute URL when base_url is set; otherwise a path relative to the
    site root. Never a domain-root path like /assets/..., so a project-site subpath works."""
    base, rel = site_base(site), rel.lstrip("/")
    if base:
        return f"{base}/{rel}" if rel else f"{base}/"
    return rel or "index.html"


def page(title, body, depth, active, site, desc="", rel=""):
    r = "../" * depth
    nav = "".join(
        f'<a href="{r}{href}"{" aria-current=page" if label == active else ""}>{label}</a>' for href, label in NAV)
    year = dt.date.today().year
    canon = f'<link rel="canonical" href="{e(abs_url(site, rel))}">\n' if site_base(site) else ""
    return f"""<!doctype html>
<html lang="en"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{e(title)} · {e(site['site_name'])}</title>
<meta name="description" content="{e(desc or 'Daily global news framed by the Sovereignty–Globalism Spectrum (SGS) Index.')}">
<link rel="stylesheet" href="{r}assets/style.css">
<link rel="alternate" type="application/rss+xml" title="SGS Daily News" href="{r}feed.xml">
{canon}</head><body>
<header class="site-header"><div class="wrap bar">
  <a class="brand" href="{r}index.html"><span class="brand-mark" aria-hidden="true"></span><span>SGS<b>Index</b></span></a>
  <button class="nav-toggle" aria-expanded="false" aria-controls="nav">Menu</button>
  <nav id="nav" class="nav">{nav}</nav>
</div></header>
<main>{body}</main>
<footer class="site-footer"><div class="wrap foot">
  <div><strong>SGS Index</strong> · Sovereignty–Globalism Spectrum by {e(site['creator'])}.<br>
  Follow <a href="https://x.com/{e(site['x_handle'])}" rel="noopener">@{e(site['x_handle'])}</a> on X for the daily index. ·
  <a href="{r}feed.xml">RSS</a></div>
  <div class="muted small">{e(site.get('disclaimer_short', ''))}<br>
  <a href="{r}newsletter.html#disclaimer">Full disclaimer</a> · © {year} {e(site['creator'])}.</div>
</div></footer>
<script src="{r}assets/site.js" defer></script>
</body></html>"""


def spectrum(label, big=False):
    side = "sov" if "Sovereign" in label else "glob" if "Globalist" in label else "neu"
    return (f'<div class="spectrum{" big" if big else ""}" role="img" aria-label="SGS rating: {e(label)}">'
            f'<div class="track"><span class="marker pos-{slug(label)}"></span></div>'
            f'<div class="ends"><span>◀ Globalism</span><span>Sovereignty ▶</span></div></div>'
            f'<p class="label {side}">{e(label)}</p>')


def fmt_date(iso, long=True):
    d = dt.date.fromisoformat(iso)
    return d.strftime("%A, %B %-d, %Y") if long else d.strftime("%b %-d, %Y")


def story_card(s, r):
    srcs = " · ".join(f'<a href="{e(x["url"])}" rel="noopener" target="_blank">{e(x["name"])}</a>'
                      if x.get("url") else e(x["name"]) for x in s.get("sources", []))
    img = (f'<div class="story-img" style="background-image:url(\'{r}{e(s["image"])}\')" role="img" '
           f'aria-label="{e(s.get("image_alt", "AI-generated illustration"))}"></div>') if s.get("image") else ""
    return f"""<article class="story" id="story-{s['rank']}">
  {img}
  <div class="story-body">
    <div class="rank">#{s['rank']}</div>
    <h3>{e(s['headline'])}</h3>
    <p>{e(s['summary'])}</p>
    {spectrum(s['label'])}
    <p class="why"><span>Why:</span> {e(s['why'])}</p>
    <p class="src small">{('<span class="muted">' + e(s['story_date']) + '</span> · ') if s.get('story_date') else ''}Sources: {srcs}</p>
  </div>
</article>"""


def episode_block(d, r):
    credits = "".join(f"<li>{e(c)}</li>" for c in d.get("video_credits", []))
    video = (f'<video controls preload="metadata" playsinline poster="{r}{e(d.get("poster") or d.get("thumbnail", ""))}">'
             f'<source src="{r}{e(d["video"])}" type="video/mp4">Your browser cannot play this video. '
             f'<a href="{r}{e(d["video"])}">Download the episode</a>.</video>') if d.get("video") else ""
    links = ([f'<a href="{r}{e(d["video"])}" download>Download MP4</a>'] if d.get("video") else []) + \
            ([f'<a href="{r}{e(d["thumbnail"])}">Thumbnail</a>'] if d.get("thumbnail") else [])
    dl = f'<p class="small muted">{" · ".join(links)}</p>' if links else '<p class="small muted">Video coming soon.</p>'
    return f"""<div class="episode">
  <div class="player">{video}
    {dl}
  </div>
  <div class="stories">{''.join(story_card(s, r) for s in d['stories'])}
    <div class="credits small muted"><strong>Episode credits.</strong><ul>{credits}</ul>{e(d.get('discovery_note', ''))}</div>
  </div>
</div>"""


SIGNUP_FORM = """<form class="signup" action="{action}" method="{method}" novalidate>
  <label for="{fid}-email">Email address</label>
  <div class="row"><input id="{fid}-email" type="email" name="{field}" placeholder="you@example.com" autocomplete="email" required>
  <button type="submit">Join the list</button></div>
  <fieldset><legend class="small">Send me</legend>
    <label class="chk"><input type="checkbox" name="list" value="ledger" checked> {name} (free monthly letter)</label>
    <label class="chk"><input type="checkbox" name="list" value="daily"> Daily SGS Top 5 news digest</label>
  </fieldset>
  <label class="chk small"><input type="checkbox" name="consent" required> I agree to receive email from CreatorJoe and can unsubscribe anytime.</label>
  <p class="form-msg small" role="status" aria-live="polite"></p>
</form>"""


def signup(site, fid):
    n = site["newsletter"]
    return SIGNUP_FORM.format(action=e(n["form_action"]), method=e(n.get("form_method", "post")),
                              field=e(n.get("email_field_name", "email")), fid=fid,
                              name=e(n.get("name", "The Sovereign Ledger")))


def pitch_full(site):
    n = site["newsletter"]
    name = n.get("name", "The Sovereign Ledger")
    html = e(n["pitch"]).replace(e(name), f"<em>{e(name)}</em>", 1)
    return f'<p class="lede">{html}</p>'


def pitch_short(site, r=""):
    name = e(site["newsletter"].get("name", "The Sovereign Ledger"))
    return f"""<div class="pitch">
  <p class="kicker">Free monthly letter</p>
  <h2>{name}</h2>
  <p>Long-term investing doesn't change day to day, so this letter doesn't either. Once a month, <em>{name}</em> steps back from the daily headlines and looks at where the Sovereignty–Globalism Spectrum moved. You'll also get research notes on the themes being tested. It's free, it comes once a month, and it's not financial advice.</p>
  <p><a href="{r}newsletter.html">About {name}</a></p>
</div>"""


SCALE = [f"{k} Globalist" for k in reversed(INTENSITY)] + ["Neutral"] + [f"{k} Sovereign" for k in INTENSITY]


def scale_pills():
    items = []
    for label in SCALE:
        side = "sov" if "Sovereign" in label else "glob" if "Globalist" in label else "neu"
        items.append(f'<li class="{side}">{e(label)}</li>')
    return '<ul class="pills">' + "".join(items) + "</ul>"


def how_body(site):
    x = link_x(site, "The SGS Index is versioned, and I post updates openly on X (@TraderJoe541) so anyone can see what changed and why.")
    return f"""<section class="section"><div class="wrap narrow prose">
  <p class="kicker">The Index</p>
  <h1>How the index works</h1>
  <h2>Two ends of one spectrum</h2>
  <p><strong class="sov">Sovereign</strong> means power is moving toward the individual, the local community, or a truly independent nation. Examples are free speech, privacy, medical choice, self-defense, local control, and stepping back from supranational bodies or foreign leverage.</p>
  <p><strong class="glob">Globalist</strong> means power is moving toward centralized or supranational control. Examples are global governance bodies and treaties that override national decisions, debt traps and aid with strings attached, central bank digital currencies, and anything that trades individual freedom for top-down management.</p>
  <h2>Sovereignty is not the same as state power</h2>
  <p>A strong government isn't automatically "sovereign." Early versions of the index drifted that way, so I reset it: a regime that crushes its own people's freedoms lands toward the globalist/centralized end, whatever flag it flies. Individual freedom comes first, and everything else is secondary.</p>
  <h2>What gets weighed</h2>
  <ul class="ticks">
    <li><strong>Individual freedoms and bodily autonomy</strong> (the biggest share, about half): speech, privacy, medical choice, self-defense, protest, movement, religious expression.</li>
    <li><strong>Anti-globalism and decentralization:</strong> does it actually break from centralized systems like the UN, WHO, IMF or supranational debt, or does it just look sovereign while adding top-down control?</li>
    <li><strong>Economic and data sovereignty:</strong> CBDCs, capital controls, debt leverage, who controls the data.</li>
    <li><strong>Foreign ties and elite networks:</strong> outside leverage, influence operations, and information warfare.</li>
  </ul>
  <h2>Checks that keep it honest</h2>
  <ul class="ticks">
    <li><strong>Rhetoric vs. outcomes.</strong> What a leader says doesn't count. What actually changes does.</li>
    <li><strong>Show the power shift.</strong> A sovereign rating needs evidence that power really moved toward individuals, communities or independent nations.</li>
    <li><strong>Spot disguised centralization.</strong> Policies sold as freedom that quietly centralize get flagged.</li>
    <li><strong>Evidence first.</strong> Public records and primary sources come first, decentralized sources are prioritized, and there are no blanket generalizations. Speculation stays off unless it's clearly labeled as speculation.</li>
  </ul>
  <div class="scale">
    <h2>The label scale</h2>
    <p>Every rated story gets one label (we never publish numbers on this site):</p>
    {scale_pills()}
  </div>
  <h2>What gets rated</h2>
  <p>The biggest geopolitical, policy and economic stories of the day. That includes international bodies (UN, EU, WHO, IMF), treaties and trade deals, elections and leadership moves, borders and self-determination, central banking, currencies and digital money, climate and global tax proposals, energy and supply-chain dependence, and tech and data control. The Daily SGS Top 5 counts down the day's five biggest moves on the spectrum.</p>
  <h2>An evolving framework</h2>
  <p>{x}</p>
</div></section>"""


# ---------------------------------------------------------------- pages
def build(site, days):
    if OUT.exists():
        shutil.rmtree(OUT)
    shutil.copytree(STATIC, OUT)
    latest = days[0] if days else None

    # Home
    if latest:
        r = ""
        top = "".join(
            f'<li><a href="news/{latest["date"]}/index.html#story-{s["rank"]}"><span class="rank-s">#{s["rank"]}</span>'
            f'<span class="h">{e(s["headline"])}</span><span class="label {"sov" if "Sovereign" in s["label"] else "glob" if "Globalist" in s["label"] else "neu"}">{e(s["label"])}</span></a></li>'
            for s in latest["stories"])
        latest_html = f"""<section class="section"><div class="wrap">
  <div class="section-head"><p class="kicker">Today's Daily News</p><h2>SGS Top 5 · {fmt_date(latest['date'])}</h2>
  <p class="muted">{e(latest.get('tagline', ''))}</p></div>
  <div class="latest">
    <a class="thumb" href="news/{latest['date']}/index.html"><img src="{e(latest.get('thumbnail') or latest.get('poster', ''))}" alt="Daily SGS Top 5 thumbnail for {fmt_date(latest['date'], False)}" loading="lazy"><span class="play">▶ Watch episode</span></a>
    <div><ol class="toplist">{top}</ol>
    <p><a class="btn" href="news/{latest['date']}/index.html">Read today's countdown →</a> <a class="btn ghost" href="news/index.html">Archive</a></p></div>
  </div></div></section>"""
    else:
        latest_html = ""
    tag = site.get("tagline", "")
    if ". " in tag:
        head, rest = tag.split(". ", 1)
        head += "."
    else:
        head, rest = tag, ""
    name = e(site["newsletter"].get("name", "The Sovereign Ledger"))
    home = f"""<section class="hero"><div class="wrap">
  <p class="kicker">Sovereignty–Globalism Spectrum</p>
  <h1>{e(head)}</h1>
  <p class="lede">{e(rest)}</p>
  <p><a class="btn" href="news/index.html">Daily News</a> <a class="btn ghost" href="newsletter.html">{name}</a></p>
  {spectrum('Neutral', big=True).replace('<p class="label neu">Neutral</p>', '')}
</div></section>
{latest_html}
<section class="section alt" id="what"><div class="wrap narrow">
  <div class="section-head"><p class="kicker">The Index in plain terms</p><h2>What is the SGS Index?</h2></div>
  <p class="lede">{e(site['definition'])}</p>
  <p><a class="btn ghost" href="how-it-works.html">How the index works</a></p>
</div></section>
<section class="section" id="newsletter"><div class="wrap split">
  {pitch_short(site)}
  <div class="card form-card">{signup(site, 'home')}</div>
</div></section>"""
    write("index.html", page(head, home, 0, "Home", site, desc=tag, rel=""))

    # Day pages
    for i, d in enumerate(days):
        newer = days[i - 1]["date"] if i > 0 else None
        older = days[i + 1]["date"] if i + 1 < len(days) else None
        pager = '<nav class="pager">' + (f'<a href="../{older}/index.html">← {fmt_date(older, False)}</a>' if older else '<span></span>') + \
                '<a href="../index.html">All days</a>' + (f'<a href="../{newer}/index.html">{fmt_date(newer, False)} →</a>' if newer else '<span></span>') + '</nav>'
        body = f"""<section class="section"><div class="wrap">
  <div class="section-head"><p class="kicker">Daily News · {fmt_date(d['date'])}</p><h1>{e(d.get('title', 'Daily SGS Top 5'))}</h1>
  <p class="lede">{e(d.get('tagline', ''))} Counting down from #5 to #1.</p></div>
  {episode_block(d, '../../')}
  {pager}
</div></section>
<section class="section alt"><div class="wrap split">{pitch_short(site, '../../')}<div class="card form-card">{signup(site, 'day')}</div></div></section>"""
        write(f"news/{d['date']}/index.html", page(f"SGS Top 5 · {fmt_date(d['date'], False)}", body, 2, "Daily News", site,
                                                   desc=" · ".join(s["headline"] for s in d["stories"]),
                                                   rel=f"news/{d['date']}/index.html"))

    # Archive
    items = "".join(f"""<li class="arch"><a href="{d['date']}/index.html">
  {f'<img src="../{e(d["thumbnail"])}" alt="" loading="lazy">' if d.get('thumbnail') else ''}
  <div><p class="kicker">{fmt_date(d['date'])}</p><h3>{e(d.get('title', 'Daily SGS Top 5'))}</h3>
  <p class="small muted">{' · '.join(e(s['headline']) for s in d['stories'][::-1][:3])}…</p></div></a></li>""" for d in days)
    body = f"""<section class="section"><div class="wrap">
  <div class="section-head"><p class="kicker">Daily News</p><h1>Archive</h1><p class="lede">Every daily SGS Top 5 countdown, newest first.</p></div>
  <ul class="archive">{items or '<li>No episodes yet.</li>'}</ul></div></section>"""
    write("news/index.html", page("Daily News archive", body, 1, "Daily News", site, rel="news/index.html"))

    # How the index works
    write("how-it-works.html", page("How the index works", how_body(site), 0, "How It Works", site,
                                    desc="How the Sovereignty–Globalism Spectrum rates a story, from what gets weighed to the verbal label scale.",
                                    rel="how-it-works.html"))

    # Newsletter — full pitch here; the home signup uses the short version.
    nname = site["newsletter"].get("name", "The Sovereign Ledger")
    body = f"""<section class="section"><div class="wrap">
  <div class="section-head"><p class="kicker">Free monthly letter</p><h1>{e(nname)}</h1></div>
  <div class="split">
    {pitch_full(site)}
    <div class="card form-card"><h2>Get the letter</h2>{signup(site, 'nl')}</div>
  </div>
</div></section>
<section class="section alt" id="disclaimer"><div class="wrap narrow">
  <h2>Disclaimer</h2>
  <p class="muted">{e(site['disclaimer'])}</p>
</div></section>"""
    write("newsletter.html", page(nname, body, 0, "Newsletter", site,
                                  desc=site["newsletter"]["pitch"],
                                  rel="newsletter.html"))

    # About — bio verbatim, with X mentions linked.
    paras = "".join(f"<p>{link_x(site, p)}</p>" for p in site["about"])
    body = f"""<section class="section"><div class="wrap narrow prose">
  <p class="kicker">About</p><h1>About the SGS Index</h1>
  {paras}
  <h2>How the episodes are made</h2>
  <ul>
    <li>Stories are found on {link_x(site, "X")} News and linked to their primary or press sources.</li>
    <li>Episode artwork is AI-generated; no real people are depicted.</li>
    <li>Narration is CreatorJoe's voice (an AI voice clone); the background music is original.</li>
  </ul>
  <h2>Contact</h2>
  <p>Reach CreatorJoe on {link_x(site, "X")}: {link_x(site, "@" + site["x_handle"])}.</p>
</div></section>"""
    write("about.html", page("About", body, 0, "About", site, desc=site["about"][0], rel="about.html"))

    # Public data index + RSS (labels only). Absolute links use base_url so they
    # stay on the project-site subpath; with no base_url they stay site-relative.
    pub = [{"date": d["date"], "title": d.get("title"), "url": abs_url(site, f"news/{d['date']}/index.html"),
            "stories": [{"rank": s["rank"], "headline": s["headline"], "label": s["label"]} for s in d["stories"]]} for d in days]
    write("days.json", json.dumps(pub, indent=2, ensure_ascii=False))
    rss_items = "".join(f"""<item><title>{e('SGS Top 5 · ' + fmt_date(d['date'], False))}</title><link>{e(abs_url(site, f"news/{d['date']}/index.html"))}</link>
<guid isPermaLink="false">sgs-{d['date']}</guid><pubDate>{dt.datetime.fromisoformat(d['date']).strftime('%a, %d %b %Y 12:00:00 +0000')}</pubDate>
<description>{e(' | '.join('#' + str(s['rank']) + ' ' + s['headline'] + ' (' + s['label'] + ')' for s in d['stories']))}</description></item>""" for d in days)
    write("feed.xml", f'<?xml version="1.0" encoding="UTF-8"?><rss version="2.0"><channel><title>SGS Index · Daily News</title>'
                      f'<link>{e(abs_url(site))}</link><description>Daily global news on the Sovereignty–Globalism Spectrum.</description>{rss_items}</channel></rss>')


def write(rel, text):
    p = OUT / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text)


# ---------------------------------------------------------------- leak check
LEAK = [re.compile(p, re.I) for p in [
    r"\bscores?\b",                                            # the word itself
    r"(?<![\w./#])[+\-\u2212]\s?\d{1,2}(?![\d%.,:])",          # signed numbers like +7, -4, −6
    r"\b(SGS|rating|index)\s*(value|reading)?\s*[:=(]\s*[+\-\u2212]?\d",  # "SGS: 4", "rating (7"
    r"\b(plus|minus)\s+(one|two|three|four|five|six|seven|eight|nine|ten)\b",
    r"\b\d{1,2}\s*/\s*10\b",                                  # "7/10"
]]


def leak_check():
    hits = []
    for f in OUT.rglob("*"):
        if f.suffix not in {".html", ".json", ".xml", ".js", ".txt"}:
            continue
        text = f.read_text(errors="ignore")
        text = re.sub(r"(href|src|poster)=\"[^\"]*\"", "", text)  # ignore URLs (dates in paths)
        text = re.sub(r"\"url\": \"[^\"]*\"", "", text)
        text = re.sub(r"<(link|guid)[^>]*>[^<]*</\1>", "", text)
        for rx in LEAK:
            for m in rx.finditer(text):
                hits.append(f"{f.relative_to(OUT)}: …{text[max(0, m.start() - 30):m.end() + 30]!r}…")
    return hits


if __name__ == "__main__":
    site = json.loads((CONTENT / "site.json").read_text())
    days = load_days()
    final, OUT = OUT, ROOT / "public.tmp"   # build to a temp dir; publish only if clean
    build(site, days)
    hits = leak_check()
    if hits:
        print("NUMERIC-SCORE LEAK CHECK FAILED (public/ left unchanged):\n  " + "\n  ".join(hits))
        sys.exit(1)
    if final.exists():
        shutil.rmtree(final)
    OUT.rename(final); OUT = final
    print(f"Built {len(days)} day(s) → {OUT}  (leak check passed: no numeric scores)")
