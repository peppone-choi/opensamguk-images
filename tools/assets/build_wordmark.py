#!/usr/bin/env python3
"""오픈삼국 워드마크 export 빌더 — 정본 assets/brand/logo-master.png(1927×720 RGBA)에서 두 앱 public 사본을 만든다.

정본은 2026-10-01 사용자 결정 D22 로 MIT 가 되어 오픈삼국 저장소 assets/brand 에서 이 저장소로 옮겨 왔다(sha256 그대로).
새로 그리지 않는다 — LANCZOS 로 줄여 담을 뿐이다.

산출(web/{game,gateway}/public/ 에 같은 파일):
    logo-wordmark.webp     840×314 WebP 손실 q88 — 로그인(420×157) · 가입(360×134) 표시의 2배
    logo-wordmark.png      840×314 256색 PNG — 위 WebP 의 대체본(<picture>)
    logo-wordmark-sm.png   172×64 256색 PNG — 셸 머리줄 Brand(86×32 · 64×24)의 2배. 이 크기는 PNG(6.5 KB)가 WebP(7.9 KB)보다 작다.

예전 앱 사본은 1200×448 · 714 KB PNG 하나를 머리줄 86×32 에도 그대로 써서 로그인 전송 바이트의 38%였다(K10 운영 측정).
어두운 바탕(#0c0f0e) 합성 PSNR: 840 WebP 35.4 dB · PNG 34.6 dB — 눈으로 구별되지 않는다.

    python3 tools/assets/build_wordmark.py           # 다시 굽는다
    python3 tools/assets/build_wordmark.py --check   # 디스크의 사본이 정본에서 나온 것인지 본다(CI)

--check 는 바이트가 아니라 푼 그림으로 본다(OS · 인코더 빌드마다 압축 바이트가 다를 수 있다).
PNG 는 다시 양자화한 그림과 RGBA PSNR 이 MIN_PNG_PSNR 이상이어야 한다(플랫폼별 미세 차이 허용, 알파 포함).
WebP 는 화면 바탕에 합성한 원본 축소와의 PSNR 이 MIN_PSNR 이상이어야 한다. 크기는 모두 같아야 한다.
바이트 상한(MAX_BYTES)도 본다 — 로고가 다시 무거워지면 빨개진다.
"""
from __future__ import annotations

import io
import math
import sys
from pathlib import Path

from PIL import Image, ImageChops, ImageStat

ROOT = Path(__file__).resolve().parents[2]
MASTER = ROOT / "assets" / "brand" / "logo-master.png"
APPS = ("game", "gateway")
BACKGROUND = (12, 15, 14, 255)  # 화면 바탕(다크 테마) — 알파 합성 비교용
WEBP_QUALITY = 88
MIN_PSNR = 34.0
MIN_PNG_PSNR = 50.0  # RGBA 채널 RMS 약 0.81 이하: 양자화의 미세 차이만 허용
MAX_BYTES = 100_000
# 이름 → (폭 px, 형식들). 높이는 정본 비율을 따른다.
WORDMARKS = {"logo-wordmark": (840, ("webp", "png")), "logo-wordmark-sm": (172, ("png",))}


def resized(master: Image.Image, width: int) -> Image.Image:
    return master.resize((width, round(width * master.height / master.width)), Image.LANCZOS)


def quantized(image: Image.Image) -> Image.Image:
    return image.quantize(colors=256, method=Image.Quantize.FASTOCTREE)


def encode(image: Image.Image, fmt: str) -> bytes:
    buf = io.BytesIO()
    if fmt == "webp":
        image.save(buf, format="WEBP", quality=WEBP_QUALITY, method=6)
    else:
        quantized(image).save(buf, format="PNG", optimize=True)
    return buf.getvalue()


def on_background(image: Image.Image) -> Image.Image:
    rgba = image.convert("RGBA")
    base = Image.new("RGBA", rgba.size, BACKGROUND)
    return Image.alpha_composite(base, rgba).convert("RGB")


def psnr(a: Image.Image, b: Image.Image) -> float:
    stat = ImageStat.Stat(ImageChops.difference(a, b))
    mse = sum(x * x for x in stat.rms) / len(stat.rms)
    return 99.0 if mse == 0 else 10 * math.log10(255 * 255 / mse)


def outputs(master: Image.Image) -> list[tuple[Path, Image.Image, str]]:
    rows = []
    for name, (width, formats) in WORDMARKS.items():
        image = resized(master, width)
        for app in APPS:
            for fmt in formats:
                rows.append((ROOT / "web" / app / "public" / f"{name}.{fmt}", image, fmt))
    return rows


def main() -> int:
    if not MASTER.exists():
        raise SystemExit(f"정본이 없다: {MASTER}")
    master = Image.open(MASTER).convert("RGBA")
    rows = outputs(master)
    if "--check" in sys.argv[1:]:
        problems = []
        for path, image, fmt in rows:
            rel = path.relative_to(ROOT)
            if not path.exists():
                problems.append(f"{rel}: 없음")
                continue
            size = path.stat().st_size
            if size > MAX_BYTES:
                problems.append(f"{rel}: {size} B > {MAX_BYTES} B")
            shown = Image.open(path)
            if shown.size != image.size:
                problems.append(f"{rel}: 크기 {shown.size} ≠ {image.size}")
                continue
            if fmt == "png":
                score = psnr(quantized(image).convert("RGBA"), shown.convert("RGBA"))
                if score < MIN_PNG_PSNR:
                    problems.append(f"{rel}: RGBA PSNR {score:.1f} < {MIN_PNG_PSNR}")
            elif (score := psnr(on_background(image), on_background(shown))) < MIN_PSNR:
                problems.append(f"{rel}: PSNR {score:.1f} < {MIN_PSNR}")
        if problems:
            for line in problems:
                print(f"DRIFT: {line}", file=sys.stderr)
            return 1
        print(f"wordmark check OK: {len(rows)} files")
        return 0
    for path, image, fmt in rows:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(encode(image, fmt))
    print(f"wordmark rebuilt: {len(rows)} files")
    return 0


if __name__ == "__main__":
    sys.exit(main())
