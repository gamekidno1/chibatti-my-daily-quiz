import json
import os
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
import sys
from datetime import datetime, timedelta
import google.generativeai as genai

# --- 1. 設定：1.5-flash に固定 ---
API_KEY = os.environ.get("GEMINI_API_KEY")
genai.configure(api_key=API_KEY)

# 429対策：2.0は制限0なので、確実に動く1.5を名指しで指定
MODEL_NAME = "gemini-1.5-flash"
output_file = 'quiz_data.json'
target_category = sys.argv[1] if len(sys.argv) > 1 else "世界情勢"
yesterday_str = (datetime.now() - timedelta(days=1)).strftime("%Y年%m月%d日")

# --- 2. ニュース取得 ---
def fetch_news(category):
    query = urllib.parse.quote(f"{category} ニュース")
    url = f"https://news.google.com/rss/search?q={query}&hl=ja&gl=JP&ceid=JP:ja"
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req) as res:
            root = ET.fromstring(res.read())
            return "\n".join([item.find('title').text for item in root.findall('.//item')[:15]])
    except: return "一般的なニュース知識で作成してください"

print(f"🚀 【{target_category}】を {MODEL_NAME} で100問生成中...")
news = fetch_news(target_category)

prompt = f"""
{yesterday_str}の「{target_category}」に関する4択クイズを100問作成。
【ニュース】
{news}
【出力】
JSON配列形式のみ。
[
  {{"category": "{target_category}", "difficulty": 1, "question": "問題", "choices": ["A","B","C","D"], "answer": "A", "explanation": "解説"}}
]
"""

# --- 3. 生成 ---
try:
    model = genai.GenerativeModel(MODEL_NAME)
    response = model.generate_content(
        prompt,
        generation_config={"response_mime_type": "application/json", "temperature": 0.7}
    )
    
    new_quizzes = json.loads(response.text)
    
    # マージ処理
    full_data = []
    if os.path.exists(output_file):
        with open(output_file, "r", encoding="utf-8") as f:
            try: full_data = json.load(f)
            except: full_data = []

    filtered = [q for q in full_data if q.get('category') != target_category]
    updated = filtered + new_quizzes
    
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(updated, f, ensure_ascii=False, indent=2)
    
    print(f"✨ 成功！100問保存したぜ。")

except Exception as e:
    print(f"🔥 エラー詳細: {e}")
    sys.exit(1)
