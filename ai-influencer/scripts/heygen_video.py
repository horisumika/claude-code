#!/usr/bin/env python3
"""基準画像を HeyGen の Photo Avatar（talking photo）にして、台本をしゃべる縦動画を作る。

教材の「画像→動画」工程を、8GB の Mac でも回るよう HeyGen に置き換えたもの。
口の動きと声が合うので、教材の「ナレーションを後から重ねる」方式より自然になる。

手順（教材 第6章と同じ check → plan → submit → wait → collect）:
  export HEYGEN_API_KEY=...
  python3 scripts/heygen_video.py voices                       # 日本語の声の一覧
  python3 scripts/heygen_video.py plan  --job-dir output/hg-01 \
      --image assets/reference_face.png --script products/today.txt --voice-id <ID>
  python3 scripts/heygen_video.py submit --job-dir output/hg-01 --allow-submit   # ここで課金
  python3 scripts/heygen_video.py wait   --job-dir output/hg-01
  python3 scripts/heygen_video.py collect --job-dir output/hg-01 --target output/hg-01/heygen.mp4

submit は job-dir に video_id が記録済みなら再送しない（二重課金防止）。
API の仕様は https://docs.heygen.com/ で最新を確認すること。
"""
import argparse
import json
import mimetypes
import os
import sys
import time
import urllib.request
from pathlib import Path

API = "https://api.heygen.com"
UPLOAD = "https://upload.heygen.com"


def key() -> str:
    k = os.environ.get("HEYGEN_API_KEY")
    if not k:
        sys.exit("HEYGEN_API_KEY が未設定です。")
    return k


def call(method: str, url: str, body=None, raw: bytes = None, ctype: str = "application/json") -> dict:
    data = raw if raw is not None else (json.dumps(body).encode() if body is not None else None)
    req = urllib.request.Request(url, data=data, method=method,
                                 headers={"X-Api-Key": key(), "Content-Type": ctype, "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=120) as r:
        resp = json.load(r)
    if resp.get("error"):
        raise RuntimeError(json.dumps(resp["error"], ensure_ascii=False))
    return resp


def load_job(job_dir: Path) -> dict:
    f = job_dir / "job.json"
    if not f.exists():
        sys.exit(f"{f} がありません。先に plan を実行してください。")
    return json.loads(f.read_text())


def save_job(job_dir: Path, job: dict) -> None:
    (job_dir / "job.json").write_text(json.dumps(job, ensure_ascii=False, indent=2))


def build_payload(talking_photo_id: str, text: str, voice_id: str, width: int, height: int) -> dict:
    return {
        "video_inputs": [{
            "character": {"type": "talking_photo", "talking_photo_id": talking_photo_id},
            "voice": {"type": "text", "input_text": text, "voice_id": voice_id},
        }],
        "dimension": {"width": width, "height": height},
    }


def cmd_voices(_):
    resp = call("GET", f"{API}/v2/voices")
    for v in resp.get("data", {}).get("voices", []):
        if "japan" in (v.get("language") or "").lower():
            print(v.get("voice_id"), v.get("name"), v.get("gender"), sep="\t")


def cmd_plan(a):
    job_dir = Path(a.job_dir)
    if (job_dir / "job.json").exists():
        sys.exit(f"{job_dir} は使用済みです。未使用の job-dir を指定してください。")
    text = Path(a.script).read_text().strip()
    if len(text) > 1500:
        sys.exit("台本が長すぎます（ショート向けに短くしてください）。")
    job_dir.mkdir(parents=True)
    job = {"image": str(Path(a.image).resolve()), "script": text, "voice_id": a.voice_id,
           "width": a.width, "height": a.height}
    save_job(job_dir, job)
    print(json.dumps(job, ensure_ascii=False, indent=2))
    print("内容を確認してから submit --allow-submit を実行してください（課金が発生します）。")


def cmd_submit(a):
    job_dir = Path(a.job_dir)
    job = load_job(job_dir)
    if job.get("video_id"):
        print(f"送信済みです（video_id={job['video_id']}）。wait で状態を確認してください。")
        return
    if not a.allow_submit:
        sys.exit("--allow-submit が無いので送信しません。")
    if not job.get("talking_photo_id"):
        img = Path(job["image"])
        ctype = mimetypes.guess_type(img.name)[0] or "image/png"
        up = call("POST", f"{UPLOAD}/v1/talking_photo", raw=img.read_bytes(), ctype=ctype)
        job["talking_photo_id"] = up["data"]["talking_photo_id"]
        save_job(job_dir, job)
    payload = build_payload(job["talking_photo_id"], job["script"], job["voice_id"], job["width"], job["height"])
    resp = call("POST", f"{API}/v2/video/generate", body=payload)
    job["video_id"] = resp["data"]["video_id"]
    save_job(job_dir, job)
    print(f"送信しました: video_id={job['video_id']}")


def status(video_id: str) -> dict:
    return call("GET", f"{API}/v1/video_status.get?video_id={video_id}")["data"]


def cmd_wait(a):
    job_dir = Path(a.job_dir)
    job = load_job(job_dir)
    if not job.get("video_id"):
        sys.exit("まだ submit されていません。")
    deadline = time.time() + a.max_wait
    while True:
        st = status(job["video_id"])
        print(st.get("status"))
        if st.get("status") == "completed":
            job["video_url"] = st.get("video_url")
            save_job(job_dir, job)
            return
        if st.get("status") == "failed":
            sys.exit("生成に失敗しました: " + json.dumps(st.get("error"), ensure_ascii=False))
        if time.time() > deadline:
            sys.exit("待機上限に達しました。処理が止まったとは限らないので、同じ job-dir で wait を再実行してください。")
        time.sleep(a.interval)


def cmd_collect(a):
    job = load_job(Path(a.job_dir))
    url = job.get("video_url") or status(job["video_id"]).get("video_url")
    if not url:
        sys.exit("まだ完成していません。")
    target = Path(a.target)
    if target.exists():
        sys.exit(f"{target} は既にあります。別名を指定してください。")
    target.parent.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(url, timeout=300) as r:
        target.write_bytes(r.read())
    print(f"保存しました: {target}（全編を再生して顔・口・手を確認してください）")


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("voices").set_defaults(fn=cmd_voices)
    p = sub.add_parser("plan")
    p.add_argument("--job-dir", required=True)
    p.add_argument("--image", required=True)
    p.add_argument("--script", required=True, help="しゃべらせる台本のテキストファイル")
    p.add_argument("--voice-id", required=True)
    p.add_argument("--width", type=int, default=720)
    p.add_argument("--height", type=int, default=1280)
    p.set_defaults(fn=cmd_plan)
    s = sub.add_parser("submit")
    s.add_argument("--job-dir", required=True)
    s.add_argument("--allow-submit", action="store_true")
    s.set_defaults(fn=cmd_submit)
    w = sub.add_parser("wait")
    w.add_argument("--job-dir", required=True)
    w.add_argument("--interval", type=int, default=10)
    w.add_argument("--max-wait", type=int, default=1800)
    w.set_defaults(fn=cmd_wait)
    c = sub.add_parser("collect")
    c.add_argument("--job-dir", required=True)
    c.add_argument("--target", required=True)
    c.set_defaults(fn=cmd_collect)
    a = ap.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
