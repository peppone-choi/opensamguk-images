#!/usr/bin/env python3
"""도시 상태 아이콘 원화 재생성 (OpenAI images/edits, 비결정적 · 수동 1회 실행).

이 스크립트는 ImageGen 호출 기록이다. 결정적 후처리는 `build_status_icons.py`가 맡고,
여기서 만든 PNG는 사람이 골라 `assets/status-icons/source/`에 정본으로 둔다.

    python3 tools/assets/gen_status_icons_imagegen.py states   # 4×4 기존 상태·수도 별 재작성
    python3 tools/assets/gen_status_icons_imagegen.py hwiha    # 2×2 휘하 신규 4종

출력: `assets/status-icons/source/raw/<sheet>-<n>.png` 와 같은 이름의 `.txt`(프롬프트).
순서: `states`(입력 = 이전 정본 시트) → 고른 결과를 `status-master-imagegen.png`로 승격 →
`hwiha`(입력 = 새 정본 시트, 팔레트·픽셀 밀도 참조) → 고른 결과를 `status-hwiha-imagegen.png`로.

Auth: 환경의 OPENAI_API_KEY. 절대 출력하지 않는다.
"""

from __future__ import annotations

import argparse
import base64
import io
import json
import os
import urllib.error
import urllib.request
import uuid
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "assets" / "status-icons" / "source"
RAW = SOURCE / "raw"
ENDPOINT = "https://api.openai.com/v1/images/edits"
MODEL = "gpt-image-2"
CANVAS = 1024

STYLE = (
    "Commercial-quality 16-bit isometric strategy-game pixel art icons, matching the attached "
    "reference sheet's art direction: light from the top-left, a dark brown-black 1-pixel "
    "outline around every shape, 3-step shading (highlight, base, shadow), a limited muted "
    "palette, chunky visible square pixels. Each icon must read as a STRONG SIMPLE SILHOUETTE "
    "that is still recognisable when shrunk to a 16x16 sprite: few large shapes, thick forms, "
    "no thin lines, no tiny details, no scenery, no ground shadow. Every icon centred in its "
    "own equal cell with generous empty margin; icons never touch or overlap each other. "
    "Pure flat white background everywhere, no checkerboard, no grid lines, no cell borders, "
    "no frames, no text, no numbers, no labels, no letters."
)

STATES = (
    "Redraw the attached reference as a NEW 4x4 sheet of 16 equal cells, read left-to-right, "
    "top-to-bottom. Cells 1-13 each hold exactly one icon; cells 14, 15 and 16 stay completely "
    "empty white. "
    "1: a tied sheaf of ripe golden grain (bumper harvest). "
    "2: three stacked round bronze Han coins with square holes (prosperity). "
    "3: a large pale ice-blue snowflake (severe cold). "
    "4: a bone-white skull wrapped in a purple cloud of miasma (plague). "
    "5: a broken earth slab split by a deep zigzag crack with two rocks jumping up (earthquake). "
    "6: a teal whirling typhoon spiral (typhoon). "
    "7: a small tiled-roof house half sunk in dark blue waves (flood). "
    "8: a cracked empty wooden bowl with a withered drooping grain stalk and one large green "
    "locust sitting on the rim (famine and locusts). "
    "9: a snapped wooden government signboard with a burning torch and a farmer's hoe crossed "
    "behind it (popular revolt; NO yellow turban, NO masked bandit). "
    "10: a city gate tower engulfed in orange flames (arson and agitation). "
    "11: a tied brown loot sack spilling bronze coins (plunder). "
    "12: a spear crossed with a red war banner and a bold red arrow pointing right (army "
    "marching to this city). "
    "13: a bold golden five-pointed star with no pedestal (capital). "
)

HWIHA = (
    "Using the attached sheet only as the style reference (same palette, outline, shading and "
    "pixel size), draw a NEW 2x2 sheet of 4 equal cells, read left-to-right, top-to-bottom, one "
    "icon per cell, each icon about half the cell wide, ONE compact solid group per icon with no "
    "scattered debris, crumbs or loose particles. "
    "1: a fat tied grain sack with a thick dark iron chain in front of it snapped in two, the "
    "two broken chain ends clearly apart (isolated: supply line cut). "
    "2: a small stone city gate completely encircled by a ring of sharpened wooden palisade "
    "stakes and spear points aimed inward (besieged). "
    "3: two crossed straight double-edged Han-dynasty jian swords with simple flat bronze "
    "guards and round pommels, and a small bright spark where the blades meet (battle). "
    "4: a builder's hammer crossed with a mason's trowel in front of a small square bamboo "
    "scaffold frame (construction works). "
)

SHEETS = {
    "states": (STATES, ("status-master-imagegen.png",)),
    "hwiha": (HWIHA, ("status-master-imagegen.png",)),
}


def _multipart(fields: dict[str, str], images: list[tuple[str, bytes]]) -> tuple[bytes, str]:
    boundary = "----status" + uuid.uuid4().hex
    out: list[bytes] = []
    for name, value in fields.items():
        out.append(
            f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"\r\n\r\n{value}\r\n'.encode()
        )
    for filename, data in images:
        out.append(
            f'--{boundary}\r\nContent-Disposition: form-data; name="image[]"; '
            f'filename="{filename}"\r\nContent-Type: image/png\r\n\r\n'.encode()
        )
        out.append(data)
        out.append(b"\r\n")
    out.append(f"--{boundary}--\r\n".encode())
    return b"".join(out), boundary


def _plate(path: Path) -> bytes:
    image = Image.open(path).convert("RGB").resize((CANVAS, CANVAS), Image.Resampling.NEAREST)
    buf = io.BytesIO()
    image.save(buf, "PNG")
    return buf.getvalue()


def generate(sheet: str) -> dict:
    task, refs = SHEETS[sheet]
    prompt = task + STYLE
    body, boundary = _multipart(
        {
            "model": MODEL,
            "prompt": prompt,
            "size": f"{CANVAS}x{CANVAS}",
            "quality": "high",
            "output_format": "png",
            "n": "1",
        },
        [(Path(ref).name, _plate(SOURCE / ref)) for ref in refs],
    )
    request = urllib.request.Request(
        ENDPOINT,
        data=body,
        headers={
            "Authorization": "Bearer " + os.environ["OPENAI_API_KEY"],
            "Content-Type": f"multipart/form-data; boundary={boundary}",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=900) as response:
            payload = json.load(response)
    except urllib.error.HTTPError as error:
        raise SystemExit(f"HTTP {error.code}: {error.read().decode(errors='replace')[:800]}")
    data = base64.b64decode(payload["data"][0]["b64_json"])
    RAW.mkdir(parents=True, exist_ok=True)
    index = 1
    while (RAW / f"{sheet}-{index}.png").exists():
        index += 1
    out = RAW / f"{sheet}-{index}.png"
    out.write_bytes(data)
    out.with_suffix(".txt").write_text(f"model={MODEL} refs={','.join(refs)}\n\n{prompt}\n")
    return {"sheet": sheet, "file": out.relative_to(ROOT).as_posix(), "usage": payload.get("usage")}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("sheet", choices=sorted(SHEETS))
    args = parser.parse_args()
    if not os.environ.get("OPENAI_API_KEY"):
        raise SystemExit("OPENAI_API_KEY is not set")
    print(json.dumps(generate(args.sheet), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
