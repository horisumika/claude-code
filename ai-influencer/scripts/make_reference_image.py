#!/usr/bin/env python3
"""基準画像（キャラの顔）を Gemini の画像生成で1枚作る。

使い方:
  export GEMINI_API_KEY=...
  python3 scripts/make_reference_image.py --out assets/reference_face.png
  python3 scripts/make_reference_image.py --out assets/reference_face_v2.png --seed-note v2

--dry-run を付けると、送信内容を表示するだけで API は呼ばない。
既存ファイルは上書きしない（教材 第1章：旧版を残す）。
標準ライブラリだけで動く。
"""
import argparse
import base64
import json
import os
import sys
import urllib.request
from pathlib import Path

MODEL = os.environ.get("GEMINI_IMAGE_MODEL", "gemini-2.5-flash-image")
ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"

# character.md の「顔と髪」「服装と背景」と合わせる。変えたら台帳も更新する。
DEFAULT_PROMPT = (
    "Photorealistic vertical 9:16 portrait of one fictional adult Japanese woman, 28 years old. "
    "Soft oval face, gentle slightly downturned eyes, natural light makeup, "
    "shoulder-length glossy dark brown hair. Wearing a plain white cotton shirt, fully clothed. "
    "Standing in a bright, tidy Japanese apartment kitchen in daylight, simple everyday goods on the counter. "
    "Waist-up, looking at the camera with a calm kind smile, hands resting out of frame. "
    "Natural skin texture, 50mm lens, shallow depth of field. "
    "Original person, not resembling any real person or celebrity. No text, no logo, no watermark."
)


def build_request(prompt: str) -> dict:
    return {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "responseModalities": ["IMAGE"],
            "imageConfig": {"aspectRatio": "9:16"},
        },
    }


def extract_image(resp: dict) -> bytes:
    for cand in resp.get("candidates", []):
        for part in cand.get("content", {}).get("parts", []):
            data = part.get("inlineData") or part.get("inline_data")
            if data and data.get("data"):
                return base64.b64decode(data["data"])
    raise RuntimeError("画像が返ってきませんでした: " + json.dumps(resp, ensure_ascii=False)[:500])


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True, help="保存先 PNG（既存なら停止）")
    ap.add_argument("--prompt", default=DEFAULT_PROMPT)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    out = Path(args.out)
    if out.exists():
        print(f"既に {out} があります。旧版を残すため別名を指定してください。", file=sys.stderr)
        return 1

    body = build_request(args.prompt)
    if args.dry_run:
        print(json.dumps({"model": MODEL, "out": str(out), "request": body}, ensure_ascii=False, indent=2))
        return 0

    key = os.environ.get("GEMINI_API_KEY")
    if not key:
        print("GEMINI_API_KEY が未設定です。", file=sys.stderr)
        return 1

    req = urllib.request.Request(
        ENDPOINT.format(model=MODEL),
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json", "x-goog-api-key": key},
    )
    with urllib.request.urlopen(req, timeout=180) as r:
        resp = json.load(r)

    png = extract_image(resp)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(png)
    # 生成条件を台帳へ写せるよう、隣に記録を残す
    out.with_suffix(".json").write_text(
        json.dumps({"model": MODEL, "prompt": args.prompt}, ensure_ascii=False, indent=2)
    )
    print(f"保存しました: {out}（顔・手・服・背景を目で確認してから採用してください）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
