import json
import os
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
import sys
import time
from datetime import datetime, timedelta
import google.generativeai as genai

# APIキー設定
API_KEY = os.environ.get("GEMINI_API_KEY")
genai.configure(api_key=API_KEY)

output_file = 'quiz_data.json'
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
            if count >= 20: break
            title = item.find('title').text
            news_text += f"・{title}\n"
            count += 1
        return news_text
    except Exception as e:
        print(f"⚠️ ニュース取得エラー: {e}")
        return ""

print(f"🚀 【{target_category}】のクイズ更新を開始")

# 1. ニュース取得
news_text = fetch_news_text(target_category)
if not news_text:
    news_text = "（最新のトレンドに基づき、一般的な知識でクイズを作成してください）"

# 2. プロンプト作成
prompt = f"""
以下の最新ニュースを参考に、{yesterday_str}時点の「{target_category}」に関する4択クイズを作成してください。
難易度はレベル1から10まで各10問ずつ、合計100問作成してください。

【参考ニュース】
{news_text}

【ルール】
- 各レベル(1-10)につき10問、計100問を必ず作成すること。
- 出力はJSON配列形式のみ。

JSON形式：
[
  {{ "category": "{target_category}", "difficulty": 1, "question": "問", "choices": ["A","B","C","D"], "answer": "A", "explanation": "説" }},
  ...
]
"""

# 3. Geminiで生成
try:
    # モデル名を最新の 'gemini-2.0-flash' に変更！
    model = genai.GenerativeModel('gemini-2.0-flash')
    response = model.generate_content(
        prompt,
        generation_config=genai.types.GenerationConfig(
            temperature=0.7,
            response_mime_type="application/json"
        )
    )
    new_quizzes = json.loads(response.text)
    print(f"✅ Geminiによる100問生成に成功したぜ！")
except Exception as e:
    print(f"❌ 生成エラー: {e}")
    # 失敗したときのために、もう一度古い名前でも試す保険（フォールバック）
    try:
        print("💡 旧モデル名でリトライします...")
        model = genai.GenerativeModel('gemini-1.5-flash-latest')
        response = model.generate_content(prompt, generation_config=genai.types.GenerationConfig(temperature=0.7, response_mime_type="application/json"))
        new_quizzes = json.loads(response.text)
        print(f"✅ リトライで成功したぜ！")
    except Exception as e2:
        print(f"❌ 最終エラー: {e2}")
        sys.exit(1)

# 4. 既存データの読み込みと差し替え
if os.path.exists(output_file):
    try:
        with open(output_file, "r", encoding="utf-8") as f:
            full_data = json.load(f)
    except Exception:
        full_data = []
else:
    full_data = []

filtered_data = [q for q in full_data if q.get('category') != target_category]
updated_data = filtered_data + new_quizzes
updated_data.sort(key=lambda x: (x.get('category', ''), x.get('difficulty', 1)))

# 5. 保存
with open(output_file, "w", encoding="utf-8") as f:
    json.dump(updated_data, f, ensure_ascii=False, indent=2)

print(f"✨ 【{target_category}】の最新クイズを上書き保存完了！")
