"""Build the web reader docs/paper/ from the LaTeX paper (same text and numbers as the PDF).

pandoc renders the section files in paper/ with paper/reader.html: masthead, abstract, a results strip whose
numbers are read from data/processed/facts_*.json, contents, numbered sections, references and the appendices.
Figure, table, equation, theorem and cross-reference numbers come from the LaTeX run itself (main.aux), so they
match the PDF. The two TikZ diagrams are compiled to PNG. The PDF and the figures the page uses are copied next
to it; GitHub Pages serves docs/ at https://thanatchon36.github.io/shadow-dollars/.

Requires pandoc, tectonic and pdftoppm (poppler) on PATH. Usage: python scripts/build_web.py
"""
from __future__ import annotations

import html
import json
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PAPER = ROOT / "paper"
FIGURES = ROOT / "figures"
PROCESSED = ROOT / "data" / "processed"
OUT = ROOT / "docs" / "paper"

REPO_URL = "https://github.com/thanatchon36/shadow-dollars"
PAPER_URL = "https://thanatchon36.github.io/shadow-dollars/paper/"
TITLE = "Shadow Dollars"
SUBTITLE = "Stablecoin Rails, Scam Finance and the Limits of Detection in Thailand"

# TikZ figures: label -> PNG written next to the page
TIKZ = {"fig:funnel": "fig_funnel.png", "fig:typology": "fig_typology.png"}

WORD = {  # cleveref type -> (singular, plural)
    "section": ("Section", "Sections"), "subsection": ("Section", "Sections"),
    "subsubsection": ("Section", "Sections"), "appendix": ("Appendix", "Appendices"),
    "subappendix": ("Appendix", "Appendices"), "figure": ("Figure", "Figures"), "table": ("Table", "Tables"),
    "equation": ("Equation", "Equations"), "assumption": ("Assumption", "Assumptions"),
    "proposition": ("Proposition", "Propositions"), "corollary": ("Corollary", "Corollaries"),
    "lemma": ("Lemma", "Lemmas"), "definition": ("Definition", "Definitions"), "remark": ("Remark", "Remarks"),
}
THEOREMS = ("assumption", "proposition", "corollary", "lemma", "definition", "remark")


def pct(x: float, nd: int = 0) -> str:
    return f"{100 * x:.{nd}f}%"


ORDINAL = {1: "lowest", 2: "second", 3: "third", 4: "fourth", 5: "fifth", 6: "sixth", 7: "seventh"}


def span(xs) -> str:
    xs = list(xs)
    return f"{100 * min(xs):.0f}\u2013{100 * max(xs):.0f}%"


def results() -> list[tuple[str, str, str, str]]:
    """(label, style, finding, detail). style: pos = public data, ref = simulated (method validation),
    null = pending."""
    r = json.loads((PROCESSED / "facts_real.json").read_text())
    s = json.loads((PROCESSED / "facts_sim.json").read_text())
    tron, eth = r["two_rails"]["USDT \u00b7 Tron"], r["two_rails"]["USDT \u00b7 Ethereum"]
    ev = r["event_results"]
    pmin, pmax = min(e["p_calibrated"] for e in ev), max(e["p_calibrated"] for e in ev)
    und = s["pak"]["undirected_2hop"].values()
    best = [max(s["pak"][k][m] for k in ("iforest_all", "iforest_behaviour")) for m in s["pak"]["iforest_all"]]
    return [
        ("Rails", "pos",
         f"USDT on Tron carries {pct(r['tron_share_last'])} of covered USDT supply "
         f"(US${r['tron_supply_bn']:.0f} bn, {r['supply_last_date']})",
         f"{tron['holders_m']:.1f} million funded addresses, {tron['holders_m'] / eth['holders_m']:.1f} times "
         f"Ethereum; {r['ratio_intensity_tron_over_eth']:.1f} times the transfers per dollar"),
        ("Sanctions", "pos",
         f"{pct(r['ofac_usdt_trx_tron_share'])} of OFAC addresses tagged USDT, TRX or USDC are Tron addresses",
         f"{r['ofac_total']:,} sanctioned digital-currency addresses in the SDN mirror"),
        ("Macro motive", "pos",
         f"Thai inflation {r['cpi_thailand_mean']:.1f}% a year, 2019\u20132023: "
         f"{ORDINAL[r['cpi_rank_thailand']]} lowest of {r['cpi_n']} comparators",
         f"Lao PDR {r['cpi_mekong']['Lao PDR']:.1f}%, Myanmar {r['cpi_mekong']['Myanmar']:.1f}%: the dollar demand "
         "is next door"),
        ("Event studies", "pos",
         f"Nominal 95% bands reject at {pct(r['placebo_overreject'])} of {r['placebo_n']} placebo dates",
         f"placebo-calibrated p-values for three crackdowns: {pmin:.2f} to {pmax:.2f}"),
        ("Graph exposure", "ref",
         f"Undirected two-hop exposure: {span(und)} precision among top-ranked accounts",
         f"multi-signal scoring reaches {span(best)}; simulated exchange-years"),
        ("Bunching test", "ref",
         f"Difference-in-bunching test: size {pct(s['bunch_size'], 1)}, power {pct(s['bunch_power']['0.02'])} "
         "at a 2% mule share",
         f"{s['mc_reps_null']} null draws, {s['mc_reps_per_share']} exchange-years per share; simulated data"),
        ("Thai exchange data", "null", "Account-level results pending",
         "the pre-registered plan runs as soon as exchange or regulator data are available under the PDPA"),
    ]


# ------------------------------------------------------------------------------------------------ LaTeX side

def braced(s: str, i: int) -> tuple[str, int]:
    """Content of the brace group starting at s[i] == '{', and the index after it."""
    assert s[i] == "{", s[i:i + 20]
    depth = 0
    for j in range(i, len(s)):
        depth += {"{": 1, "}": -1}.get(s[j], 0)
        if depth == 0:
            return s[i + 1:j], j + 1
    raise ValueError("unbalanced braces")


def parse_aux(aux: str) -> dict[str, dict]:
    """label -> {type, num, name} from \\newlabel lines (cleveref's @cref entries give the type)."""
    labels: dict[str, dict] = {}
    for line in aux.splitlines():
        if not line.startswith("\\newlabel{"):
            continue
        key, i = braced(line, len("\\newlabel"))
        body, _ = braced(line, i)
        if key.endswith("@cref"):
            m = re.match(r"\{\[(\w+)\]\[[^\]]*\]\[[^\]]*\]([^}]*)\}", body)
            labels.setdefault(key[:-5], {}).update(type=m.group(1), num=m.group(2))
        else:
            num, j = braced(body, 0)
            _, j = braced(body, j)  # page
            name, _ = braced(body, j)
            labels.setdefault(key, {}).update(name=re.sub(r"\\relax\s*$", "", name).strip())
    return {k: v for k, v in labels.items() if "type" in v}


def tex_tools() -> None:
    for tool in ("pandoc", "tectonic", "pdftoppm"):
        if shutil.which(tool) is None:
            raise RuntimeError(f"{tool} not found on PATH")


def compile_labels(build: Path) -> dict[str, dict]:
    """Run tectonic on a copy of the paper (XeTeX ignores \\pdfoutput, which would select pdfTeX drivers)."""
    main = (build / "main.tex").read_text()
    (build / "main.tex").write_text(re.sub(r"^\\pdfoutput=1\s*\n", "", main))
    subprocess.run(["tectonic", "-k", "--chatter=minimal", "main.tex"], cwd=build, check=True,
                   capture_output=True, text=True)
    return parse_aux((build / "main.aux").read_text())


def tikz_blocks(tex: str) -> list[tuple[str, str]]:
    """(label, tikzpicture source) for every figure that draws with TikZ."""
    out = []
    for fig in re.finditer(r"\\begin\{figure\}.*?\\end\{figure\}", tex, re.DOTALL):
        pic = re.search(r"\\begin\{tikzpicture\}.*?\\end\{tikzpicture\}", fig.group(0), re.DOTALL)
        lab = re.search(r"\\label\{([^}]+)\}", fig.group(0))
        if pic and lab:
            out.append((lab.group(1), pic.group(0)))
    return out


def render_tikz(preamble: str, tex: str, build: Path, out_dir: Path) -> None:
    """Compile each TikZ figure as a standalone page with the paper's packages, colours and macros; PNG out."""
    keep = "\n".join(
        line for line in preamble.splitlines()
        # one-line package loads, libraries, colours and macros; not the multi-line hyperref call
        if re.match(r"\\(usepackage(\[[^\]]*\])?\{[^}]+\}|usetikzlibrary|definecolor|newcommand)", line)
        and not re.search(r"\{(arxiv|hyperref|cleveref|caption|natbib|microtype|tcolorbox|float)\}", line)
    )
    # the fonts of paper/arxiv.sty (Times, Helvetica)
    fonts = "\\renewcommand{\\rmdefault}{ptm}\n\\renewcommand{\\sfdefault}{phv}\n"
    for label, pic in tikz_blocks(tex):
        name = TIKZ[label]
        stem = name.removesuffix(".png")
        doc = (f"\\documentclass[border=8pt]{{standalone}}\n{keep}\n{fonts}"
               "\\setlength{\\textwidth}{6.5in}\n\\begin{document}\n" + pic + "\n\\end{document}\n")
        (build / f"{stem}.tex").write_text(doc)
        run = subprocess.run(["tectonic", "--chatter=minimal", f"{stem}.tex"], cwd=build,
                             capture_output=True, text=True)
        if run.returncode:
            raise RuntimeError(f"TikZ figure {label} failed to compile:\n{run.stdout[-2000:]}{run.stderr[-2000:]}")
        subprocess.run(["pdftoppm", "-png", "-r", "220", "-singlefile", f"{stem}.pdf", str(out_dir / stem)],
                       cwd=build, check=True)


def plain_columns(tex: str) -> str:
    """The L{width} column type the paper defines with \\newcolumntype, as p{width}: pandoc does not expand it."""
    out, pos = [], 0
    for m in re.finditer(r"\\begin\{(tabularx\}\{[^}]*|tabular)\}", tex):
        spec, end = braced(tex, m.end())
        out.append(tex[pos:m.end()] + "{" + spec.replace("L{", "p{") + "}")
        pos = end
    return "".join(out) + tex[pos:]


def web_source(main: str, build: Path) -> str:
    """The paper body as pandoc-friendly LaTeX: PNG figures, TikZ as images, references before the appendix."""
    body = main.split("\\begin{document}", 1)[1]
    body = body[body.index("\\input{sec1_intro}"):]
    body = re.sub(r"\\phantomsection\s*|\\addcontentsline\{[^}]*\}\{[^}]*\}\{[^}]*\}\s*", "", body)
    body = re.sub(r"\{\\small\\setlength\{\\bibsep\}.*?\\bibliography\{refs\}\}",
                  r"\\section*{References}\n\\bibliography{refs}", body, flags=re.DOTALL)
    body = body.replace("\\end{document}", "")

    def expand(m: re.Match) -> str:
        tex = (build / f"{m.group(1)}.tex").read_text()
        for label, pic in tikz_blocks(tex):
            tex = tex.replace(pic, f"\\includegraphics{{figures/{TIKZ[label]}}}")
        tex = re.sub(r"\\input\{(tables/[^}]+)\}", lambda t: (build / f"{t.group(1)}.tex").read_text(), tex)
        return plain_columns(tex)

    body = re.sub(r"\\input\{(sec\d_\w+|appendix)\}", expand, body)
    macros = ("\\newcommand{\\fig}[2]{\\includegraphics{figures/#2.png}}\n"
              "\\newcommand{\\E}{\\mathbb{E}}\n\\newcommand{\\1}{\\mathbf{1}}\n")
    return f"\\documentclass{{article}}\n{macros}\\begin{{document}}\n{body}\n\\end{{document}}\n"


def front_matter(main: str) -> dict:
    abstract = re.search(r"\\begin\{abstract\}(.*?)\\end\{abstract\}", main, re.DOTALL).group(1)
    keywords = [k.strip() for k in re.search(r"\\keywords\{(.*?)\}\n", main, re.DOTALL).group(1).split("\\and")]
    jel = re.search(r"JEL codes\}+\\enspace\s*([^\n]+)", main).group(1).strip()
    date = re.search(r"\\date\{([^}]*)\}", main).group(1)
    author = re.search(r"\\author\{([^}\n]*)", main).group(1).strip()
    abstract_html = subprocess.run(["pandoc", "--from=latex", "--to=html5", "--wrap=none"], input=abstract,
                                   capture_output=True, text=True, check=True).stdout
    return dict(abstract=abstract_html, keywords=[re.sub(r"\s+", " ", k) for k in keywords], jel=jel,
                date=date, author=author)


# ------------------------------------------------------------------------------------------------ HTML side

def cut_div(page: str, start: int) -> tuple[str, int]:
    """The balanced <div ...>...</div> starting at page[start], and the index after it."""
    depth, i = 0, start
    for m in re.finditer(r"<div\b|</div>", page[start:]):
        depth += 1 if m.group(0) == "<div" else -1
        if depth == 0:
            i = start + m.end()
            return page[start:i], i
    raise ValueError("unbalanced div")


def number_sections(page: str, labels: dict) -> str:
    """pandoc numbers the appendices 12, 13, ...; LaTeX letters them. Check labelled numbers against main.aux."""
    first_app = re.search(r'<h1 data-number="[^"]+" id="app:', page).start()
    state = {"h1": 0, "h2": 0}

    def header(m: re.Match) -> str:
        level, num, hid = m.group(1), m.group(2), m.group(3)
        if m.start() >= first_app:
            if level == "1":
                state["h1"] += 1
                state["h2"] = 0
            else:
                state["h2"] += 1
            letter = chr(ord("A") + state["h1"] - 1)
            num = letter if level == "1" else f"{letter}.{state['h2']}"
        if hid in labels and labels[hid]["num"] != num:
            raise RuntimeError(f"section {hid}: web {num}, PDF {labels[hid]['num']}")
        renum[hid] = num
        return (f'<h{level} data-number="{num}" id="{hid}"><span class="header-section-number">{num}</span>')

    renum: dict[str, str] = {}
    page = re.sub(r'<h([12]) data-number="([^"]+)" id="([^"]+)"><span class="header-section-number">[^<]*</span>',
                  header, page)
    return re.sub(r'(<a href="#([^"]+)" id="toc-[^"]+"><span class="toc-section-number">)[^<]*',
                  lambda m: m.group(1) + renum.get(m.group(2), ""), page)


def cross_refs(page: str, labels: dict) -> str:
    def ref(m: re.Match) -> str:
        kind, keys = m.group(2), m.group(3).split(",")
        missing = [k for k in keys if k not in labels]
        if missing:
            raise RuntimeError(f"unresolved reference {missing}")
        types = {labels[k]["type"] for k in keys}
        nums = [labels[k]["num"] for k in keys]
        if types == {"equation"}:
            nums = [f"({n})" for n in nums]
        text = nums[0] if len(nums) == 1 else ", ".join(nums[:-1]) + " and " + nums[-1]
        if kind.startswith("ref+"):
            singular, plural = WORD[sorted(types)[0]] if len(types) == 1 else ("", "")
            if len(types) == 1:
                text = f"{singular if len(nums) == 1 else plural} {text}"
            else:  # mixed types: each with its own word
                parts = [f"{WORD[labels[k]['type']][0]} {labels[k]['num']}" for k in keys]
                text = ", ".join(parts[:-1]) + " and " + parts[-1]
            # cleveref is loaded with [capitalise]: \cref and \Cref both print a capitalised name
        return f'<a href="#{keys[0]}" class="xref">{text}</a>'

    return re.sub(r'<a href="#([^"]+)" data-reference-type="([^"]+)" data-reference="([^"]+)">[^<]*</a>', ref, page)


def theorems(page: str, labels: dict) -> str:
    count = {t: 0 for t in THEOREMS}

    def thm(m: re.Match) -> str:
        kind, key = m.group(1), m.group(3)
        count[kind] += 1
        num = str(count[kind]) if kind != "assumption" else f"A{count[kind]}"
        name = ""
        if key:
            if labels[key]["num"] != num:
                raise RuntimeError(f"{key}: web {num}, PDF {labels[key]['num']}")
            name = labels[key].get("name", "")
        head = f"{WORD[kind][0]} {num}" + (f" ({html.escape(name)})" if name else "") + "."
        return f'{m.group(0)}<span class="thm-head">{head}</span> '

    return re.sub(r'<div class="(%s)">\s*<p>(<span id="([^"]+)" data-label="[^"]+"></span>\s*)?'
                  % "|".join(THEOREMS), thm, page)


def equations(page: str, labels: dict) -> str:
    def eq(m: re.Match) -> str:
        key = re.search(r"\\label\{([^}]+)\}", m.group(0))
        if not key:
            return m.group(0)
        key = key.group(1)
        return (f'<span class="eq" id="{key}">{m.group(0)}'
                f'<span class="eqno">({labels[key]["num"]})</span></span>')

    return re.sub(r'<math display="block".*?</math>', eq, page, flags=re.DOTALL)


def floats(page: str, labels: dict) -> str:
    def figure(m: re.Match) -> str:
        key = m.group(1)
        return f'<figure id="{key}"{m.group(2)}<figcaption><b>Figure {labels[key]["num"]}.</b> '

    page = re.sub(r'<figure id="([^"]+)" data-latex-placement="[^"]*"(>.*?)<figcaption>', figure, page,
                  flags=re.DOTALL)

    def table(m: re.Match) -> str:
        key, cap, rows = m.group(1), m.group(2), m.group(3)
        return (f'<div class="tbl" id="{key}"><p class="tcap"><b>Table {labels[key]["num"]}.</b> {cap}</p>'
                f'<div class="tscroll"><table>{rows}</table></div></div>')

    page = re.sub(r'<div id="(tab:[^"]+)">\s*<table[^>]*>\s*<caption>(.*?)</caption>(.*?)</table>\s*</div>',
                  table, page, flags=re.DOTALL)
    page = re.sub(r"<colgroup>.*?</colgroup>\s*", "", page, flags=re.DOTALL)
    # uncaptioned tables (the replication commands) scroll sideways too
    page = re.sub(r'(?<!<div class="tscroll">)(<table>.*?</table>)', r'<div class="tscroll">\1</div>', page,
                  flags=re.DOTALL)

    def img(m: re.Match) -> str:
        tag = re.sub(r'\s(?:style|width|height)="[^"]*"', "", m.group(0))
        return tag.replace("<img ", '<img loading="lazy" ', 1)

    return re.sub(r"<img\b[^>]*>", img, page)


def move_references(page: str) -> str:
    start = page.index('<div id="refs"')
    refs, end = cut_div(page, start)
    page = page[:start] + page[end:]
    head = re.search(r'<h1 class="unnumbered" id="references">References</h1>', page)
    return page[:head.end()] + "\n" + refs + page[head.end():]


def check(page: str, labels: dict) -> None:
    for key, v in labels.items():
        if v["type"] in ("figure", "table") and f'id="{key}"' not in page:
            raise RuntimeError(f"{v['type']} {key} missing from the web page")
    left = re.findall(r"\[(?:fig|tab|sec|app|eq|prop|cor|lem|as):[^\]]*\]", page)
    if left:
        raise RuntimeError(f"unresolved labels in the page: {left[:5]}")


def build() -> Path:
    tex_tools()
    main = (PAPER / "main.tex").read_text()
    preamble = main.split("\\begin{document}", 1)[0]
    fm = front_matter(main)
    with tempfile.TemporaryDirectory() as tmp:
        build = Path(tmp) / "paper"
        shutil.copytree(PAPER, build)
        labels = compile_labels(build)
        (OUT / "figures").mkdir(parents=True, exist_ok=True)
        for f in (OUT / "figures").glob("*.png"):
            f.unlink()
        render_tikz(preamble, (build / "sec4_framework.tex").read_text(), build, OUT / "figures")
        (build / "figures").mkdir(exist_ok=True)
        for png in FIGURES.glob("fig_*.png"):
            shutil.copyfile(png, build / "figures" / png.name)
        for name in TIKZ.values():
            shutil.copyfile(OUT / "figures" / name, build / "figures" / name)
        (build / "_web.tex").write_text(web_source(main, build))
        meta = {
            "title": TITLE, "subtitle": SUBTITLE, "author": [fm["author"]], "date": fm["date"],
            "keywords": fm["keywords"], "jel": fm["jel"], "pagetitle": TITLE,
            "description": "Preprint: stablecoin rails, scam finance and the limits of detection in Thailand.",
        }
        (build / "_meta.json").write_text(json.dumps(meta))
        page = subprocess.run(
            ["pandoc", "_web.tex", "--from=latex", "--to=html5", "--mathml", "--wrap=none", "--standalone",
             "--template=reader.html", "--number-sections", "--toc", "--toc-depth=1", "--citeproc",
             "--bibliography=refs.bib", "--metadata-file=_meta.json"],
            capture_output=True, text=True, check=True, cwd=build,
        ).stdout
        used = sorted(set(re.findall(r'src="figures/([\w.-]+)"', page)))
        for name in used:
            if name not in TIKZ.values():
                shutil.copyfile(FIGURES / name, OUT / "figures" / name)

    page = re.sub(r'(<div class="abstract-body">).*?(</div>)', lambda m: m.group(1) + fm["abstract"] + m.group(2),
                  page, count=1, flags=re.DOTALL)
    page = number_sections(page, labels)
    page = cross_refs(page, labels)
    page = theorems(page, labels)
    page = equations(page, labels)
    page = floats(page, labels)
    page = move_references(page)
    check(page, labels)

    items = "\n".join(
        f'<li class="r r-{style}"><span class="r-id">{html.escape(label)}</span>'
        f'<span class="r-text">{html.escape(finding)}<small>{html.escape(detail)}</small></span></li>'
        for label, style, finding, detail in results()
    )
    actions = (
        '<li><a href="paper.pdf">Download PDF</a></li>'
        f'<li><a href="{REPO_URL}">Code and replication</a></li>'
        f'<li><a href="{REPO_URL}/tree/main/data">Data and manifest</a></li>'
    )
    bib = (
        "@misc{chongmankhong2026shadowdollars,\n"
        "  author = {Chongmankhong, Thanatchon},\n"
        f"  title  = {{{TITLE}: {SUBTITLE}}},\n"
        "  year   = {2026},\n"
        "  note   = {Preprint},\n"
        f"  url    = {{{PAPER_URL}}}\n"
        "}"
    )
    colophon = (
        "<p>Rendered from the LaTeX source in <code>paper/</code> by <code>scripts/build_web.py</code> "
        "(<code>make web</code>). Figure, table, equation and section numbers come from the LaTeX run, and the "
        "results strip reads <code>data/processed/facts_*.json</code>, the same files the paper quotes. "
        "The PDF is authoritative. Results marked simulated validate methods against planted ground truth and "
        "are not evidence about real markets.</p>"
    )
    for marker, value in (
        ("<!--ACTIONS-->", actions),
        ("<!--RESULTS-NOTE-->", (
            "Headline numbers, read from the result files. Green: public on-chain, sanctions and macro data; "
            "amber: simulation (method validation only); grey: pending."
        )),
        ("<!--RESULTS-->", items),
        ("<!--CITE-->", f"<h2>How to cite</h2><pre><code>{html.escape(bib)}</code></pre>"),
        ("<!--COLOPHON-->", colophon),
    ):
        if marker not in page:
            raise RuntimeError(f"reader.html lacks {marker}")
        page = page.replace(marker, value)

    (OUT / "index.html").write_text(page, encoding="utf-8")
    shutil.copyfile(PAPER / "paper.pdf", OUT / "paper.pdf")
    return OUT / "index.html"


if __name__ == "__main__":
    print("web reader ->", build().relative_to(ROOT))
