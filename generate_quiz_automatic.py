import json
import os
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
import sys
import time
from datetime import datetime, timedelta
import google.generativeai as genai

# API設定
API_KEY = os.environ.get("GEMINI_API_KEY")
genai.configure(api_key=API_KEY)

output_file = 'quiz_data.json'
target_category = sys.argv[1] if len(sys.argv) > 1 else "世界情勢"
yesterday_str = (datetime.now() - timedelta(days=1)).strftime("%Y年%m月%d日")

def fetch_news(category):
    query = urllib.parse.quote(f"{category} ニュース")
    url = f"https://news.google.com/rss/search?q={query}&hl=ja&gl=JP&ceid=JP:ja"
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req) as res:
            root = ET.fromstring(res.read())
            return "\n".join([item.find('title').text for item in root.findall('.//item')[:15]])
    except: return ""

print(f"🚀 【{target_category}】の最新クイズ100問を生成開始...")
news_text = fetch_news(target_category)

prompt = f"""
以下の最新ニュースを参考に、{yesterday_str}時点の「{target_category}」に関する4択クイズを作成してください。
難易度はレベル1から10まで各10問ずつ、合計100問作成してください。

【参考ニュース】
{news_text}

【出力形式】
JSON配列のみ。
[
  {{ "category": "{target_category}", "difficulty": 1, "question": "問題文", "choices": ["A","B","C","D"], "answer": "A", "explanation": "解説" }}
]
"""

# 試行するモデル名のリスト（これが404対策の決定打だぜ！）
model_names = ['gemini-2.0-flash', 'gemini-1.5-flash', 'gemini-1.5-flash-latest']
success = False

for model_name in model_names:
    if success: break
    print(f"🤖 モデル {model_name} で挑戦中...")
    
    try:
        # ここが修正ポイント！ 'models/' を付けずに直接指定
        model = genai.GenerativeModel(model_name)
        response = model.generate_content(
            prompt,
            generation_config={
                "response_mime_type": "application/json",
                "temperature": 0.7
            }
        )
        
        new_quizzes = json.loads(response.text)
        
        # 既存データの読み込みとマージ
        if os.path.exists(output_file):
            with open(output_file, "r", encoding="utf-8") as f:
                full_data = json.load(f)
        else:
            full_data = []

        filtered_data = [q for q in full_data if q.get('category') != target_category]
        updated_data = filtered_data + new_quizzes
        updated_data.sort(key=lambda x: (x.get('category', ''), x.get('difficulty', 1)))

        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(updated_data, f, ensure_ascii=False, indent=2)
        
        print(f"✅ {target_category} の100問生成に成功したぜ！")
        success = True

    except Exception as e:
        print(f"⚠️ {model_name} でエラー: {e}")
        # トラフィック過多（429）の場合は少し待つ
        if "429" in str(e) or "Resource" in str(e):
            print("💤 トラフィック制限中... 20秒待機して次を試すぜ。")
            time.sleep(20)
        continue

if not success:
    print("❌ 全てのモデルで生成に失敗しました。")
    sys.exit(1)
