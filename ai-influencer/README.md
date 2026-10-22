# AIインフルエンサー ショート動画キット（1,000円以下の日用雑貨・楽天アフィリエイト）

購入済み教材「AIインフルエンサーの教科書」の流れ（キャラ台帳 → 基準画像 → 動画 → 投稿下書き）を、
M2・8GB の Mac で回せるように **画像は Gemini、動画は HeyGen** に置き換えたものです。

| ファイル | 中身 |
|---|---|
| `character.md` | キャラ台帳（教材 第1章の形式） |
| `pipeline.md` | Claude Code へ渡す制作指示書（教材 第6章の形式） |
| `products/today.md` | 今日の1本の台本・投稿文・表示設定 |
| `scripts/make_reference_image.py` | 基準画像を Gemini で1枚生成 |
| `scripts/heygen_video.py` | 基準画像を HeyGen でしゃべらせる |

## Mac での使い方

```bash
cp -R ai-influencer ~/ai-influencer && cd ~/ai-influencer

# 1. 基準画像
export GEMINI_API_KEY=...
python3 scripts/make_reference_image.py --out assets/reference_face.png
#   → 目で確認して採用。character.md に版と日付を書く

# 2. しゃべる動画（HeyGen）
export HEYGEN_API_KEY=...
python3 scripts/heygen_video.py voices                     # 日本語の声を選ぶ
printf '%s\n' "1000円以下で買える、暮らしがちょっとラクになる雑貨を3つ比べてみました。" > products/today.txt
python3 scripts/heygen_video.py plan   --job-dir output/hg-01 --image assets/reference_face.png --script products/today.txt --voice-id <ID>
python3 scripts/heygen_video.py submit --job-dir output/hg-01 --allow-submit   # 課金はここだけ
python3 scripts/heygen_video.py wait   --job-dir output/hg-01
python3 scripts/heygen_video.py collect --job-dir output/hg-01 --target output/hg-01/heygen.mp4
```

その後の字幕・BGM・「AI生成」「PR」表示の重ね合わせは、手元の ffmpeg 仕上げスクリプトで行います。

## 公開前に必ず確認すること

- **AI表示**：YouTube「改変または合成されたコンテンツ」／TikTok「AI生成」ラベル
  （[YouTube ヘルプ](https://support.google.com/youtube/answer/14328491)、[TikTok ガイドライン](https://www.tiktok.com/community-guidelines/en/integrity-authenticity/)）
- **広告表示**（楽天リンクを付ける回）：動画とキャプションに「PR」、YouTube「有料プロモーション」、TikTok「コンテンツの開示」
  （[消費者庁 ステマ規制](https://www.caa.go.jp/policies/policy/representation/fair_labeling/stealth_marketing/)）
- 架空の使用経験（「使ってみた」）や効き目の断定を言わせない
- 価格は投稿日に楽天で確認し、「投稿時点の価格」と添える
- 画像生成サービス・HeyGen の**商用利用条件**を確認し、`character.md` に記録する
- 公開は人が全編を再生して確認してから手動で行う
