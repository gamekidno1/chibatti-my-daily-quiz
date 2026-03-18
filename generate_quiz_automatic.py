import json
import os
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
import sys
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
            news_items = [item.find('title').text for item in root.findall('.//item')[:15]]
            return "\n".join(news_items)
    except Exception as e:
        print(f"ニュース取得エラー: {e}")
        return ""

print(f"🚀 【{target_category}】の最新クイズ100問を生成しています...")
news_text = fetch_news(target_category)

prompt = f"""
以下の最新ニュースを参考に、{yesterday_str}時点の「{target_category}」に関する4択クイズを作成してください。
難易度はレベル1から10まで各10問ずつ、合計100問作成してください。

【参考ニュース】
{news_text}

【ルール】
- 各レベル(1-10)につき10問、計100問を必ず作成すること。
- 出力はJSON配列形式のみ。解説（explanation）に私信は含めない。

JSON形式：
[
  {{ "category": "{target_category}", "difficulty": 1, "question": "問題文", "choices": ["A","B","C","D"], "answer": "A", "explanation": "解説" }},
  ...
]
"""

try:
    # 互換性と安定性が最も高いモデル指定
    model = genai.GenerativeModel('models/gemini-1.5-flash')
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

    # 指定ジャンルのみ入れ替え
    filtered_data = [q for q in full_data if q.get('category') != target_category]
    updated_data = filtered_data + new_quizzes
    updated_data.sort(key=lambda x: (x.get('category', ''), x.get('difficulty', 1)))

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(updated_data, f, ensure_ascii=False, indent=2)
    
    print(f"✅ {target_category} の更新が正常に完了しました。")

except Exception as e:
    print(f"❌ 生成または処理中にエラーが発生しました: {e}")
    sys.exit(1)
