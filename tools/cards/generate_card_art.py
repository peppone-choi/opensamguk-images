#!/usr/bin/env python3
"""계책 카드 그림 후보 생성기 — originals/stratagem-cards/design.json → 후보 PNG + 출처 원장.

OPENAI_API_KEY 를 환경변수로만 읽는다. 키 값은 출력·기록하지 않는다.
후보는 previews/stratagem-cards/candidates/<card>/ 에, 출처(모델·프롬프트·해시·날짜)는
originals/stratagem-cards/provenance.json 에 남긴다. 채택은 사람이 한다.

  python3 tools/cards/generate_card_art.py --cards maebok,ganpa --n 4 --quality low
  python3 tools/cards/generate_card_art.py --dry-run     # 프롬프트만 찍는다(호출 없음)
"""
from __future__ import annotations

import argparse
import base64
import datetime
import hashlib
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DESIGN = ROOT / "originals/stratagem-cards/design.json"
PROVENANCE = ROOT / "originals/stratagem-cards/provenance.json"
OUT = ROOT / "previews/stratagem-cards/candidates"
ENDPOINT = "https://api.openai.com/v1/images/generations"


def prompt_for(design: dict, card: dict, style: str) -> str:
    return f"{design['styles'][style]} {design.get('periodRules', '')} Scene: {card['scene']}"


def generate(key: str, model: str, prompt: str, size: str, quality: str, n: int) -> list[bytes]:
    body = json.dumps({"model": model, "prompt": prompt, "size": size, "quality": quality, "n": n}).encode()
    req = urllib.request.Request(ENDPOINT, data=body, headers={
        "Authorization": f"Bearer {key}", "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=600) as res:
            payload = json.load(res)
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", "replace")[:600]
        raise SystemExit(f"OpenAI API {e.code}: {detail}")
    return [base64.b64decode(row["b64_json"]) for row in payload["data"]]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cards", default="", help="쉼표로 나눈 card id (기본: 전부)")
    ap.add_argument("--n", type=int, default=4)
    ap.add_argument("--quality", default="low", choices=["low", "medium", "high"])
    ap.add_argument("--style", default=None, help="design.json styles 의 키 (기본: defaultStyle)")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args(argv)
    design = json.loads(DESIGN.read_text(encoding="utf-8"))
    style = args.style or design["defaultStyle"]
    if style not in design["styles"]:
        raise SystemExit(f"design.json 에 없는 style: {style}")
    wanted = {c for c in args.cards.split(",") if c}
    unknown = wanted - {c["id"] for c in design["cards"]}
    if unknown:
        raise SystemExit(f"design.json 에 없는 카드: {sorted(unknown)}")
    cards = [c for c in design["cards"] if not wanted or c["id"] in wanted]
    if args.dry_run:
        for c in cards:
            print(f"[{c['id']}] {prompt_for(design, c, style)}\n")
        return 0
    key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not key:
        raise SystemExit("OPENAI_API_KEY 가 비어 있다 — 메타레포 .env 를 export 한 뒤 다시 돌려라")
    ledger = json.loads(PROVENANCE.read_text(encoding="utf-8")) if PROVENANCE.exists() else {
        "schemaVersion": 1, "note": "AI 생성 후보의 출처. 채택 여부는 adopted 로 사람이 적는다.", "runs": []}
    for c in cards:
        prompt = prompt_for(design, c, style)
        images = generate(key, design["model"], prompt, design["size"], args.quality, args.n)
        stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        folder = OUT / c["id"]
        folder.mkdir(parents=True, exist_ok=True)
        files = []
        for i, raw in enumerate(images, start=1):
            path = folder / f"{c['id']}-{stamp}-{style}-{args.quality}-{i}.png"
            path.write_bytes(raw)
            files.append({"path": str(path.relative_to(ROOT)), "sha256": hashlib.sha256(raw).hexdigest()})
        ledger["runs"].append({"card": c["id"], "generatedAt": stamp, "provider": "OpenAI Images API",
                               "model": design["model"], "style": style, "size": design["size"], "quality": args.quality,
                               "prompt": prompt, "files": files, "adopted": None})
        PROVENANCE.write_text(json.dumps(ledger, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        print(f"{c['id']}: {len(files)} candidates", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
