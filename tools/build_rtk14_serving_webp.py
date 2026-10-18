#!/usr/bin/env python3
"""RTK14 serving 초상의 작은 WebP 변형을 만든다(2026-10-18 D176).

목록 화면은 24×34 · 36×51 칸에 148×210 PNG(평균 62.7KB)를 받아 왔다. 같은 그림을
작은 WebP 로 더한다. 기존 png/jpg 경로와 URL 계약은 그대로 두고 옆에 더하기만 한다.

  serving/thumb/<id>.webp  48×68 — serving/portrait/<id>.png(148×210)를 LANCZOS 로 축소
  serving/icon/<id>.webp   96×96 — serving/icon/<id>.png 를 크기 그대로 WebP 로

해시 · 크기 기록은 portraits/rtk14/manifest/serving-webp.json 이다.

    python3 tools/build_rtk14_serving_webp.py          # 다시 만든다
    python3 tools/build_rtk14_serving_webp.py --check  # 드리프트 검사, 불일치면 비0 종료

--check 는 바이트 재인코딩 일치를 보지 않는다(libwebp 판이 다르면 바이트가 달라진다).
대신 ① id 집합 ② 크기 ③ 원본 PNG 해시(원본이 바뀌었는데 안 다시 만든 것) ④ WebP 해시
(손편집) ⑤ 원본 축소본 대비 PSNR 이 만들 때 잰 최저보다 1 dB 넘게 떨어지지 않는지 본다.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import math
import statistics
import sys
from pathlib import Path

from PIL import Image, ImageChops, features

ROOT = Path(__file__).resolve().parents[1]
SERVING = ROOT / "portraits" / "rtk14" / "serving"
MANIFEST = ROOT / "portraits" / "rtk14" / "manifest" / "serving-webp.json"

QUALITY = 80
METHOD = 4
# --check 의 PSNR 하한 = 만들 때 잰 변형별 최저(manifest variants.<name>.minPsnr) − 이 여유.
# 고정 임계값을 지어내지 않고 실측 기준선을 쓴다. 여유는 libwebp 판 차이로 흔들릴 몫이다.
PSNR_SLACK_DB = 1.0

VARIANTS = {
    "thumb": {"source": "portrait", "size": (48, 68)},
    "icon": {"source": "icon", "size": (96, 96)},
}


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _ids() -> list[str]:
    ids = sorted(p.stem for p in (SERVING / "portrait").glob("*.png"))
    icon_ids = sorted(p.stem for p in (SERVING / "icon").glob("*.png"))
    if not ids or ids != icon_ids:
        raise SystemExit("serving/portrait 와 serving/icon 의 id 집합이 다르다")
    return ids


def _reference(source: Image.Image, size: tuple[int, int]) -> Image.Image:
    rgb = source.convert("RGB")
    if rgb.size == size:
        return rgb
    return rgb.resize(size, Image.Resampling.LANCZOS)


def _encode(image: Image.Image) -> bytes:
    buf = io.BytesIO()
    image.save(buf, "WEBP", quality=QUALITY, method=METHOD)
    return buf.getvalue()


def _psnr(a: Image.Image, b: Image.Image) -> float:
    diff = ImageChops.difference(a.convert("RGB"), b.convert("RGB"))
    hist = diff.histogram()
    sq = sum(count * (i % 256) ** 2 for i, count in enumerate(hist))
    mse = sq / (a.width * a.height * 3)
    return math.inf if mse == 0 else 10 * math.log10(255**2 / mse)


def build() -> dict:
    files: dict[str, dict] = {}
    stats: dict[str, dict] = {}
    for name, spec in VARIANTS.items():
        out_dir = SERVING / name
        out_dir.mkdir(exist_ok=True)
        sizes, psnrs = [], []
        for officer_id in _ids():
            src_path = SERVING / spec["source"] / f"{officer_id}.png"
            src_bytes = src_path.read_bytes()
            with Image.open(io.BytesIO(src_bytes)) as source:
                ref = _reference(source, spec["size"])
            data = _encode(ref)
            (out_dir / f"{officer_id}.webp").write_bytes(data)
            with Image.open(io.BytesIO(data)) as decoded:
                psnrs.append(_psnr(decoded, ref))
            sizes.append(len(data))
            files[f"{name}/{officer_id}.webp"] = {
                "bytes": len(data),
                "sha256": _sha256(data),
                "sourceSha256": _sha256(src_bytes),
            }
        stats[name] = {
            "source": f"serving/{spec['source']}/<id>.png",
            "size": list(spec["size"]),
            "count": len(sizes),
            "totalBytes": sum(sizes),
            "meanBytes": round(statistics.mean(sizes), 1),
            "medianBytes": statistics.median(sizes),
            "maxBytes": max(sizes),
            "minPsnr": round(min(psnrs), 2),
        }
    manifest = {
        "schemaVersion": 1,
        "decision": "D176 (2026-10-18)",
        "generator": "tools/build_rtk14_serving_webp.py",
        "command": "python3 tools/build_rtk14_serving_webp.py",
        "encoder": {
            "format": "WEBP",
            "quality": QUALITY,
            "method": METHOD,
            "resample": "LANCZOS",
            "pillow": Image.__version__,
            "libwebp": features.version("webp"),
        },
        "variants": stats,
        "files": files,
    }
    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    return manifest


def check() -> list[str]:
    errors: list[str] = []
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    recorded = manifest["files"]
    ids = _ids()
    expected = {f"{name}/{i}.webp" for name in VARIANTS for i in ids}
    actual = {f"{name}/{p.name}" for name in VARIANTS for p in (SERVING / name).glob("*.webp")}
    for path in sorted(expected - actual):
        errors.append(f"MISSING {path}")
    for path in sorted(actual - expected):
        errors.append(f"EXTRA {path}")
    for path in sorted(expected - recorded.keys()):
        errors.append(f"UNRECORDED {path}")
    for name, spec in VARIANTS.items():
        floor = manifest["variants"][name]["minPsnr"] - PSNR_SLACK_DB
        for officer_id in ids:
            rel = f"{name}/{officer_id}.webp"
            out = SERVING / rel
            if rel not in recorded or not out.exists():
                continue
            data = out.read_bytes()
            src_bytes = (SERVING / spec["source"] / f"{officer_id}.png").read_bytes()
            if _sha256(data) != recorded[rel]["sha256"]:
                errors.append(f"HASH {rel}: manifest 와 다르다(손편집?)")
            if _sha256(src_bytes) != recorded[rel]["sourceSha256"]:
                errors.append(f"STALE {rel}: 원본 PNG 가 바뀌었다 — 다시 만들어라")
            with Image.open(io.BytesIO(data)) as decoded, Image.open(io.BytesIO(src_bytes)) as source:
                if decoded.format != "WEBP" or decoded.size != spec["size"]:
                    errors.append(f"SHAPE {rel}: {decoded.format} {decoded.size}")
                    continue
                psnr = _psnr(decoded, _reference(source, spec["size"]))
                if psnr < floor:
                    errors.append(f"PSNR {rel}: {psnr:.2f} < {floor:.2f}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--check", action="store_true", help="드리프트 검사만 한다")
    args = parser.parse_args()
    if args.check:
        errors = check()
        for line in errors[:50]:
            print(line, file=sys.stderr)
        if errors:
            print(f"serving webp check FAILED: {len(errors)} errors", file=sys.stderr)
            return 1
        print(f"serving webp check OK: {len(_ids())} ids × {len(VARIANTS)} variants")
        return 0
    manifest = build()
    for name, s in manifest["variants"].items():
        print(f"{name}: {s['count']} files, mean {s['meanBytes']} B, total {s['totalBytes']} B, min PSNR {s['minPsnr']} dB")
    return 0


if __name__ == "__main__":
    sys.exit(main())
