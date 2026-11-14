#!/usr/bin/env python3
"""docs-src/ 의 markdown 원고를 docs/ 의 정적 HTML 로 바꾼다.

    python3 tools/build_docs.py --n2h /경로/ndhmd2html.py

* ndhmd 방언 원고(설명서·사양서·빠른 시작)는 ndhmd2html 로 변환한다.
  - 설명서에 raw LaTeX(tblr) 로 적힌 표는 변환 전에 파이프 표로 바꾼 사본을 쓴다
    (원고 자체는 건드리지 않는다).
* 변경 이력(CHANGELOG)은 일반 markdown 이라 pandoc(-f gfm)으로 변환한다.
* 결과: docs/*.html, docs/search-index.json
  (docs/docs.css, docs/docs.js 는 손으로 쓰는 파일이라 건드리지 않는다)

ndhmd2html 위치는 --n2h, 환경변수 NDHMD2HTML, PATH 의 ndhmd2html(.py) 순으로 찾는다.
"""
import argparse
import html
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "docs-src"
OUT = ROOT / "docs"

# slug, 원고, 쪽 제목, 부제, 종류, 표 전처리, 절 번호
DOCS = [
    dict(slug="quickstart", src="quickstart.md", kind="ndhmd",
         title="빠른 시작", sub="ndhmdSuite 설치부터 첫 PDF까지",
         group="start", number=False),
    dict(slug="ndhmdwriter-manual", src="ndhmdwriter-manual.md", kind="ndhmd",
         title="ndhmdWriter 설명서 (참조편)", sub="ndhmdWriter 0.9.5 기준 · 메뉴와 화면 순서로 적은 기능 사전",
         group="ref", number=True, tblr=True),
    dict(slug="ndhmd4tex-dialect-guide", src="ndhmd4tex-dialect-guide.md", kind="ndhmd",
         title="ndhmd4tex 방언 사양서", sub="ndhmd4tex 0.22 기준 · ndhmarkdown 문법 전체",
         group="ref", number=False),
    dict(slug="ndhmdwriter-changelog", src="ndhmdwriter-changelog.md", kind="gfm",
         title="ndhmdwriter 변경 이력", sub="최신 항목이 위에 있습니다",
         group="log", number=False),
    dict(slug="ndhmd4tex-changelog", src="ndhmd4tex-changelog.md", kind="gfm",
         title="ndhmd4tex · ndhmd2html 변경 이력", sub="최신 항목이 위에 있습니다",
         group="log", number=False),
]

CARDS = [
    ("start", "처음 시작하기", [
        ("quickstart", "빠른 시작", "ndhmdSuite를 설치하고 첫 PDF를 뽑기까지만 다룬 짧은 안내.")]),
    ("ref", "참조 문서", [
        ("ndhmdwriter-manual", "ndhmdWriter 설명서",
         "화면 구성, 서랍, 편집창, 찾기, 도구, 컴파일, PDF 연동, 환경설정, 단축키까지 메뉴 순서로 적은 사전."),
        ("ndhmd4tex-dialect-guide", "ndhmd4tex 방언 사양서",
         "ndhmarkdown 문법 전체: front matter, 헤딩, 수식, 표, 그림, 상호참조, 커스텀 환경, mapping.yaml 등.")]),
    ("log", "변경 이력", [
        ("ndhmdwriter-changelog", "ndhmdwriter 변경 이력", "버전별 수정 내용 전체."),
        ("ndhmd4tex-changelog", "ndhmd4tex · ndhmd2html 변경 이력", "버전별 수정 내용 전체.")]),
]


# ───────────────────────── tblr → 파이프 표 ─────────────────────────

FENCE_RE = re.compile(r"^\s{0,3}(`{3,}|~{3,})")


def _match_brace(s, i):
    """s[i] == '{' 일 때 짝이 되는 '}' 의 위치."""
    depth = 0
    j = i
    while j < len(s):
        c = s[j]
        if c == "\\":
            j += 2
            continue
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return j
        j += 1
    raise ValueError("중괄호가 닫히지 않았다")


SIMPLE_CMDS = {
    "textbackslash": "\\", "textasciicircum": "^", "textasciitilde": "~",
    "textasciigrave": "`", "allowbreak": "", "textbar": "|",
}
MD_SPECIAL = re.compile(r"([\\`*_<>|#])")
warnings = []


def tex_inline(s, in_code=False):
    """tblr 칸 안의 LaTeX 조각을 markdown 으로."""
    out = []
    i = 0
    while i < len(s):
        c = s[i]
        if c == "\\":
            m = re.match(r"\\([A-Za-z]+)", s[i:])
            if not m:                       # \{ \} \_ \% \& \# \$ \, ...
                nxt = s[i + 1] if i + 1 < len(s) else ""
                if nxt in ",;:!/ ":
                    out.append(" " if nxt != "/" else "")
                else:
                    out.append(nxt if in_code else MD_SPECIAL.sub(r"\\\1", nxt))
                i += 2
                continue
            name = m.group(1)
            i += 1 + len(name)
            if name in SIMPLE_CMDS:
                v = SIMPLE_CMDS[name]
                out.append(v if in_code else MD_SPECIAL.sub(r"\\\1", v))
                if i < len(s) and s[i:i + 2] == "{}":
                    i += 2
                continue
            if i < len(s) and s[i] == "{":
                j = _match_brace(s, i)
                arg = s[i + 1:j]
                i = j + 1
                if name == "texttt":
                    inner = tex_inline(arg, in_code=True)
                    if "`" in inner:
                        out.append("`` " + inner + " ``")
                    elif inner.strip():
                        out.append("`" + inner + "`")
                elif name == "textbf":
                    out.append("**" + tex_inline(arg) + "**")
                elif name in ("emph", "textit"):
                    out.append("*" + tex_inline(arg) + "*")
                elif name == "ref":
                    out.append("[#" + arg + "]")
                else:
                    warnings.append(f"알 수 없는 명령 \\{name}")
                    out.append(tex_inline(arg, in_code))
                continue
            warnings.append(f"알 수 없는 명령 \\{name}")
            continue
        if c in "{}":
            i += 1
            continue
        if c == "~":
            out.append(" ")
        elif in_code:
            out.append(c)
        else:
            out.append(MD_SPECIAL.sub(r"\\\1", c))
        i += 1
    return "".join(out)


def cell_md(raw):
    t = tex_inline(re.sub(r"\s+", " ", raw.strip()))
    return re.sub(r"(?<!\\)\|", r"\\|", t)


def tblr_to_pipe(block):
    """\\begin{tblr}{...} ... \\end{tblr} 하나를 파이프 표 문자열로."""
    m = re.search(r"\\begin\{tblr\}\s*\{", block)
    pre_open = m.end() - 1
    pre_close = _match_brace(block, pre_open)
    body = block[pre_close + 1:block.rindex("\\end{tblr}")]
    body = re.sub(r"\\(toprule|bottomrule)\b", "", body)
    parts = re.split(r"\\midrule\b", body)
    rows_of = lambda txt: [r for r in re.split(r"\\\\\s*(?:\n|$)", txt) if r.strip()]
    if len(parts) >= 2:
        head, rest = rows_of(parts[0]), rows_of(parts[1])
        header, rows = head[0], head[1:] + rest
    else:
        allrows = rows_of(body)
        header, rows = allrows[0], allrows[1:]

    def split_cells(r):
        return [cell_md(x) for x in re.split(r"(?<!\\)&", r)]

    hc = split_cells(header)
    n = len(hc)
    lines = ["| " + " | ".join(hc) + " |", "|" + "|".join(["---"] * n) + "|"]
    for r in rows:
        cs = split_cells(r)
        cs = (cs + [""] * n)[:n]
        lines.append("| " + " | ".join(cs) + " |")
    return "\n".join(lines)


def convert_tblr(md):
    lines = md.split("\n")
    out = []
    i = 0
    fence = None
    count = 0
    while i < len(lines):
        ln = lines[i]
        fm = FENCE_RE.match(ln)
        if fence is None and fm:
            fence = fm.group(1)
        elif fence is not None and fm and fm.group(1)[0] == fence[0] and len(fm.group(1)) >= len(fence) \
                and ln.strip() == fm.group(1):
            fence = None
        if fence is None and re.match(r"\s*(\\noindent\s*)?\\begin\{tblr\}", ln):
            j = i
            while "\\end{tblr}" not in lines[j]:
                j += 1
            block = "\n".join(lines[i:j + 1]).replace("\\noindent", "", 1)
            out.append(tblr_to_pipe(block))
            count += 1
            i = j + 1
            continue
        out.append(ln)
        i += 1
    return "\n".join(out), count


def unnumber_appendices(md):
    """'# 부록 A. …' 헤딩은 이미 이름에 번호가 있으니 자동 장 번호를 붙이지 않는다."""
    def rep(m):
        attr = (m.group(3) or "").strip()
        if attr.startswith("#"):
            attr = "label=" + attr[1:]
        extra = ", " + attr if attr else ""
        return f"{m.group(1)}{m.group(2)} {{unnumbered{extra}}}"
    return re.sub(r"^(# )(부록 .+?)(?:[ \t]*\{([^}]*)\})?[ \t]*$", rep, md, flags=re.M)


def uncomment_missing_figure(md, srcdir):
    """주석 속 ASCII 그림 + 없는 PDF 그림 한 쌍을, 코드 블록 하나로 바꾼다."""
    pat = re.compile(r"<!--\s*\n(```verb\n.*?\n```)\s*\n-->\s*\n+!\[[^\]]*\]\(([^)]+)\)", re.S)

    def rep(m):
        if (srcdir / m.group(2)).exists():
            return m.group(0)
        return m.group(1).replace("```verb", "```text", 1)

    return pat.sub(rep, md)


# ───────────────────────── 변환 ─────────────────────────

def n2h_cmd(arg):
    cand = arg or os.environ.get("NDHMD2HTML") or shutil.which("ndhmd2html") or shutil.which("ndhmd2html.py")
    if not cand:
        sys.exit("ndhmd2html 을 찾을 수 없습니다. --n2h 로 경로를 알려 주세요.")
    return [sys.executable, "-I", cand] if cand.endswith(".py") else [cand]


def run_ndhmd(cmd, md_text, spec, tmp):
    stem = spec["slug"]
    srcfile = tmp / f"{stem}.md"
    srcfile.write_text(md_text, encoding="utf-8")
    outfile = tmp / f"{stem}.body.html"
    args = cmd + [str(srcfile), "--body-only", "--default", "NONE", "--no-simple-css", "-o", str(outfile)]
    if not spec["number"]:
        args.append("--no-number-sections")
    r = subprocess.run(args, capture_output=True, text=True, cwd=tmp)
    if r.returncode != 0:
        sys.exit(f"{spec['src']} 변환 실패:\n{r.stderr}")
    for ln in r.stderr.splitlines():
        if ln.startswith("경고") or ln.startswith("오류"):
            print(f"  [{stem}] {ln}")
    return outfile.read_text(encoding="utf-8")


def run_gfm(md_text):
    # 원고가 `[메뉴 이름](단축키)` 꼴로 쓴 것은 링크가 아니니 평범한 글로 둔다
    md_text = re.sub(r"\[([^\]\n]+)\]\((?!https?://|#|\.{0,2}/|mailto:)([^)\n]*)\)", r"\1 (\2)", md_text)
    r = subprocess.run(["pandoc", "-f", "gfm", "-t", "html", "--wrap=none"],
                       input=md_text, capture_output=True, text=True)
    if r.returncode != 0:
        sys.exit("pandoc 실패:\n" + r.stderr)
    return r.stdout


TAG = re.compile(r"<[^>]+>")
HEAD = re.compile(r"<h([1-6])([^>]*?)>(.*?)</h\1>", re.S)


def text_of(h):
    return re.sub(r"\s+", " ", html.unescape(TAG.sub("", h))).strip()


def postprocess(body, spec):
    body = re.sub(r"<header class=\"title-block\">.*?</header>", "", body, flags=re.S)
    # 위치 표시 span 제거 (보이지 않는 빈 span)
    heads = []

    def add_anchor(m):
        lvl, attrs, inner = int(m.group(1)), m.group(2), m.group(3)
        idm = re.search(r'id="([^"]+)"', attrs)
        if not idm:
            return m.group(0)
        hid = idm.group(1)
        heads.append((lvl, hid, text_of(inner)))
        return f'<h{lvl}{attrs}>{inner}<a class="anchor" href="#{hid}" aria-label="링크">#</a></h{lvl}>'

    body = HEAD.sub(add_anchor, body)
    # 표를 가로로 넘칠 때 스크롤되도록 감싼다
    body = re.sub(r"(<table\b.*?</table>)", r'<div class="tablewrap">\1</div>', body, flags=re.S)
    return body, heads


def build_toc(heads):
    if not heads:
        return ""
    levels = sorted({h[0] for h in heads})
    top = levels[0]
    if top == 1 and len(heads) > 1 and sum(1 for h in heads if h[0] == 1) == 1:
        # 장이 아니라 문서 제목 하나뿐인 경우
        top = levels[1] if len(levels) > 1 else top
    items = []
    cur = None
    for lvl, hid, title in heads:
        if lvl < top:
            continue
        if lvl == top:
            cur = {"id": hid, "title": title, "kids": []}
            items.append(cur)
        elif lvl == top + 1 and cur is not None:
            cur["kids"].append((hid, title))
    out = ['<ul class="toc-list">']
    for it in items:
        t = html.escape(it["title"])
        if it["kids"]:
            out.append(f'<li><details><summary><a href="#{it["id"]}">{t}</a></summary><ul>')
            for kid, kt in it["kids"]:
                out.append(f'<li><a href="#{kid}">{html.escape(kt)}</a></li>')
            out.append("</ul></details></li>")
        else:
            out.append(f'<li><a href="#{it["id"]}">{t}</a></li>')
    out.append("</ul>")
    return "\n".join(out)


def search_sections(body, spec, heads):
    """검색 색인: 헤딩(h1~h3) 단위로 본문을 자른다."""
    marks = [(m.start(), int(m.group(1)), re.search(r'id="([^"]+)"', m.group(2)), m.group(3))
             for m in HEAD.finditer(body)]
    secs = []
    for k, (pos, lvl, idm, inner) in enumerate(marks):
        if lvl > 3 or not idm:
            continue
        end = len(body)
        for pos2, lvl2, _i, _t in marks[k + 1:]:
            if lvl2 <= 3:
                end = pos2
                break
        chunk = body[pos:end]
        txt = text_of(re.sub(r'<a class="anchor".*?</a>', "", chunk))
        title = text_of(re.sub(r'<a class="anchor".*?</a>', "", inner))
        secs.append({"d": spec["slug"], "i": idm.group(1), "t": title,
                     "x": txt[len(title):].strip()[:6000]})
    return secs


# ───────────────────────── 쪽 틀 ─────────────────────────

def page(spec, body, toc, math, prev_next):
    head_title = html.escape(spec["title"])
    mj = ('<script>window.MathJax={tex:{inlineMath:[["\\\\(","\\\\)"]],displayMath:[["\\\\[","\\\\]"]]}};</script>\n'
          '<script async src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-chtml.js"></script>\n') if math else ""
    return f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{head_title} — ndhmdSuite</title>
<meta name="description" content="{html.escape(spec['sub'])}">
<link rel="icon" href="data:,">
<link rel="stylesheet" href="docs.css">
{mj}</head>
<body>
<header class="top">
  <div class="wrap">
    <a class="brand" href="../index.html">ndhmd<span>Suite</span></a>
    <nav>
      <a href="index.html">문서</a>
      <a href="../index.html#download">다운로드</a>
    </nav>
    <div class="search">
      <input id="q" type="search" placeholder="문서 검색…" autocomplete="off" aria-label="문서 검색">
      <div id="results" class="results" hidden></div>
    </div>
  </div>
</header>
<div class="layout">
  <aside class="side" id="side">
    <button class="side-toggle" id="sideToggle" type="button">목차</button>
    <nav class="toc" aria-label="목차">
{toc}
    </nav>
  </aside>
  <main class="doc">
    <div class="doc-head">
      <h1 class="doc-title">{head_title}</h1>
      <p class="doc-sub">{html.escape(spec['sub'])}</p>
    </div>
{body}
{prev_next}
  </main>
</div>
<script src="docs.js"></script>
</body>
</html>
"""


def index_page(built):
    cards = []
    for gid, gtitle, items in CARDS:
        cs = []
        for slug, title, desc in items:
            cs.append(f'<a class="dcard" href="{slug}.html"><b>{html.escape(title)}</b>'
                      f'<span>{html.escape(desc)}</span></a>')
        cards.append(f'<h2>{html.escape(gtitle)}</h2>\n<div class="dgrid">\n' + "\n".join(cs) + "\n</div>")
    spec = dict(title="문서", sub="ndhmdSuite 사용 안내")
    body = (
        '<p class="doc-lead">ndhmdSuite의 사용 안내입니다. 처음이라면 빠른 시작을 먼저 보고, '
        '나머지는 사전처럼 찾아서 쓰세요. 위쪽 검색창은 아래 모든 문서를 한 번에 찾아 줍니다.</p>\n'
        + "\n".join(cards)
        + '\n<p class="doc-note">PDF판: '
        '<a href="https://github.com/xltxlvr/ndhmd4tex/blob/main/guide/ndhmd4tex_dialect_guide.pdf">방언 사양서</a> '
        '(GitHub)</p>')
    return page(spec, body, "", False, "").replace('<aside class="side" id="side">', '<aside class="side empty" id="side">')


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--n2h", help="ndhmd2html(.py) 경로")
    ap.add_argument("--only", help="이 slug 하나만 다시 만든다")
    a = ap.parse_args()
    cmd = n2h_cmd(a.n2h)
    OUT.mkdir(exist_ok=True)

    index = []
    built_specs = [s for s in DOCS if not a.only or s["slug"] == a.only]
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        if (SRC / "img").is_dir():           # 그림은 변환할 때도, 결과 폴더에도 둔다
            shutil.copytree(SRC / "img", tmp / "img")
            shutil.copytree(SRC / "img", OUT / "img", dirs_exist_ok=True)
        for spec in built_specs:
            print(f"* {spec['src']}")
            md = (SRC / spec["src"]).read_text(encoding="utf-8")
            if spec["kind"] == "ndhmd":
                md = uncomment_missing_figure(md, SRC)
                if spec["number"]:
                    md = unnumber_appendices(md)
                if spec.get("tblr"):
                    md, n = convert_tblr(md)
                    print(f"  tblr 표 {n}개를 파이프 표로 바꿨다")
                body = run_ndhmd(cmd, md, spec, tmp)
            else:
                body = run_gfm(md)
            body, heads = postprocess(body, spec)
            toc = build_toc(heads)
            math = 'class="math' in body
            idx = built_specs.index(spec)
            # 이전/다음 쪽은 같은 group 안에서만
            same = [s for s in DOCS if s["group"] == spec["group"]]
            pn = []
            k = same.index(spec)
            if k > 0:
                pn.append(f'<a href="{same[k-1]["slug"]}.html">← {html.escape(same[k-1]["title"])}</a>')
            if k + 1 < len(same):
                pn.append(f'<a class="next" href="{same[k+1]["slug"]}.html">{html.escape(same[k+1]["title"])} →</a>')
            pager = '<nav class="pager">' + "".join(pn) + "</nav>" if pn else ""
            (OUT / f"{spec['slug']}.html").write_text(page(spec, body, toc, math, pager), encoding="utf-8")
            index.extend(search_sections(body, spec, heads))
            print(f"  → docs/{spec['slug']}.html ({len(heads)}개 헤딩)")

    if warnings:
        print("\n주의:", *sorted(set(warnings)), sep="\n  ")

    if not a.only:
        (OUT / "index.html").write_text(index_page(None), encoding="utf-8")
        (OUT / "search-index.json").write_text(json.dumps(index, ensure_ascii=False, separators=(",", ":")),
                                               encoding="utf-8")
        print(f"* docs/index.html, docs/search-index.json ({len(index)}개 절)")


if __name__ == "__main__":
    main()
