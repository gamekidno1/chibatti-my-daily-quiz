import json
import os
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
import sys
import time
from datetime import datetime, timedelta
import google.generativeai as genai

# --- 初期設定 ---
API_KEY = os.environ.get("GEMINI_API_KEY")
if not API_KEY:
    print("❌ エラー: GEMINI_API_KEY が設定されていません。")
    sys.exit(1)

genai.configure(api_key=API_KEY)

output_file = 'quiz_data.json'
target_category = sys.argv[1] if len(sys.argv) > 1 else "世界情勢"
yesterday_str = (datetime.now() - timedelta(days=1)).strftime("%Y年%m月%d日")

# --- 【最重要】利用可能なモデルを自動で見つける関数 ---
def find_best_model():
    print("🔍 利用可能なモデルを探索中...")
    try:
        available_models = []
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                available_models.append(m.name)
                print(f"  - 発見: {m.name}")
        
        if not available_models:
            print("❌ 利用可能なモデルが一つも見つかりませんでした。APIキーを確認してください。")
            sys.exit(1)

        # 1. 優先順位: 1.5-flash -> 2.0-flash -> その他の flash
        for name in available_models:
            if 'gemini-1.5-flash' in name: return name
        for name in available_models:
            if 'gemini-2.0-flash' in name: return name
        for name in available_models:
            if 'flash' in name: return name
            
        return available_models[0] # 何もなければ最初の一つを返す
    except Exception as e:
        print(f"❌ モデル一覧の取得に失敗しました: {e}")
        sys.exit(1)

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

# --- メイン処理 ---
best_model_name = find_best_model()
print(f"🚀 使用モデル確定: 【{best_model_name}】")
print(f"📦 【{target_category}】のクイズ更新を開始します...")

news_text = fetch_news_text(target_category)
if not news_text:
    news_text = "（最新のトレンドに基づき、一般的な知識でクイズを作成してください）"

prompt = f"""
以下の最新ニュースを参考に、{yesterday_str}時点の「{target_category}」に関する4択クイズを作成してください。
難易度はレベル1から10まで各10問ずつ、合計100問作成してください。

【参考ニュース】
{news_text}

【ルール】
- 各レベル(1-10)につき10問、計100問を必ず作成すること。
- 出力はJSON配列形式のみ。解説（explanation）に私信は含めないこと。

JSON形式：
[
  {{ "category": "{target_category}", "difficulty": 1, "question": "問題文", "choices": ["A","B","C","D"], "answer": "A", "explanation": "解説文" }},
  ...
]
"""

try:
    model = genai.GenerativeModel(best_model_name)
    response = model.generate_content(
        prompt,
        generation_config=genai.types.GenerationConfig(
            temperature=0.7,
            response_mime_type="application/json"
        )
    )
    new_quizzes = json.loads(response.text)
    print(f"✅ Geminiによる100問生成に成功！")
except Exception as e:
    print(f"❌ クイズ生成中にエラーが発生しました: {e}")
    sys.exit(1)

# データの保存処理
if os.path.exists(output_file):
    try:
        with open(output_file, "r", encoding="utf-8") as f:
            full_data = json.load(f)
    except:
        full_data = []
else:
    full_data = []

filtered_data = [q for q in full_data if q.get('category') != target_category]
updated_data = filtered_data + new_quizzes
updated_data.sort(key=lambda x: (x.get('category', ''), x.get('difficulty', 1)))

with open(output_file, "w", encoding="utf-8") as f:
    json.dump(updated_data, f, ensure_ascii=False, indent=2)

print(f"✨ 【{target_category}】の最新100問を quiz_data.json に保存しました。")
