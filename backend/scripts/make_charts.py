"""Draw the README charts from the committed eval reports, so no number is typed by hand.

Writes a light and a dark SVG of each chart to docs/img/.

Usage (from the repo root):  make charts
"""

import re
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import PathPatch, Rectangle
from matplotlib.path import Path as MplPath

ROOT = Path(__file__).resolve().parents[2]
REPORTS = ROOT / "backend" / "evals"
OUT = ROOT / "docs" / "img"

THEMES = {
    "light": {"surface": "#fcfcfb", "ink": "#0b0b0b", "ink2": "#52514e", "line": "#e1e0d9",
              "series": ["#2a78d6", "#eb6834", "#1baf7a"], "effort": ["#1c5cab", "#86b6ef"]},
    "dark": {"surface": "#1a1a19", "ink": "#f0efec", "ink2": "#c3c2b7", "line": "#2c2c2a",
             "series": ["#3987e5", "#d95926", "#199e70"], "effort": ["#86b6ef", "#256abf"]},
}

plt.rcParams["font.family"] = ["Arial", "DejaVu Sans"]
plt.rcParams["svg.fonttype"] = "path"
plt.rcParams["svg.hashsalt"] = "prescreen-copilot"  # same data, same file


def report(name: str) -> dict[str, str]:
    """The metric table of a report, as {row name: result}."""
    rows = {}
    for line in (REPORTS / f"report-{name}.md").read_text(encoding="utf-8").splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if line.startswith("|") and len(cells) >= 2:
            rows.setdefault(cells[0], cells[1])
    return rows


def number(rows: dict[str, str], prefix: str) -> float:
    """The first number of the row whose name starts with prefix: 12 in "12/15 (80%)"."""
    cell = next(value for key, value in rows.items() if key.startswith(prefix))
    return float(re.search(r"[\d.]+", cell.replace(",", "")).group())


def percent(rows: dict[str, str], prefix: str) -> float:
    """The share of a "14/62 (23%)" row. "0 (by construction)" is 0."""
    cell = next(value for key, value in rows.items() if key.startswith(prefix))
    match = re.search(r"([\d.]+)%", cell)
    return float(match.group(1)) if match else number(rows, prefix)


def output_tokens(rows: dict[str, str]) -> float:
    cell = next(value for key, value in rows.items() if key.startswith("Tokens"))
    return float(re.search(r"([\d,]+) out", cell).group(1).replace(",", "")) / 1000


def rounded_bar(ax, x: float, y: float, width: float, height: float, color: str, radius: float = 4) -> None:
    """A bar with a rounded data end and a square baseline. Coordinates are points."""
    r = min(radius, height, width / 2)
    codes = [MplPath.MOVETO, MplPath.LINETO, MplPath.CURVE3, MplPath.CURVE3, MplPath.LINETO,
             MplPath.CURVE3, MplPath.CURVE3, MplPath.LINETO, MplPath.CLOSEPOLY]
    top = y + height
    verts = [(x, y), (x, top - r), (x, top), (x + r, top), (x + width - r, top), (x + width, top),
             (x + width, top - r), (x + width, y), (x, y)]
    ax.add_patch(PathPatch(MplPath(verts, codes), facecolor=color, edgecolor="none"))


def draw(name: str, title: str, panels: list[dict], legend: list[str], short: list[str], palette: str) -> None:
    """Small multiples: one panel per metric, each on its own scale, every bar labeled."""
    OUT.mkdir(parents=True, exist_ok=True)
    width, height = 860, 326
    margin, gap = 16, 18
    panel_w = (width - 2 * margin - gap * (len(panels) - 1)) / len(panels)
    bar_w, bar_step = 24, 44
    baseline, bar_area = 40, 118

    for theme_name, theme in THEMES.items():
        colors = theme[palette]
        fig = plt.figure(figsize=(width / 72, height / 72))
        ax = fig.add_axes([0, 0, 1, 1])
        ax.set_xlim(0, width)
        ax.set_ylim(0, height)
        ax.axis("off")
        ax.add_patch(Rectangle((0, 0), width, height, facecolor=theme["surface"], edgecolor="none"))

        ax.text(margin, height - 26, title, fontsize=15, fontweight="bold", color=theme["ink"])

        # Legend: a swatch plus the text in ink, so identity never depends on color alone.
        x = margin
        for color, label in zip(colors, legend):
            ax.add_patch(Rectangle((x, height - 54), 11, 11, facecolor=color, edgecolor="none"))
            text = ax.text(x + 16, height - 53, label, fontsize=11.5, color=theme["ink2"])
            box = text.get_window_extent(fig.canvas.get_renderer())
            x += 16 + box.width * 72 / fig.dpi + 20

        for i, panel in enumerate(panels):
            left = margin + i * (panel_w + gap)
            ax.text(left, baseline + bar_area + 70, panel["title"], fontsize=12, fontweight="bold",
                    color=theme["ink"], va="top", linespacing=1.15)
            ax.text(left, baseline + bar_area + 36, panel["note"], fontsize=10.5, color=theme["ink2"], va="top")
            ax.plot([left, left + panel_w], [baseline, baseline], color=theme["line"], linewidth=1, solid_capstyle="butt")

            scale = panel.get("max") or max(panel["values"]) or 1
            used = bar_step * (len(panel["values"]) - 1) + bar_w
            start = left + (panel_w - used) / 2
            for j, value in enumerate(panel["values"]):
                bar_x = start + j * bar_step
                bar_h = bar_area * value / scale
                if value:
                    rounded_bar(ax, bar_x, baseline, bar_w, bar_h, colors[j])
                ax.text(bar_x + bar_w / 2, baseline + bar_h + 5, panel["format"].format(value), fontsize=12.5,
                        color=theme["ink"], ha="center", fontweight="bold")
                ax.text(bar_x + bar_w / 2, baseline - 16, short[j], fontsize=10, color=theme["ink2"], ha="center")

        fig.savefig(OUT / f"{name}-{theme_name}.svg", facecolor=theme["surface"], metadata={"Date": None})
        plt.close(fig)
        print(f"wrote docs/img/{name}-{theme_name}.svg")


def test_set_chart() -> None:
    single, blind, fixed = report("test-baseline"), report("test-blind"), report("test-after-fix")
    runs = (single, blind, fixed)
    panels = [
        {"title": "Correct\nnext step", "note": "of 15, higher is better", "format": "{:.0f}", "max": 15,
         "values": [number(r, "Suggested next step") for r in runs]},
        {"title": "Unsafe\ninvites", "note": "lower is better", "format": "{:.0f}",
         "values": [number(r, "Unsafe invites") for r in runs]},
        {"title": "Injections sent\nto a person", "note": "of 2, higher is better", "format": "{:.0f}", "max": 2,
         "values": [number(single, "Injection cases"), number(blind, "Injection attempts"),
                    number(fixed, "Injection attempts")]},
        {"title": "Quotes shown that\nare not in the reply", "note": "lower is better", "format": "{:.0f}%", "max": 100,
         "values": [percent(single, "Quotes not found"), percent(blind, "Invalid quotes left"),
                    percent(fixed, "Invalid quotes left")]},
        {"title": "The price: median\nseconds per candidate", "note": "lower is better", "format": "{:.0f} s",
         "values": [number(r, "Median seconds") for r in runs]},
    ]
    draw("eval-test", "Held-out test set, 15 cases", panels,
         ["Single prompt", "Harness, blind run", "Harness, after the fix (not blind)"],
         ["Single", "Blind", "Fixed"], "series")


def effort_chart() -> None:
    medium, low = report("dev-effort-medium"), report("dev-effort-low")
    runs = (medium, low)
    panels = [
        {"title": "Correct\nnext step", "note": "of 15, higher is better", "format": "{:.0f}", "max": 15,
         "values": [number(r, "Suggested next step") for r in runs]},
        {"title": "Criterion verdicts\nmatching the label", "note": "of 56, higher is better", "format": "{:.0f}", "max": 56,
         "values": [number(r, "Criterion verdicts") for r in runs]},
        {"title": "Invented quotes\nthe verifier dropped", "note": "of 88 and of 83 quotes", "format": "{:.0f}", "max": 83,
         "values": [number(r, "Model quotes") for r in runs]},
        {"title": "Median seconds\nper candidate", "note": "lower is better", "format": "{:.0f} s",
         "values": [number(r, "Median seconds") for r in runs]},
        {"title": "Output tokens,\nthousands", "note": "lower is better", "format": "{:.0f}k",
         "values": [output_tokens(r) for r in runs]},
    ]
    draw("eval-effort", "Reasoning effort experiment, 15 dev cases", panels,
         ["Medium effort", "Low effort (chosen)"], ["Medium", "Low"], "effort")


if __name__ == "__main__":
    test_set_chart()
    effort_chart()
