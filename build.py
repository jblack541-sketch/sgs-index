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
STORY_KEYS = {"rank", "headline", "summary", "label", "why", "story_date", "image", "image_alt", "sources",
              "what_it_means", "economic_impact", "everyday_example"}
# Optional plain-language breakdown, shown in this order after the specifics when present.
BREAKDOWN = [("what_it_means", "What this means"), ("economic_impact", "Money impact"),
             ("everyday_example", "In everyday terms")]
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
       ("mission.html", "Mission"), ("how-it-works.html", "How It Works"), ("newsletter.html", "Newsletter"),
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
<meta name="description" content="{e(desc or 'Daily world news, rated on one simple question: is power moving to everyday people and independent nations, or to global control?')}">
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
  <div><strong>SGS Index</strong> · the Sovereignty–Globalism Spectrum, by {e(site['creator'])}. Who's really in control, explained in plain words.<br>
  Follow <a href="https://x.com/{e(site['x_handle'])}" rel="noopener">@{e(site['x_handle'])}</a> on X for daily updates. ·
  <a href="{r}mission.html">My mission</a> · <a href="{r}feed.xml">RSS feed</a></div>
  <div class="muted small">{e(site.get('disclaimer_short', ''))}<br>
  <a href="{r}newsletter.html#disclaimer">Full disclaimer (plain English)</a> · © {year} {e(site['creator'])}.</div>
</div></footer>
<script src="{r}assets/site.js" defer></script>
</body></html>"""


def spectrum(label, big=False):
    side = "sov" if "Sovereign" in label else "glob" if "Globalist" in label else "neu"
    return (f'<div class="spectrum{" big" if big else ""}" role="img" aria-label="SGS rating: {e(label)}">'
            f'<div class="track"><span class="marker pos-{slug(label)}"></span></div>'
            f'<div class="ends"><span>◀ More global control</span><span>More independence ▶</span></div></div>'
            f'<p class="label {side}">{e(label)}</p>')


def fmt_date(iso, long=True):
    d = dt.date.fromisoformat(iso)
    return d.strftime("%A, %B %-d, %Y") if long else d.strftime("%b %-d, %Y")


def story_card(s, r):
    srcs = " · ".join(f'<a href="{e(x["url"])}" rel="noopener" target="_blank">{e(x["name"])}</a>'
                      if x.get("url") else e(x["name"]) for x in s.get("sources", []))
    img = (f'<div class="story-img" style="background-image:url(\'{r}{e(s["image"])}\')" role="img" '
           f'aria-label="{e(s.get("image_alt", "AI-generated illustration"))}"></div>') if s.get("image") else ""
    return f"""<article class="story{'' if img else ' no-img'}" id="story-{s['rank']}">
  {img}
  <div class="story-body">
    <div class="rank">#{s['rank']}</div>
    <h3>{e(s['headline'])}</h3>
    <p>{e(s['summary'])}</p>
    {breakdown(s)}
    {spectrum(s['label'])}
    <p class="why"><span>Why this label:</span> {e(s['why'])}</p>
    <p class="src small">{('<span class="muted">' + e(s['story_date']) + '</span> · ') if s.get('story_date') else ''}Sources: {srcs}</p>
  </div>
</article>"""


def breakdown(s):
    rows = [(lbl, str(s[k]).strip()) for k, lbl in BREAKDOWN if str(s.get(k) or "").strip()]
    if not rows:
        return ""
    return '<dl class="breakdown">' + "".join(f"<dt>{e(l)}</dt><dd>{e(v)}</dd>" for l, v in rows) + "</dl>"


def episode_block(d, r):
    credits = "".join(f"<li>{e(c)}</li>" for c in d.get("video_credits", []))
    video = (f'<video controls preload="metadata" playsinline poster="{r}{e(d.get("poster") or d.get("thumbnail", ""))}">'
             f'<source src="{r}{e(d["video"])}" type="video/mp4">Your browser can\'t play this video. '
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
    <label class="chk"><input type="checkbox" name="list" value="daily"> Daily SGS Top 5 news recap</label>
  </fieldset>
  <label class="chk small"><input type="checkbox" name="consent" required> Yes, CreatorJoe can email me. I can unsubscribe anytime.</label>
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
  <p>Long-term investing doesn't change much day to day, so this letter doesn't either. Once a month, <em>{name}</em> steps back from the daily news and looks at the big picture: did the world move toward more independence or more central control, and what could that mean for people investing for the long haul? You'll also get notes on the ideas I'm testing. It's free, it comes once a month, and it's not financial advice.</p>
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
    x = link_x(site, "I keep improving the index, and I post every update openly on X (@TraderJoe541) so anyone can see what changed and why.")
    return f"""<section class="section"><div class="wrap narrow prose">
  <p class="kicker">The Index</p>
  <h1>How the index works</h1>
  <p class="lede">The SGS Index rates news stories on one question: who gains power? Here's how I decide, in plain words.</p>
  <h2>Two ends of one line</h2>
  <p><strong class="sov">Sovereign</strong> means power is moving toward you: the individual, your local community, or a country that truly runs its own affairs. Think free speech, privacy, making your own medical choices, the right to defend yourself, local control, and countries stepping back from big international bodies or outside pressure.</p>
  <p><strong class="glob">Globalist</strong> means power is moving away from you, up to big central or international bodies that make decisions for many countries at once. Think global organizations and treaties that override a country's own choices, loans and aid that come with strings attached, central bank digital currencies (government-run digital money that can be tracked and controlled), and anything that trades your freedom for top-down control.</p>
  <h2>A strong government is not the same as a free people</h2>
  <p>A powerful government doesn't automatically count as "sovereign." Early versions of the index leaned that way, so I fixed it. A government that crushes its own people's freedoms lands on the globalist, central-control side, no matter what flag it flies. Your freedom comes first. Everything else comes second.</p>
  <h2>What I look at</h2>
  <ul class="ticks">
    <li><strong>Your personal freedoms and your body</strong> (the biggest part, about half): free speech, privacy, medical choice, self-defense, the right to protest, freedom to move around, and freedom of religion.</li>
    <li><strong>Breaking away from central control:</strong> does it really step away from big central systems like the UN, the WHO (World Health Organization), the IMF (International Monetary Fund, which lends to countries) or debt owed to global lenders? Or does it just look independent while adding more top-down control?</li>
    <li><strong>Control of money and data:</strong> government digital money, limits on moving your money across borders, debt used as leverage, and who controls your data.</li>
    <li><strong>Foreign ties and powerful networks:</strong> pressure from outside powers, behind-the-scenes influence campaigns, and battles over information.</li>
  </ul>
  <h2>How I keep it honest</h2>
  <ul class="ticks">
    <li><strong>Actions, not words.</strong> What a leader says doesn't count. What actually changes does.</li>
    <li><strong>Show the shift.</strong> To call something Sovereign, there has to be proof that power really moved toward people, communities or independent countries.</li>
    <li><strong>Catch hidden power grabs.</strong> If a policy is sold as freedom but quietly hands more control to the top, I flag it.</li>
    <li><strong>Evidence first.</strong> I start with public records and original sources, give extra weight to independent sources, and avoid broad generalizations. If something is a guess, I say so clearly, or I leave it out.</li>
  </ul>
  <div class="scale">
    <h2>The labels</h2>
    <p>Every story gets one label. I never post numbers on this site, just these words:</p>
    {scale_pills()}
    <p class="small muted">Slightly, Moderately, Strongly or Extremely tells you how big the shift is. Sovereign or Globalist tells you which way it goes. Neutral means it doesn't really move either way.</p>
  </div>
  <h2>What gets rated</h2>
  <p>The biggest world, policy and money stories of the day. That includes international groups (the UN, EU, WHO and IMF), treaties and trade deals, elections and changes in leadership, borders and a people's right to choose their own future, central banks, currencies and digital money, climate and global tax plans, how much countries rely on others for energy and goods, and who controls technology and data. The Daily SGS Top 5 counts down the five stories that shifted power the most that day.</p>
  <h2>Always improving</h2>
  <p>{x}</p>
  <p><a class="btn ghost" href="mission.html">Read my mission</a></p>
</div></section>"""


def mission_body(site):
    x = link_x(site, "Ask questions and push back on X at @TraderJoe541. I don't have every answer, and your questions help me explain things better.")
    name = e(site["newsletter"].get("name", "The Sovereign Ledger"))
    return f"""<section class="section"><div class="wrap narrow prose">
  <p class="kicker">Mission</p>
  <h1>My mission</h1>
  <h2>Why I started this</h2>
  <p>I'll be honest: I started studying the market and the news to make money. Somewhere along the way, I started enjoying it. Once I understood how money really works, I could see the world more clearly, and I could tell what's built to last and what isn't.</p>
  <h2>What I learned</h2>
  <p>Money leaves a trail. When you follow it, you can check anyone's receipts, including politicians. Where is the money going? Is it giving power back to people, or taking it away? That one question changed how I see the news.</p>
  <h2>What I'm doing with it</h2>
  <p>The SGS Index is how I share that question with you. Every day I break down the biggest stories in plain words: what happened, what it means, and how it hits your wallet. Once a month, <em>{name}</em> looks at the long-term picture for investors.</p>
  <h2>What you'll get</h2>
  <ul class="ticks">
    <li><strong>The Daily SGS Top 5.</strong> A short video every morning that counts down the five biggest stories of the day. Each one gets a simple label, from Extremely Sovereign (more freedom for people and nations) to Extremely Globalist (more control at the global level), with Neutral in the middle.</li>
    <li><strong><em>{name}</em>.</strong> A free letter, once a month, for people investing for the long haul. It skips the daily noise and looks at the big themes, like debt, interest rates, sound money and energy.</li>
    <li><strong>Words, not numbers.</strong> Every rating is a plain label, so you can see at a glance which way a story leans and how strongly.</li>
  </ul>
  <h2>How I'll teach, and how we'll grow</h2>
  <ul class="ticks">
    <li><strong>Plain words, every time.</strong> Every story gets explained so anyone can follow it. No background needed.</li>
    <li><strong>Why it matters to you.</strong> I'll connect the headlines to everyday life: your freedom, your paycheck, your savings.</li>
    <li><strong>Terms explained.</strong> If I use a word like sovereignty or backtest, I'll tell you what it means right there.</li>
    <li><strong>Open about the method.</strong> I show how the index works, and where it falls short.</li>
    <li><strong>No hype. No buy or sell calls.</strong> This is about understanding the world, not chasing quick trades.</li>
    <li><strong>Learning together.</strong> {x}</li>
  </ul>
  <div class="card">
    <h2>Quick word guide</h2>
    <p><strong class="sov">Sovereign:</strong> people and nations running their own affairs.<br>
    <strong class="glob">Globalist:</strong> decisions moving up to big international bodies.<br>
    <strong>Index:</strong> a consistent way of rating things, so one day can be compared with the next.<br>
    <strong>Backtest:</strong> checking how an idea would have played out in the past.</p>
  </div>
  <h2>My promise</h2>
  <p>No hype and no jargon. If you can read the news, you can follow along, and we'll learn this together.</p>
  <p>Stay sovereign. <span class="muted">— Joe</span></p>
  <p><a class="btn" href="news/index.html">Watch the Daily Top 5</a> <a class="btn ghost" href="newsletter.html">Get the monthly letter</a> <a class="btn ghost" href="how-it-works.html">How the index works</a></p>
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
  <div class="section-head"><p class="kicker">Today's news</p><h2>SGS Top 5 · {fmt_date(latest['date'])}</h2>
  <p class="muted">{e(latest.get('tagline', ''))}</p></div>
  <div class="latest">
    <a class="thumb" href="news/{latest['date']}/index.html"><img src="{e(latest.get('thumbnail') or latest.get('poster', ''))}" alt="Daily SGS Top 5 thumbnail for {fmt_date(latest['date'], False)}" loading="lazy"><span class="play">▶ Watch episode</span></a>
    <div><ol class="toplist">{top}</ol>
    <p><a class="btn" href="news/{latest['date']}/index.html">Read today's countdown →</a> <a class="btn ghost" href="news/index.html">Past days</a></p></div>
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
  <p><a class="btn" href="news/index.html">Daily News</a> <a class="btn ghost" href="newsletter.html">{name}</a> <a class="btn ghost" href="mission.html">My mission</a></p>
  {spectrum('Neutral', big=True).replace('<p class="label neu">Neutral</p>', '')}
</div></section>
{latest_html}
<section class="section alt" id="what"><div class="wrap narrow">
  <div class="section-head"><p class="kicker">In plain words</p><h2>What is the SGS Index?</h2></div>
  <p class="lede">{e(site['definition'])}</p>
  <p><a class="btn ghost" href="how-it-works.html">How the index works</a> <a class="btn ghost" href="mission.html">Read my mission</a></p>
</div></section>
<section class="section" id="mission"><div class="wrap narrow">
  <div class="section-head"><p class="kicker">My mission</p><h2>News anyone can understand</h2></div>
  <p class="lede">My goal is simple: show you who gains power from each big story, explain it in everyday words, and connect it to your freedom and your money. No hype, no buy or sell calls, and no background needed.</p>
  <p><a class="btn" href="mission.html">Read the full mission</a></p>
</div></section>
<section class="section alt" id="newsletter"><div class="wrap split">
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
  <p class="lede">{e(d.get('tagline', ''))} We count down from #5 to #1, and each story gets a simple label showing which way it moves power.</p></div>
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
  <div class="section-head"><p class="kicker">Daily News</p><h1>Archive</h1><p class="lede">Every Daily SGS Top 5, newest first. Each one counts down the five stories that shifted power the most that day.</p></div>
  <ul class="archive">{items or '<li>No episodes yet.</li>'}</ul></div></section>"""
    write("news/index.html", page("Daily News archive", body, 1, "Daily News", site, rel="news/index.html"))

    # How the index works
    write("how-it-works.html", page("How the index works", how_body(site), 0, "How It Works", site,
                                    desc="How the SGS Index rates a story, in plain words: what I look at, how I keep it honest, and what each label means.",
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
    <li>I find stories on {link_x(site, "X")} News, and each one links to the original source or news report.</li>
    <li>The pictures in each episode are made with AI. None of them show real people.</li>
    <li>The voice is mine, recreated with AI. The background music was made just for the show.</li>
  </ul>
  <h2>Contact</h2>
  <p>Questions, pushback or story ideas? Reach me on {link_x(site, "X")}: {link_x(site, "@" + site["x_handle"])}.</p>
  <p><a class="btn ghost" href="mission.html">Read my mission</a></p>
</div></section>"""
    write("about.html", page("About", body, 0, "About", site, desc=site["about"][0], rel="about.html"))

    # Mission
    write("mission.html", page("My mission", mission_body(site), 0, "Mission", site,
                               desc="What the SGS Index is, what I'll show you, and how I'll explain it so anyone can understand.",
                               rel="mission.html"))

    # Public data index + RSS (labels only). Absolute links use base_url so they
    # stay on the project-site subpath; with no base_url they stay site-relative.
    pub = [{"date": d["date"], "title": d.get("title"), "url": abs_url(site, f"news/{d['date']}/index.html"),
            "stories": [{"rank": s["rank"], "headline": s["headline"], "label": s["label"]} for s in d["stories"]]} for d in days]
    write("days.json", json.dumps(pub, indent=2, ensure_ascii=False))
    rss_items = "".join(f"""<item><title>{e('SGS Top 5 · ' + fmt_date(d['date'], False))}</title><link>{e(abs_url(site, f"news/{d['date']}/index.html"))}</link>
<guid isPermaLink="false">sgs-{d['date']}</guid><pubDate>{dt.datetime.fromisoformat(d['date']).strftime('%a, %d %b %Y 12:00:00 +0000')}</pubDate>
<description>{e(' | '.join('#' + str(s['rank']) + ' ' + s['headline'] + ' (' + s['label'] + ')' for s in d['stories']))}</description></item>""" for d in days)
    write("feed.xml", f'<?xml version="1.0" encoding="UTF-8"?><rss version="2.0"><channel><title>SGS Index · Daily News</title>'
                      f'<link>{e(abs_url(site))}</link><description>Daily world news, rated by who gains power: everyday people and independent nations, or global control.</description>{rss_items}</channel></rss>')


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
