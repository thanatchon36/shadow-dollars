"""Editorial figure style used throughout the paper.

Design rules (applied consistently):
* One accent colour per figure carries the finding; everything else is grey.
* Titles state the finding, subtitles state units and period.
* Every figure carries its source; simulated figures carry a visible badge.
"""
from __future__ import annotations

import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib import font_manager

from .config import FIGURES, PALETTE

TEXT_WIDTH_IN = 6.3  # LaTeX \textwidth of the paper (A4, 1in margins)


def _pick_font() -> str:
    names = {f.name for f in font_manager.fontManager.ttflist}
    for cand in ("Inter", "IBM Plex Sans", "Source Sans 3", "DejaVu Sans"):
        if cand in names:
            return cand
    return "DejaVu Sans"


FONT = _pick_font()


def apply() -> None:
    mpl.rcParams.update({
        "font.family": FONT,
        "font.size": 8.5,
        "axes.titlesize": 9,
        "axes.labelsize": 8.5,
        "axes.labelcolor": PALETTE["ink"],
        "axes.edgecolor": PALETTE["faint"],
        "axes.linewidth": 0.6,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.grid": True,
        "axes.grid.axis": "y",
        "axes.axisbelow": True,
        "grid.color": PALETTE["grid"],
        "grid.linewidth": 0.6,
        "xtick.color": PALETTE["muted"],
        "ytick.color": PALETTE["muted"],
        "xtick.labelsize": 7.5,
        "ytick.labelsize": 7.5,
        "xtick.major.width": 0.6,
        "ytick.major.width": 0,
        "ytick.major.size": 0,
        "legend.frameon": False,
        "legend.fontsize": 7.5,
        "figure.facecolor": PALETTE["paper"],
        "axes.facecolor": PALETTE["paper"],
        "savefig.facecolor": PALETTE["paper"],
        "savefig.bbox": "tight",
        "savefig.pad_inches": 0.04,
        "pdf.fonttype": 42,
        "ps.fonttype": 42,
        "lines.solid_capstyle": "round",
        "text.color": PALETTE["ink"],
    })


def _extent(fig):
    """Union of the tight bounding boxes of all axes, in figure fraction."""
    fig.canvas.draw()
    r = fig.canvas.get_renderer()
    boxes = [ax.get_tightbbox(r) for ax in fig.axes]
    boxes = [b.transformed(fig.transFigure.inverted()) for b in boxes if b is not None]
    return (min(b.x0 for b in boxes), min(b.y0 for b in boxes),
            max(b.x1 for b in boxes), max(b.y1 for b in boxes))


def _wrap(text: str, fig, fontsize: float) -> str:
    import textwrap
    width = int(fig.get_figwidth() * 72 / (fontsize * 0.52))
    return "\n".join(textwrap.wrap(text, width=width))


def headline(fig, title: str, subtitle: str | None = None, y: float | None = None) -> None:
    """Left-aligned headline + subtitle placed just above everything drawn.

    Call it after all axes, titles and legends exist. ``y`` is ignored (kept
    for backwards compatibility): positions are computed from the rendered
    bounding boxes, so headlines never collide with panel titles.
    """
    x0, _, _, top = _extent(fig)
    pt = 1 / 72 / fig.get_figheight()
    cur = top + 7 * pt
    if subtitle:
        st = fig.text(x0, cur, _wrap(subtitle, fig, 8), ha="left", va="bottom", fontsize=8,
                      color=PALETTE["muted"], linespacing=1.25)
        fig.canvas.draw()
        bb = st.get_window_extent(fig.canvas.get_renderer()).transformed(fig.transFigure.inverted())
        cur = bb.y1 + 3 * pt
    fig.text(x0, cur, title, ha="left", va="bottom", fontsize=10.5, fontweight="bold",
             color=PALETTE["ink"])


def source(fig, text: str, y: float | None = None, simulated: bool = False) -> None:
    """Source note under the figure; simulated figures get a red marker line above it.

    Placing the SIMULATED DATA marker outside the plotting area guarantees that
    it never covers data, labels or reference lines.
    """
    x0, bottom, _, _ = _extent(fig)
    pt = 1 / 72 / fig.get_figheight()
    cur = bottom - 6 * pt
    if simulated:
        fig.text(x0, cur, "SIMULATED DATA  \u00b7  METHOD VALIDATION ONLY", ha="left", va="top", fontsize=6.5,
                 fontweight="bold", color=PALETTE["illicit"])
        cur -= 10 * pt
    fig.text(x0, cur, _wrap(text, fig, 6.5), ha="left", va="top", fontsize=6.5,
             color=PALETTE["muted"], linespacing=1.25)


def simulated_badge(ax, text: str = "SIMULATED DATA  ·  METHOD VALIDATION") -> None:
    ax.text(0.995, 0.985, text, transform=ax.transAxes, ha="right", va="top",
            fontsize=6, fontweight="bold", color=PALETTE["illicit"],
            bbox=dict(boxstyle="round,pad=0.35", fc="white", ec=PALETTE["illicit"], lw=0.7),
            zorder=20)


def end_label(ax, x, y, text, color, dx=4, fontsize=7.5, weight="bold", va="center"):
    ax.annotate(text, xy=(x, y), xytext=(dx, 0), textcoords="offset points",
                ha="left", va=va, fontsize=fontsize, color=color, fontweight=weight,
                annotation_clip=False)


def note(ax, xy, xytext, text, color=None, ha="left", fontsize=7, arrow=True):
    color = color or PALETTE["ink"]
    ax.annotate(text, xy=xy, xytext=xytext, textcoords="data", ha=ha, va="center",
                fontsize=fontsize, color=color,
                arrowprops=dict(arrowstyle="-", lw=0.6, color=PALETTE["muted"],
                                shrinkA=2, shrinkB=2) if arrow else None)


def overlap_report(fig, tol: float = 1.0) -> list[dict]:
    """Detect text that collides with other text or with plotted data lines.

    Every visible, non-empty Text artist (titles, labels, tick labels, legend
    entries, annotations) is compared with every other one, and with the
    densified display-space paths of the data lines in each axes. Texts drawn
    on an opaque background box are treated as deliberate labels and are only
    checked against other text.
    """
    import numpy as np
    from matplotlib.text import Text

    fig.canvas.draw()
    r = fig.canvas.get_renderer()
    # Tick labels outside the view interval exist as objects but are never drawn.
    all_tl, drawn_tl = set(), set()
    for ax in fig.axes:
        for axis in (ax.xaxis, ax.yaxis):
            for tk in axis.get_major_ticks() + axis.get_minor_ticks():
                all_tl.update((id(tk.label1), id(tk.label2)))
            if not ax.axison or not axis.get_visible():
                continue
            try:
                shown = axis._update_ticks()
            except Exception:  # pragma: no cover - private API fallback
                shown = axis.get_major_ticks()
            for tk in shown:
                drawn_tl.update((id(tk.label1), id(tk.label2)))
    texts = []
    for t in fig.findobj(Text):
        if not t.get_visible() or not t.get_text().strip():
            continue
        if id(t) in all_tl and id(t) not in drawn_tl:
            continue
        bb = t.get_window_extent(r)
        if bb.width < 1 or bb.height < 1:
            continue
        texts.append((t, bb.expanded(1.0, 1.0)))
    issues = []
    for i in range(len(texts)):
        a = texts[i][1]
        for j in range(i + 1, len(texts)):
            b = texts[j][1]
            if a.x0 + tol < b.x1 - tol and b.x0 + tol < a.x1 - tol and \
               a.y0 + tol < b.y1 - tol and b.y0 + tol < a.y1 - tol:
                issues.append({"kind": "text-text", "a": texts[i][0].get_text()[:40],
                               "b": texts[j][0].get_text()[:40]})
    for t, bb in texts:
        if t.get_bbox_patch() is not None:
            continue
        for ax in fig.axes:
            for line in ax.get_lines():
                if not line.get_visible() or line.get_linestyle() in ("None", "", " "):
                    continue
                xy = line.get_xydata()
                if len(xy) < 2:
                    continue
                d = line.get_transform().transform(np.asarray(xy, float))
                d = d[np.all(np.isfinite(d), axis=1)]
                if len(d) < 2:
                    continue
                k = np.linspace(0, 1, 12)[:, None, None]
                seg = (d[:-1] * (1 - k) + d[1:] * k).reshape(-1, 2)
                inside = ((seg[:, 0] > bb.x0 + tol) & (seg[:, 0] < bb.x1 - tol) &
                          (seg[:, 1] > bb.y0 + tol) & (seg[:, 1] < bb.y1 - tol))
                if inside.any():
                    pt = seg[inside][0]
                    issues.append({"kind": "text-line", "a": t.get_text()[:40],
                                   "b": f"{line.get_label()} ls={line.get_linestyle()} color={line.get_color()}",
                                   "at_px": [round(float(pt[0])), round(float(pt[1]))]})
                    break
    return issues


QA_LOG: dict = {}


def save(fig, name: str) -> None:
    QA_LOG[name] = overlap_report(fig)
    if QA_LOG[name]:
        print(f"[overlap QA] {name}: {len(QA_LOG[name])} issue(s)")
        for it in QA_LOG[name]:
            print("    ", it)
    fig.savefig(FIGURES / f"{name}.pdf")
    fig.savefig(FIGURES / f"{name}.png", dpi=220)
    plt.close(fig)
