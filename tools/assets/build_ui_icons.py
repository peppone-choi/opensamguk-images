#!/usr/bin/env python3
"""UI 아이콘 SVG 세트 빌더 (ADR-LITE-049 Phase 5 · I-1).

정본은 손으로 그린 `assets/ui-icons/source/<name>.svg`(20×20, stroke currentColor)다. 이 빌더는
결정적으로 (1) 개별 SVG 를 최소화해 `web/{game,gateway}/public/icons/<name>.svg` 로 export 하고
(2) 한 장의 sprite `web/{game,gateway}/public/icons/icons.svg`(`<symbol id="ico-<name>">`)를 만들고
(3) `assets/ui-icons/manifest.json`(이름·sha256·라벨)과 (4) 판별 시트 `assets/brand/ui-icons/preview.html`
(16/20/32px, 청동·이끼·적갈·정보 4색)을 쓴다. 외부 도구(svgo) 없이 표준 라이브러리만 쓴다.

    python3 tools/assets/build_ui_icons.py
    python3 tools/assets/build_ui_icons.py --check   # 손편집 드리프트 검사, 불일치면 비0 종료
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "assets" / "ui-icons" / "source"
MANIFEST = ROOT / "assets" / "ui-icons" / "manifest.json"
PREVIEW = ROOT / "assets" / "brand" / "ui-icons" / "preview.html"
EXPORT_DIRS = [ROOT / "web" / "game" / "public" / "icons", ROOT / "web" / "gateway" / "public" / "icons"]
VIEWBOX = "0 0 20 20"
PALETTE = {"bronze": "#d3b064", "moss": "#8fa77a", "rust": "#e08a7c", "info": "#7aa7c7"}
BG = "#0c0f0e"

_TITLE = re.compile(r"<title>(.*?)</title>", re.S)
_PATHS = re.compile(r"<path\b[^>]*?d=\"([^\"]+)\"[^>]*/>", re.S)
_VIEWBOX = re.compile(r"viewBox=\"([^\"]+)\"")


def load_sources() -> list[dict[str, str]]:
    icons = []
    for path in sorted(SOURCE.glob("*.svg")):
        text = path.read_text(encoding="utf-8")
        viewbox = _VIEWBOX.search(text)
        if not viewbox or viewbox.group(1) != VIEWBOX:
            raise SystemExit(f"{path.name}: viewBox 는 '{VIEWBOX}' 여야 한다")
        if "fill=\"#" in text or "stroke=\"#" in text:
            raise SystemExit(f"{path.name}: 색은 currentColor 만 — 고정 색 금지")
        title = _TITLE.search(text)
        paths = _PATHS.findall(text)
        if not paths:
            raise SystemExit(f"{path.name}: <path d> 가 없다")
        icons.append({
            "name": path.stem,
            "label": title.group(1).strip() if title else path.stem,
            "d": " ".join(re.sub(r"\s+", " ", d).strip() for d in paths),
        })
    if not icons:
        raise SystemExit("원본 SVG 가 없다")
    return icons


def minified_svg(icon: dict[str, str]) -> str:
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{VIEWBOX}" fill="none" stroke="currentColor" '
        f'stroke-width="1.5" stroke-linecap="square" stroke-linejoin="miter"><title>{icon["label"]}</title>'
        f'<path d="{icon["d"]}"/></svg>\n'
    )


def sprite_svg(icons: list[dict[str, str]]) -> str:
    # <use> 는 참조 원소의 스타일만 물려받고 sprite 루트 <svg> 의 속성은 못 본다.
    # 따라서 stroke/fill 은 반드시 <symbol> 자체에 둔다.
    symbols = "".join(
        f'<symbol id="ico-{i["name"]}" viewBox="{VIEWBOX}" fill="none" stroke="currentColor" stroke-width="1.5" '
        f'stroke-linecap="square" stroke-linejoin="miter"><title>{i["label"]}</title><path d="{i["d"]}"/></symbol>'
        for i in icons
    )
    return f'<svg xmlns="http://www.w3.org/2000/svg" style="display:none">{symbols}</svg>\n'


def manifest_json(icons: list[dict[str, str]]) -> str:
    rows = [
        {
            "name": i["name"],
            "label": i["label"],
            "sha256": hashlib.sha256(minified_svg(i).encode("utf-8")).hexdigest(),
        }
        for i in icons
    ]
    return json.dumps({"viewBox": VIEWBOX, "stroke": 1.5, "icons": rows}, ensure_ascii=False, indent=2) + "\n"


def preview_html(icons: list[dict[str, str]]) -> str:
    sizes = (16, 20, 32)
    cells = []
    for i in icons:
        row = []
        for tone, color in PALETTE.items():
            for size in sizes:
                row.append(
                    f'<svg width="{size}" height="{size}" style="color:{color}"><use href="#ico-{i["name"]}"/></svg>'
                )
        cells.append(
            f'<div class="cell"><div class="row">{"".join(row)}</div>'
            f'<div class="name">{i["name"]}<span>{i["label"]}</span></div></div>'
        )
    sprite = sprite_svg(icons).replace(' style="display:none"', ' style="position:absolute;width:0;height:0"')
    return (
        "<!doctype html><html><head><meta charset=\"utf-8\"><title>UI 아이콘 판별 시트</title>"
        f"<style>body{{margin:0;background:{BG};color:#ece6d8;font:12px/1.4 -apple-system,sans-serif;padding:16px}}"
        "h1{font-size:14px;margin:0 0 12px;color:#d3b064}.grid{display:grid;grid-template-columns:repeat(2,1fr);gap:8px 16px}"
        ".cell{border:1px solid #2c342f;padding:6px 8px;background:#1b201d}.row{display:flex;align-items:center;gap:8px}"
        ".name{margin-top:4px;color:#8a8477;font-family:ui-monospace,monospace;font-size:10px}.name span{margin-left:8px;color:#b9b2a3}"
        "</style></head><body>"
        f"<h1>UI 아이콘 판별 시트 — 16 / 20 / 32px × 청동·이끼·적갈·정보 ({len(icons)}종)</h1>{sprite}"
        f"<div class=\"grid\">{''.join(cells)}</div></body></html>\n"
    )


def outputs(icons: list[dict[str, str]]) -> dict[Path, str]:
    out: dict[Path, str] = {}
    for export_dir in EXPORT_DIRS:
        out[export_dir / "icons.svg"] = sprite_svg(icons)
        for icon in icons:
            out[export_dir / f"{icon['name']}.svg"] = minified_svg(icon)
    out[MANIFEST] = manifest_json(icons)
    out[PREVIEW] = preview_html(icons)
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="파일을 쓰지 않고 현재 산출물과 비교한다")
    args = parser.parse_args(argv)
    icons = load_sources()
    produced = outputs(icons)
    if args.check:
        drift = [str(p.relative_to(ROOT)) for p, text in produced.items() if not p.exists() or p.read_text(encoding="utf-8") != text]
        if drift:
            print("드리프트:\n  " + "\n  ".join(drift))
            return 1
        print(f"ok — {len(icons)} icons, {len(produced)} files")
        return 0
    for path, text in produced.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    print(f"wrote {len(produced)} files for {len(icons)} icons")
    return 0


if __name__ == "__main__":
    sys.exit(main())
