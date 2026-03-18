import json
import os
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
import sys
from datetime import datetime, timedelta
import google.generativeai as genai

# --- 1. 設定 ---
API_KEY = os.environ.get("GEMINI_API_KEY")
genai.configure(api_key=API_KEY)

MODEL_NAME = "gemini-1.5-flash"
output_file = 'quiz_data.json'
target_category = sys.argv[1] if len(sys.argv) > 1 else "世界情勢"
today_str = datetime.now().strftime("%Y年%m月%d日")

# --- 2. ニュース取得（取得数を増やして鮮度を上げる） ---
def fetch_news(category):
    # より「最新」「ニュース」に反応するようにクエリを調整
    query = urllib.parse.quote(f"{category} 最新 ニュース")
    url = f"https://news.google.com/rss/search?q={query}&hl=ja&gl=JP&ceid=JP:ja"
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req) as res:
            root = ET.fromstring(res.read())
            # 20件取得して、AIにたっぷり情報を渡すぜ
            items = [item.find('title').text for item in root.findall('.//item')[:20]]
            return "\n".join(items)
    except: return ""

print(f"🚀 【{target_category}】を時事問題モードで生成中...")
news_text = fetch_news(target_category)

# --- 3. プロンプト（Geminiへの「喝」！） ---
# ここで一般常識を禁止し、渡したニュースに固執させる。
prompt = f"""
あなたは時事問題のプロフェッショナルです。
提供された最新ニュースをもとに、{today_str}時点の「{target_category}」に関する4択クイズを100問作成してください。

【厳守ルール】
1. 一般常識（例：国連本部の場所、人口1位の国など）は絶対に禁止です。
2. 必ず、提供された【最新ニュース】に含まれる具体的な事件、人物、発言、数値をもとに問題を作ってください。
3. ニュースが足りない場合は、2025年後半から2026年現在の国際社会における「最新の動向（紛争、選挙、条約、経済指標）」を反映してください。
4. 難易度10は、ニュースの詳細な背景や具体的な数値（％や金額など）を問う高度な時事問題にしてください。

【最新ニュース】
{news_text}

【出力形式】
JSON配列のみ。
[
  {{ "category": "{target_category}", "difficulty": 1, "question": "問題", "choices": ["A","B","C","D"], "answer": "A", "explanation": "解説（何月何日のニュースに基づくか等）" }}
]
"""

# --- 4. 生成 ---
try:
    model = genai.GenerativeModel(MODEL_NAME)
    response = model.generate_content(
        prompt,
        generation_config={"response_mime_type": "application/json", "temperature": 0.8}
    )
    
    new_quizzes = json.loads(response.text)
    
    # マージ
    full_data = []
    if os.path.exists(output_file):
        with open(output_file, "r", encoding="utf-8") as f:
            try: full_data = json.load(f)
            except: full_data = []

    # ジャンル入れ替え
    filtered_data = [q for q in full_data if q.get('category') != target_category]
    updated_data = filtered_data + new_quizzes
    updated_data.sort(key=lambda x: (x.get('category', ''), x.get('difficulty', 1)))

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(updated_data, f, ensure_ascii=False, indent=2)
    
    print(f"✨ ✅ 成功！時事クイズ100問を保存したぜ。")

except Exception as e:
    print(f"🔥 エラー: {e}")
    sys.exit(1)
