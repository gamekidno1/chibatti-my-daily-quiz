import json
import os
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
import sys
import time
from datetime import datetime

from google import genai

# 基本設定
API_KEY = os.environ.get("GEMINI_API_KEY")
client = genai.Client(api_key=API_KEY)
MODEL_NAME = "gemini-2.5-flash"
output_file = 'quiz_data.json'
target_category = sys.argv[1] if len(sys.argv) > 1 else "世界情勢"
today_str = datetime.now().strftime("%Y年%m月%d日")

def fetch_news(category):
    query = urllib.parse.quote(f"{category} 最新 ニュース")
    url = f"https://news.google.com/rss/search?q={query}&hl=ja&gl=JP&ceid=JP:ja"
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=10) as res:
            root = ET.fromstring(res.read())
            items = [item.find('title').text for item in root.findall('.//item')[:15]]
            return "\n".join(items)
    except: return ""

print(f"🚀 【{target_category}】の最新100問を生成中 (Model: {MODEL_NAME})...")
news = fetch_news(target_category)

prompt = f"""
あなたは時事問題のプロです。提供された最新ニュースをもとに、{today_str}時点の「{target_category}」に関する4択クイズを100問作成してください。

【鉄則】
1. 一般常識や過去のニュース（2025年6月以前の出来事）での出題は禁止です。
2. 必ず【最新ニュース】セクションに記載されたニュースだけを元に出題してください。記載されていない話題は絶対に使わないでください。
3. 各問題の解説に「2026年3月のニュースによると」のように具体的な時期を必ず入れてください。
4. 出力は以下のJSON配列形式とキー構成を【完全に】守ること。これ以外のフォーマットはシステムエラーを引き起こすため絶対に避けてください。
5. 難易度(difficulty)は1から10まで、各レベル10問ずつ作成すること。
6. 出力は必ず配列 [...] から始めてください。オブジェクト {{...}} でラップしないでください。

【必須JSONフォーマット】
[
  {{
    "category": "{target_category}",
    "difficulty": 1,
    "question": "ニュースに基づいた問題文",
    "choices": ["選択肢A", "選択肢B", "選択肢C", "選択肢D"],
    "answer": "正解の選択肢",
    "explanation": "解説（必ずいつのニュースかを含めること）"
  }}
]

【最新ニュース】
{news if news else "2026年現在の最新トレンド"}
"""

try:
    # リトライ付き生成（最大3回、あらゆるエラーに対応）
    max_retries = 3
    new_quizzes = None
    for attempt in range(max_retries):
        try:
            response = client.models.generate_content(
                model=MODEL_NAME,
                contents=prompt,
                config={"response_mime_type": "application/json", "temperature": 0.7}
            )
            raw_text = response.text.strip()
            if raw_text.startswith("```"):
                raw_text = raw_text.split("\n", 1)[1].rsplit("```", 1)[0]
            new_quizzes = json.loads(raw_text)
            print(f"✅ {attempt+1}回目の生成でJSONパース成功！")
            break
        except json.JSONDecodeError as e:
            print(f"⚠️ {attempt+1}回目: JSONパースエラー ({e})。リトライします...")
            if attempt == max_retries - 1:
                raise ValueError(f"JSON生成に{max_retries}回失敗しました。")
            time.sleep(5)
        except Exception as e:
            print(f"⚠️ {attempt+1}回目: API呼び出しエラー ({e})。リトライします...")
            if attempt == max_retries - 1:
                raise ValueError(f"API呼び出しに{max_retries}回失敗しました: {e}")
            time.sleep(10)

    # 🛡️ 絶対防衛ライン（バリデーション） - 不良問題は除外して続行
    # オブジェクトでラップされてた場合、中の配列を取り出す
    if isinstance(new_quizzes, dict):
        for value in new_quizzes.values():
            if isinstance(value, list) and len(value) > 0:
                new_quizzes = value
                print(f"⚠️ オブジェクトでラップされていたため、中の配列を取り出しました。")
                break

    if not isinstance(new_quizzes, list) or len(new_quizzes) == 0:
        raise ValueError("生成されたデータが空、または配列形式ではありません。")

    required_keys = {"category", "difficulty", "question", "choices", "answer", "explanation"}
    valid_quizzes = []
    for i, q in enumerate(new_quizzes):
        if not required_keys.issubset(q.keys()):
            print(f"⚠️ {i+1}問目: 必須項目不足のためスキップ")
            continue
        if not isinstance(q["choices"], list) or len(q["choices"]) != 4:
            print(f"⚠️ {i+1}問目: 選択肢が4つではないためスキップ")
            continue
        if q.get("category") != target_category:
            print(f"⚠️ {i+1}問目: カテゴリ不一致のためスキップ")
            continue
        valid_quizzes.append(q)

    if len(valid_quizzes) < 50:
        raise ValueError(f"有効な問題が{len(valid_quizzes)}問しかありません（最低50問必要）。")

    new_quizzes = valid_quizzes
    print(f"🛡️ 検問クリア！有効な問題 {len(new_quizzes)}問 を確認しました。上書き処理に移行します。")

    # 既存データの読み込みとマージ
    full_data = []
    if os.path.exists(output_file):
        with open(output_file, "r", encoding="utf-8") as f:
            try: full_data = json.load(f)
            except: full_data = []

    filtered = [q for q in full_data if q.get('category') != target_category]
    updated = filtered + new_quizzes
    updated.sort(key=lambda x: (x.get('category', ''), x.get('difficulty', 1)))

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(updated, f, ensure_ascii=False, indent=2)

    print(f"✅ {target_category} の更新が完了し、本番環境に反映されました！")

except Exception as e:
    print(f"❌ エラー発生: {e}")
    print("⚠️ 安全装置が作動しました。不良品データのため、既存の quiz_data.json は保護されました。")
    sys.exit(1)
