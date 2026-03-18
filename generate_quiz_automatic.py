import json
import os
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
import sys
from datetime import datetime, timedelta
from google import genai
from google.genai import types

# APIキー設定
API_KEY = os.environ.get("GEMINI_API_KEY")
client = genai.Client(api_key=API_KEY)

output_file = 'quiz_data.json'
# 引数からジャンルを受け取る（デフォルトは世界情勢）
target_category = sys.argv[1] if len(sys.argv) > 1 else "世界情勢"
yesterday_str = (datetime.now() - timedelta(days=1)).strftime("%Y年%m月%d日")

# --- ニュース取得関数 ---
def fetch_news_text(category):
    query = urllib.parse.quote(f"{category} ニュース")
    url = f"https://news.google.com/rss/search?q={query}&hl=ja&gl=JP&ceid=JP:ja"
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req) as response:
            xml_data = response.read()
        root = ET.fromstring(xml_data)
        news_text = ""
        count = 0
        for item in root.findall('.//item'):
            if count >= 20: break # 少し多めに20件
            title = item.find('title').text
            news_text += f"・{title}\n"
            count += 1
        return news_text
    except Exception as e:
        print(f"⚠️ ニュース取得エラー: {e}")
        return ""

print(f"🚀 【{target_category}】のクイズ更新を開始（30分おき・部分上書きモード）")

# 1. ニュース取得
news_text = fetch_news_text(target_category)
if not news_text:
    news_text = "（ニュース取得失敗のため、最新のトレンドを推測して作成してください）"

# 2. プロンプト作成（各難易度10問、計100問！）
prompt = f"""
以下の最新ニュースを参考に、{yesterday_str}時点の「{target_category}」に関する4択クイズを作成してください。
難易度はレベル1から10まで各10問ずつ、合計100問作成してください。

【参考ニュース】
{news_text}

【ルール】
- 各レベル(1-10)につき、必ず10個のクイズ（計100個）を作成すること。
- Level 1は一般常識、Level 10は超マニアックな専門知識。
- 重複を避け、幅広いトピックを扱ってください。
- 出力はJSON配列形式のみ。解説（explanation）に私信は含めないこと。

JSON形式：
[
  {{ "category": "{target_category}", "difficulty": 1, "question": "問", "choices": ["A","B","C","D"], "answer": "A", "explanation": "説" }},
  ...
]
"""

# 3. Geminiで生成
try:
    response = client.models.generate_content(
        model='gemini-2.0-flash', # 高速なflashモデルが最適
        contents=prompt,
        config=types.GenerateContentConfig(
            temperature=0.7,
            response_mime_type="application/json"
        )
    )
    new_quizzes = json.loads(response.text)
    print(f"✅ Geminiによる100問生成に成功したぜ！")
except Exception as e:
    print(f"❌ 生成エラー: {e}")
    exit(1)

# 4. 既存データの読み込みと差し替え
if os.path.exists(output_file):
    with open(output_file, "r", encoding="utf-8") as f:
        full_data = json.load(f)
else:
    full_data = []

# 対象ジャンルの古いデータを削除
filtered_data = [q for q in full_data if q.get('category') != target_category]

# 新しいデータを追加
updated_data = filtered_data + new_quizzes

# 難易度でソート（アプリの表示順を整える）
updated_data.sort(key=lambda x: (x.get('category'), x.get('difficulty', 1)))

# 5. 保存
with open(output_file, "w", encoding="utf-8") as f:
    json.dump(updated_data, f, ensure_ascii=False, indent=2)

print(f"✨ 【{target_category}】の最新100問を quiz_data.json に上書き納品したぜ！")
