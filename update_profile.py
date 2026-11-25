#!/usr/bin/env python3
"""Render the profile's public GitHub activity. Only Python's stdlib is required."""
from __future__ import annotations

from collections import Counter
from datetime import date
from html import escape
import json
import os
from pathlib import Path
import urllib.error
import urllib.parse
import urllib.request

ASSETS = Path(__file__).resolve().parent
WIDTH = 1120
BG, BORDER, TEXT, MUTED = "#101a2b", "#34425f", "#edf4ff", "#a9b8d1"
CYAN, VIOLET, BLUE = "#59e4f8", "#a99bff", "#76a9ff"
COLORS = ["#477bea", "#f1a55d", "#72d5f9", "#a99bff", "#6fceaa", "#788ba6"]


def svg_start(height: int, label: str) -> str:
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{height}" '
        f'viewBox="0 0 {WIDTH} {height}" role="img" aria-label="{escape(label, quote=True)}">'
        f'<rect x=".75" y=".75" width="{WIDTH-1.5}" height="{height-1.5}" rx="14" '
        f'fill="{BG}" stroke="{BORDER}" stroke-width="1.5"/>'
    )


def txt(x, y, value, *, size=20, color=TEXT, bold=False, mono=False, anchor="start"):
    family = "monospace" if mono else "Arial, Helvetica, sans-serif"
    weight = "700" if bold else "400"
    return (
        f'<text x="{x}" y="{y}" font-family="{family}" font-size="{size}" '
        f'font-weight="{weight}" fill="{color}" text-anchor="{anchor}">{escape(str(value))}</text>'
    )


def save(name: str, body: str) -> None:
    ASSETS.mkdir(exist_ok=True)
    (ASSETS / ("ionut-" + name)).write_text(body + "\n", encoding="utf-8")


def metrics(total: int, repositories: int, active: int, as_of: date) -> str:
    out = [svg_start(180, f"{total} contributions, {repositories} public repositories, {active} active contribution days.")]
    out += [txt(28, 32, "GITHUB // ACTIVITY", color=CYAN, mono=True, size=15, bold=True),
            txt(1090, 32, f"UPDATED {as_of:%d %b %Y}".upper(), size=13, color=MUTED, mono=True, anchor="end")]
    for index, (number, title, subtitle, color) in enumerate([
        (total, "Contributions", "PAST 12 MONTHS", CYAN),
        (repositories, "Public repositories", "ON GITHUB", VIOLET),
        (active, "Active days", "PAST 12 MONTHS", BLUE),
    ]):
        x = 28 + index * 360
        out += [
            f'<rect x="{x}" y="48" width="344" height="109" rx="9" fill="#0b1423" stroke="#2b3a54"/>',
            f'<path d="M{x+1} 83V58q0-9 9-9h28" fill="none" stroke="{color}" stroke-width="2"/>',
            txt(x + 17, 109, number, size=43, bold=True, color=color),
            txt(x + 110, 89, title, size=19, bold=True),
            txt(x + 110, 114, subtitle, size=12, color=MUTED, mono=True),
        ]
    return "".join(out) + "</svg>"


def languages(mix: Counter) -> str:
    if not mix:
        out = [svg_start(137, "Core languages: C++, Java, Python. Language mix will refresh automatically.")]
        out.append(txt(27, 32, "LANGUAGES // CORE STACK", size=15, color=CYAN, mono=True, bold=True))
        for i, (label, color) in enumerate([("C++", COLORS[0]), ("Java", COLORS[1]), ("Python", COLORS[2])]):
            x = 28 + i * 360
            out += [f'<rect x="{x}" y="50" width="344" height="49" rx="8" fill="#0b1423" stroke="#2b3a54"/>',
                    f'<circle cx="{x+23}" cy="74" r="6" fill="{color}"/>',
                    txt(x + 40, 81, label, bold=True, size=21)]
        out.append(txt(28, 121, "No language statistics available for eligible public projects.", size=13, color=MUTED))
        return "".join(out) + "</svg>"

    ranked = [(name, n) for name, n in mix.most_common() if n > 0]
    total = sum(n for _, n in ranked)
    if total <= 0:
        return languages(Counter())
    shown = ranked[:4]
    if len(ranked) > 4:
        shown.append(("Other", sum(n for _, n in ranked[4:])))
    out = [svg_start(153, "Language mix by bytes across public non-fork projects: " +
                     ", ".join(f"{name} {value/total:.1%}" for name, value in shown))]
    out += [txt(28, 32, "LANGUAGES // PUBLIC PROJECTS", size=15, color=CYAN, mono=True, bold=True),
            txt(1090, 32, "BYTES OF CODE", size=13, color=MUTED, mono=True, anchor="end"),
            '<clipPath id="bar"><rect x="28" y="49" width="1064" height="17" rx="8.5"/></clipPath>',
            '<g clip-path="url(#bar)">']
    x = 28.0
    for i, (name, n) in enumerate(shown):
        w = n / total * 1064
        color = {"C++": COLORS[0], "Java": COLORS[1], "Python": COLORS[2]}.get(name, COLORS[3+i % 3])
        out.append(f'<rect x="{x:.2f}" y="49" width="{w:.2f}" height="17" fill="{color}"/>')
        x += w
    out.append("</g>")
    for i, (name, n) in enumerate(shown):
        x = 28 + (i % 3) * 360
        y = 93 + (i // 3) * 32
        color = {"C++": COLORS[0], "Java": COLORS[1], "Python": COLORS[2]}.get(name, COLORS[3+i % 3])
        label = name if len(name) <= 21 else name[:20] + "…"
        out += [f'<circle cx="{x+7}" cy="{y-6}" r="5.5" fill="{color}"/>',
                txt(x + 20, y, label, size=17, bold=True),
                txt(x + 310, y, f"{n/total:.1%}", size=15, color=MUTED, anchor="end")]
    return "".join(out) + "</svg>"


def snake(weeks: list[list[dict]], total: int) -> str:
    active = sum(int(d["contributionCount"]) > 0 for week in weeks for d in week)
    # Move left-to-right on one row and right-to-left on the next. This keeps
    # the body connected while it crosses the contribution grid.
    num_cols = max(1, len(weeks))
    step_x = 1058 / num_cols
    step_y = 18
    x0, y0 = 31, 58
    side = min(13.5, step_x - 2)
    path = [(col, row) for row in range(7)
            for col in (range(num_cols) if row % 2 == 0 else range(num_cols - 1, -1, -1))]
    index = {pos: i for i, pos in enumerate(path)}
    duration = max(15, len(path) * 0.12)
    out = [svg_start(235, f"Contribution snake: {total} contributions across {active} active days.")]
    out += ['<style>@media (prefers-reduced-motion: reduce) {.moving-snake{display:none} .activity-dot{fill-opacity:1!important}}</style>',
            txt(28, 31, "CONTRIBUTION GRID // SNAKE MODE", size=15, color=CYAN, bold=True, mono=True),
            txt(1090, 31, f"{total} CONTRIBUTIONS  /  {active} ACTIVE DAYS", size=13, color=MUTED, mono=True, anchor="end")]
    counts = {(column, int(day["weekday"])): int(day["contributionCount"])
              for column, week in enumerate(weeks) for day in week}
    max_count = max(counts.values(), default=1) or 1
    palette = ["#26354b", "#305b82", "#3f8daa", "#52bed7", "#76edfb"]
    for (c, r), n in counts.items():
        x, y = x0 + c * step_x, y0 + r * step_y
        level = min(4, (n * 4 + max_count - 1) // max_count) if n else 0
        shape = f'<rect class="activity-dot" x="{x:.2f}" y="{y:.2f}" width="{side:.2f}" height="{side:.2f}" rx="2.4" fill="{palette[level]}"'
        visit = (index[c, r] - 5) % len(path)
        if n and 0 < visit < len(path) - 1:
            t = visit / len(path)
            t2 = (visit + 1) / len(path)
            out.append(f'{shape}><animate attributeName="fill-opacity" values="1;1;0.18;0.18;1" keyTimes="0;{t:.6f};{t2:.6f};0.999;1" dur="{duration:.2f}s" repeatCount="indefinite"/></rect>')
        else:
            out.append(shape + "/>")
    out.append('<g class="moving-snake">')
    # The connecting path makes the moving body continuous. Start with all
    # six segments visible on the first row rather than across the wrap.
    connections = []
    for frame in range(len(path)):
        coords = [path[(frame+5-tail) % len(path)] for tail in range(5, -1, -1)]
        commands = []
        last = None
        for c, r in coords:
            command = "L" if last and abs(c-last[0])+abs(r-last[1]) == 1 else "M"
            commands.append(f"{command}{x0+c*step_x+side/2:.2f},{y0+r*step_y+side/2:.2f}")
            last = (c, r)
        connections.append(" ".join(commands))
    out.append(f'<path d="{connections[0]}" fill="none" stroke="#936eea" stroke-width="8" stroke-linecap="round" stroke-linejoin="round"><animate attributeName="d" calcMode="discrete" values="{";".join(connections)}" dur="{duration:.2f}s" repeatCount="indefinite"/></path>')
    for tail in range(5, -1, -1):
        points = [path[(i+5-tail) % len(path)] for i in range(len(path))]
        xy = [f"{x0 + c*step_x:.2f},{y0+r*step_y:.2f}" for c, r in points]
        body_size = side + 0.9 if tail == 0 else side - tail * .55
        inset = (side - body_size) / 2
        initial = xy[0]
        color = "#bcadff" if tail == 0 else "#936eea"
        out.append(f'<g transform="translate({initial})"><animateTransform attributeName="transform" type="translate" calcMode="discrete" values="{";".join(xy)}" dur="{duration:.2f}s" repeatCount="indefinite"/>'
                   f'<rect x="{inset:.2f}" y="{inset:.2f}" width="{body_size:.2f}" height="{body_size:.2f}" rx="3" fill="{color}" stroke="#d8d2ff" stroke-width="{0.8 if tail == 0 else 0}"/>')
        if tail == 0:
            out.append(f'<circle cx="{side*.7:.2f}" cy="{side*.33:.2f}" r="1.5" fill="#171127"/><circle cx="{side*.7:.2f}" cy="{side*.68:.2f}" r="1.5" fill="#171127"/>')
        out.append("</g>")
    out += ["</g>", txt(28, 214, "01  /  EVERY COMMIT COUNTS", color=MUTED, size=13, mono=True)]
    for i, col in enumerate(palette):
        out.append(f'<rect x="{997+i*18}" y="200" width="13" height="13" rx="2" fill="{col}"/>')
    return "".join(out) + "</svg>"


def api(url: str, token: str, payload=None):
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    headers = {"Accept": "application/vnd.github+json", "User-Agent": "borceaionut-profile-graphics"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if data:
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers)
    with urllib.request.urlopen(req, timeout=30) as response:
        return json.load(response)


def public_rest(path, token):
    url = "https://api.github.com" + path
    try:
        return api(url, token)
    except urllib.error.HTTPError as err:
        # Public resources do not require authentication. In case a repository
        # token cannot access another public repository, use anonymous lookup.
        if token and err.code in (401, 403, 404):
            return api(url, "")
        raise


def read_github(login: str, token: str):
    """Read visible contribution counts and public project languages; never private repositories."""
    query = """query($login:String!){
      user(login:$login){
        contributionsCollection{
          contributionCalendar{
            totalContributions
            weeks{ contributionDays{ date weekday contributionCount } }
          }
        }
      }
    }"""
    reply = api("https://api.github.com/graphql", token, {"query": query, "variables": {"login": login}})
    if reply.get("errors") or not reply.get("data", {}).get("user"):
        raise RuntimeError("GitHub contribution calendar could not be retrieved")
    calendar = reply["data"]["user"]["contributionsCollection"]["contributionCalendar"]
    weeks = [week["contributionDays"] for week in calendar["weeks"]]
    mix = Counter()
    repos = []
    encoded_login = urllib.parse.quote(login, safe="")
    for page in range(1, 101):
        batch = public_rest(f"/users/{encoded_login}/repos?type=owner&per_page=100&page={page}", token)
        repos += [r for r in batch if not r.get("private") and r.get("visibility", "public") == "public"]
        if len(batch) < 100:
            break
    else:
        raise RuntimeError("Repository pagination limit reached")
    for repo in repos:
        if repo.get("fork") or repo["name"].lower() == login.lower():
            continue
        owner, name = (urllib.parse.quote(p, safe="") for p in repo["full_name"].split("/", 1))
        mix.update(public_rest(f"/repos/{owner}/{name}/languages", token))
    return weeks, int(calendar["totalContributions"]), len(repos), mix


def main():
    token = os.environ["GH_TOKEN"]
    login = os.environ["PROFILE_LOGIN"]
    weeks, total, repositories, mix = read_github(login, token)
    today = date.today()
    active = sum(int(d["contributionCount"]) > 0 for w in weeks for d in w)
    # Render all cards first; a failed API fetch never overwrites the last
    # successful set of images.
    renders = {
        "metrics.svg": metrics(total, repositories, active, today),
        "languages.svg": languages(mix),
        "snake.svg": snake(weeks, total),
    }
    for filename, rendered in renders.items():
        save(filename, rendered)
    print(f"Updated profile graphics: {total} contributions, {repositories} public repositories, {active} active days.")


if __name__ == "__main__":
    main()
