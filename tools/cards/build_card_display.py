#!/usr/bin/env python3
"""계책 카드 그림 표시용 export — 채택본(exports/stratagem-cards/*.webp, 512×768)을 화면 표시 크기의 2배로 줄인다.

앱은 카드를 154×231 로 그린다(계책 덱 #1132). 512×768 을 그대로 보내면 장당 40–53 KB 를 쓰는데, 표시의 2배(308×462)면
장당 약 20 KB 로 줄고 어두운 바탕 없이 RGB 끼리 비교한 PSNR 이 37 dB 안팎이다. 새로 그리지 않는다 — 채택본을 LANCZOS 로 줄여
WebP(손실 q85)로 다시 담을 뿐이다.

    python3 tools/cards/build_card_display.py           # exports/stratagem-cards/display/<id>.webp 를 다시 쓴다
    python3 tools/cards/build_card_display.py --check   # 디스크의 display 가 채택본에서 나온 것인지 본다

--check 는 바이트가 아니라 푼 그림으로 본다(OS · 인코더 빌드마다 WebP 바이트가 다를 수 있다).
채택본과 display 의 이름 집합이 같고, 크기가 308×462 이며, 채택본을 다시 줄인 것과의 PSNR 이 MIN_PSNR 이상이어야 한다.
"""
from __future__ import annotations

import io
import math
import sys
from pathlib import Path

from PIL import Image, ImageChops, ImageStat

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "exports" / "stratagem-cards"
DISPLAY = SOURCE / "display"
SIZE = (308, 462)  # 앱 표시 154×231 의 2배
QUALITY = 85
MIN_PSNR = 34.0


def reference(path: Path) -> Image.Image:
    return Image.open(path).convert("RGB").resize(SIZE, Image.LANCZOS)


def encode(image: Image.Image) -> bytes:
    buf = io.BytesIO()
    image.save(buf, format="WEBP", quality=QUALITY, method=6)
    return buf.getvalue()


def psnr(a: Image.Image, b: Image.Image) -> float:
    stat = ImageStat.Stat(ImageChops.difference(a, b))
    mse = sum(x * x for x in stat.rms) / 3
    return 99.0 if mse == 0 else 10 * math.log10(255 * 255 / mse)


def sources() -> list[Path]:
    return sorted(SOURCE.glob("*.webp"))


def main() -> int:
    check = "--check" in sys.argv[1:]
    cards = sources()
    if not cards:
        raise SystemExit(f"채택본이 없다: {SOURCE}")
    if check:
        problems = []
        want = {p.name for p in cards}
        have = {p.name for p in DISPLAY.glob("*.webp")}
        problems += [f"display 없음: {n}" for n in sorted(want - have)]
        problems += [f"채택본 없는 display: {n}" for n in sorted(have - want)]
        for path in cards:
            out = DISPLAY / path.name
            if not out.exists():
                continue
            shown = Image.open(out).convert("RGB")
            if shown.size != SIZE:
                problems.append(f"{out.name}: 크기 {shown.size} ≠ {SIZE}")
                continue
            score = psnr(reference(path), shown)
            if score < MIN_PSNR:
                problems.append(f"{out.name}: PSNR {score:.1f} < {MIN_PSNR}")
        if problems:
            for line in problems:
                print(f"DRIFT: {line}", file=sys.stderr)
            return 1
        print(f"card display check OK: {len(cards)} cards at {SIZE[0]}×{SIZE[1]}")
        return 0
    DISPLAY.mkdir(exist_ok=True)
    for path in cards:
        (DISPLAY / path.name).write_bytes(encode(reference(path)))
    print(f"card display rebuilt: {len(cards)} cards → {DISPLAY.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
