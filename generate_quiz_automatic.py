import json
import os
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
import sys
from datetime import datetime, timedelta
import google.generativeai as genai

# --- 1. 初期診断 ---
print("🔍 診断開始...")
API_KEY = os.environ.get("GEMINI_API_KEY")
if not API_KEY:
    print("❌ APIキーが環境変数に見当たらないぜ！")
    sys.exit(1)

genai.configure(api_key=API_KEY)
# 最も標準的なモデル名に固定
MODEL_NAME = "gemini-1.5-flash"
output_file = 'quiz_data.json'
target_category = sys.argv[1] if len(sys.argv) > 1 else "世界情勢"
today_str = datetime.now().strftime("%Y年%m月%d日")

# --- 2. ニュース取得（安全策） ---
def fetch_news(category):
    print(f"📡 【{category}】の最新ニュースをGoogleから取得中...")
    query = urllib.parse.quote(f"{category} 最新 ニュース")
    url = f"https://news.google.com/rss/search?q={query}&hl=ja&gl=JP&ceid=JP:ja"
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=10) as res:
            root = ET.fromstring(res.read())
            items = []
            for item in root.findall('.//item')[:15]:
                title = item.find('title').text
                if title: items.append(title)
            print(f"✅ ニュースを {len(items)} 件取得したぜ。")
            return "\n".join(items)
    except Exception as e:
        print(f"⚠️ ニュース取得で軽微なエラー（スキップするぜ）: {e}")
        return ""

news_text = fetch_news(target_category)

# --- 3. プロンプト作成 ---
prompt = f"""
あなたは時事クイズ制作のプロです。提供された最新ニュースをもとに、{today_str}時点の「{target_category}」に関する4択クイズを100問作成してください。
【条件】
- 一般常識（過去の人口や場所など）は禁止。
- 必ず提供ニュース、または2025年〜2026年現在の最新動向から出題すること。
- 難易度1〜10まで各10問。
- 出力はJSON配列形式のみ。
【最新ニュース】
{news_text if news_text else "最新の国際情勢、テクノロジー動向に基づき作成してください"}
"""

# --- 4. Gemini実行 ---
print(f"🤖 Gemini ({MODEL_NAME}) に100問生成を依頼中...（これには1分ほどかかるぜ）")
try:
    model = genai.GenerativeModel(MODEL_NAME)
    response = model.generate_content(
        prompt,
        generation_config={"response_mime_type": "application/json", "temperature": 0.8}
    )
    
    if not response.text:
        raise Exception("Geminiからの返答が空だぜ")
    
    new_quizzes = json.loads(response.text)
    print(f"✅ クイズ {len(new_quizzes)} 問の生成に成功！")

    # --- 5. 保存 ---
    full_data = []
    if os.path.exists(output_file):
        with open(output_file, "r", encoding="utf-8") as f:
            try: full_data = json.load(f)
            except: full_data = []

    # ジャンル入れ替え
    filtered = [q for q in full_data if q.get('category') != target_category]
    updated = filtered + new_quizzes
    updated.sort(key=lambda x: (x.get('category', ''), x.get('difficulty', 1)))

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(updated, f, ensure_ascii=False, indent=2)
    
    print(f"✨ 全ての工程が完了したぜ！プロデューサー！")

except Exception as e:
    print(f"🔥 実行エラー発生: {e}")
    sys.exit(1)
