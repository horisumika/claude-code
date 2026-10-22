#!/usr/bin/env python3
"""今日の商品を楽天市場APIで探し、送料込み1,000円以下の候補とアフィリエイトリンクを作る。

使い方:
  export RAKUTEN_APP_ID=...        # 楽天ウェブサービスのアプリID
  export RAKUTEN_AFFILIATE_ID=...  # 楽天アフィリエイトID
  python3 scripts/rakuten_links.py --out output/links-01.md

  キーワードを変える: --keyword "サンサンスポンジ" --keyword "キャベピィ" ...

検索条件: 価格 <= --max-price（既定1000円）、送料込みのみ、レビュー件数の多い順。
API の仕様は https://webservice.rakuten.co.jp/documentation/ichiba-item-search で最新を確認すること。
標準ライブラリだけで動く。
"""
import argparse
import json
import os
import sys
import time
import urllib.parse
import urllib.request
from datetime import date
from pathlib import Path

ENDPOINT = "https://app.rakuten.co.jp/services/api/IchibaItem/Search/20220601"
DEFAULT_KEYWORDS = ["サンサンスポンジ", "キャベピィMAX", "ニトリル手袋 100枚"]


def search(app_id: str, aff_id: str, keyword: str, max_price: int, hits: int) -> list:
    q = urllib.parse.urlencode({
        "applicationId": app_id,
        "affiliateId": aff_id,
        "keyword": keyword,
        "maxPrice": max_price,
        "postageFlag": 1,      # 送料込みのみ
        "availability": 1,     # 在庫あり
        "sort": "-reviewCount",
        "hits": hits,
        "format": "json",
        "formatVersion": 2,
    })
    with urllib.request.urlopen(f"{ENDPOINT}?{q}", timeout=30) as r:
        return json.load(r).get("Items", [])


def pick(items: list, max_price: int) -> list:
    # API の条件に加えて手元でも確かめる
    return [i for i in items if i.get("itemPrice", 10**9) <= max_price and i.get("postageFlag") == 0]


def to_markdown(results: dict, max_price: int) -> str:
    lines = [f"# 楽天リンク（{date.today()} 取得・送料込み{max_price}円以下）", "",
             "※価格は取得時点のもの。投稿前に商品ページで再確認する。", ""]
    for kw, items in results.items():
        lines.append(f"## {kw}")
        if not items:
            lines += ["条件に合う商品がありませんでした。別の商品に差し替えてください。", ""]
            continue
        for i in items:
            lines.append(f"- {i['itemName'][:60]}")
            lines.append(f"  - 価格: {i['itemPrice']}円（送料込み）／{i.get('shopName','')}")
            lines.append(f"  - レビュー: {i.get('reviewAverage')}（{i.get('reviewCount')}件）")
            lines.append(f"  - アフィリエイトリンク: {i.get('affiliateUrl') or '（取得できず）'}")
        lines.append("")
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--keyword", action="append")
    ap.add_argument("--max-price", type=int, default=1000)
    ap.add_argument("--top", type=int, default=3, help="キーワードごとに残す件数")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    app_id, aff_id = os.environ.get("RAKUTEN_APP_ID"), os.environ.get("RAKUTEN_AFFILIATE_ID")
    if not app_id or not aff_id:
        print("RAKUTEN_APP_ID と RAKUTEN_AFFILIATE_ID を設定してください。", file=sys.stderr)
        return 1
    out = Path(args.out)
    if out.exists():
        print(f"{out} は既にあります。別名を指定してください。", file=sys.stderr)
        return 1

    results = {}
    for kw in args.keyword or DEFAULT_KEYWORDS:
        results[kw] = pick(search(app_id, aff_id, kw, args.max_price, 30), args.max_price)[: args.top]
        time.sleep(1)  # API の呼び出し間隔を空ける

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(to_markdown(results, args.max_price))
    print(f"保存しました: {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
