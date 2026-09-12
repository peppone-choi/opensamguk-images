#!/usr/bin/env python3
"""빈 상태 일러스트 빌더 (ADR-LITE-049 Phase 5 · I-2).

정본은 손으로 그린 `assets/ui-illustrations/source/<name>.svg`(96×96, 2색 고정)다. 결정적으로
(1) 개별 SVG 를 최소화해 `web/{game,gateway}/public/illustrations/<name>.svg` 로 export 하고
(2) `assets/ui-illustrations/manifest.json`(이름·제목·sha256), (3) 판별 시트
`assets/brand/ui-illustrations/preview.html` 을 쓴다. 표준 라이브러리만 쓴다.

    python3 tools/assets/build_ui_illustrations.py
    python3 tools/assets/build_ui_illustrations.py --check
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "assets" / "ui-illustrations" / "source"
MANIFEST = ROOT / "assets" / "ui-illustrations" / "manifest.json"
PREVIEW = ROOT / "assets" / "brand" / "ui-illustrations" / "preview.html"
EXPORT_DIRS = [ROOT / "web" / "game" / "public" / "illustrations", ROOT / "web" / "gateway" / "public" / "illustrations"]
VIEWBOX = "0 0 96 96"
ALLOWED_COLORS = {"#d3b064", "#697e58"}
BG = "#0c0f0e"

_TITLE = re.compile(r"<title>(.*?)</title>", re.S)
_VIEWBOX = re.compile(r"viewBox=\"([^\"]+)\"")
_COLOR = re.compile(r"#[0-9a-fA-F]{6}")


def load_sources() -> list[dict[str, str]]:
    items = []
    for path in sorted(SOURCE.glob("*.svg")):
        text = path.read_text(encoding="utf-8")
        vb = _VIEWBOX.search(text)
        if not vb or vb.group(1) != VIEWBOX:
            raise SystemExit(f"{path.name}: viewBox 는 '{VIEWBOX}' 여야 한다")
        colors = {c.lower() for c in _COLOR.findall(text)}
        if not colors <= ALLOWED_COLORS:
            raise SystemExit(f"{path.name}: 허용 색 밖 {sorted(colors - ALLOWED_COLORS)}")
        title = _TITLE.search(text)
        body = re.sub(r"<title>.*?</title>", "", text, flags=re.S)
        body = re.sub(r"<svg\b[^>]*>", "", body, count=1)
        body = body.replace("</svg>", "")
        body = re.sub(r"\s+", " ", body).strip()
        body = re.sub(r">\s+<", "><", body)
        items.append({"name": path.stem, "title": title.group(1).strip() if title else path.stem, "body": body})
    if not items:
        raise SystemExit("원본 SVG 가 없다")
    return items


def minified_svg(item: dict[str, str]) -> str:
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{VIEWBOX}" width="96" height="96" role="img">'
        f'<title>{item["title"]}</title>{item["body"]}</svg>\n'
    )


def manifest_json(items: list[dict[str, str]]) -> str:
    rows = [{"name": i["name"], "title": i["title"], "sha256": hashlib.sha256(minified_svg(i).encode("utf-8")).hexdigest()} for i in items]
    return json.dumps({"viewBox": VIEWBOX, "colors": sorted(ALLOWED_COLORS), "illustrations": rows}, ensure_ascii=False, indent=2) + "\n"


def preview_html(items: list[dict[str, str]]) -> str:
    cells = "".join(
        f'<div class="cell">{minified_svg(i).replace("width=\"96\" height=\"96\"", "width=\"96\" height=\"96\"")}'
        f'<div class="small">{minified_svg(i).replace("width=\"96\" height=\"96\"", "width=\"48\" height=\"48\"")}</div>'
        f'<div class="name">{i["name"]}<span>{i["title"]}</span></div></div>'
        for i in items
    )
    return (
        "<!doctype html><html><head><meta charset=\"utf-8\"><title>빈 상태 일러스트 판별 시트</title>"
        f"<style>body{{margin:0;background:{BG};color:#ece6d8;font:12px/1.4 -apple-system,sans-serif;padding:16px}}"
        "h1{font-size:14px;margin:0 0 12px;color:#d3b064}.grid{display:flex;gap:16px;flex-wrap:wrap}"
        ".cell{border:1px solid #2c342f;padding:12px;background:#1b201d;display:flex;flex-direction:column;align-items:center;gap:8px}"
        ".name{color:#8a8477;font-family:ui-monospace,monospace;font-size:10px}.name span{margin-left:8px;color:#b9b2a3}"
        f"</style></head><body><h1>빈 상태 일러스트 — 96 / 48px ({len(items)}종)</h1><div class=\"grid\">{cells}</div></body></html>\n"
    )


def outputs(items: list[dict[str, str]]) -> dict[Path, str]:
    out: dict[Path, str] = {}
    for d in EXPORT_DIRS:
        for i in items:
            out[d / f"{i['name']}.svg"] = minified_svg(i)
    out[MANIFEST] = manifest_json(items)
    out[PREVIEW] = preview_html(items)
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)
    items = load_sources()
    produced = outputs(items)
    if args.check:
        drift = [str(p.relative_to(ROOT)) for p, t in produced.items() if not p.exists() or p.read_text(encoding="utf-8") != t]
        if drift:
            print("드리프트:\n  " + "\n  ".join(drift))
            return 1
        print(f"ok — {len(items)} illustrations, {len(produced)} files")
        return 0
    for p, t in produced.items():
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(t, encoding="utf-8")
    print(f"wrote {len(produced)} files for {len(items)} illustrations")
    return 0


if __name__ == "__main__":
    sys.exit(main())
