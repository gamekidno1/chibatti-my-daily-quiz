import json
import os
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
import sys
import time
from datetime import datetime, timedelta
import google.generativeai as genai

# --- 1. 初期設定 ---
API_KEY = os.environ.get("GEMINI_API_KEY")
genai.configure(api_key=API_KEY)

output_file = 'quiz_data.json'
target_category = sys.argv[1] if len(sys.argv) > 1 else "世界情勢"
yesterday_str = (datetime.now() - timedelta(days=1)).strftime("%Y年%m月%d日")

# --- 2. 使えるモデルを自動検出（これが404対策の決定打だぜ！） ---
print("🔍 使えるモデルを探しているぜ...")
available_models = []
try:
    for m in genai.list_models():
        if 'generateContent' in m.supported_generation_methods:
            available_models.append(m.name)
    
    # 優先順位：2.0-flash > 1.5-flash > 1.5-flash-latest > その他
    best_model = None
    for priority in ['gemini-2.0-flash', 'gemini-1.5-flash', '1.5-flash']:
        for am in available_models:
            if priority in am:
                best_model = am
                break
        if best_model: break
    
    if not best_model and available_models:
        best_model = available_models[0]
    
    if not best_model:
        raise Exception("使えるモデルが一つも見つからないぜ...APIキーを確認してくれ。")
        
    print(f"✅ ターゲットモデル決定: {best_model}")

except Exception as e:
    print(f"❌ モデルリスト取得エラー: {e}")
    sys.exit(1)

# --- 3. ニュース取得 ---
def fetch_news(category):
    query = urllib.parse.quote(f"{category} ニュース")
    url = f"https://news.google.com/rss/search?q={query}&hl=ja&gl=JP&ceid=JP:ja"
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req) as res:
            root = ET.fromstring(res.read())
            return "\n".join([item.find('title').text for item in root.findall('.//item')[:15]])
    except: return ""

print(f"🚀 【{target_category}】の最新クイズ100問を生成中...")
news = fetch_news(target_category)

prompt = f"""
{yesterday_str}時点の「{target_category}」に関する4択クイズを100問作成してください。
【ニュース】
{news}
【ルール】
- 難易度レベル1〜10まで各10問、計100問。
- JSON配列形式のみで出力。
"""

# --- 4. クイズ生成 ---
try:
    model = genai.GenerativeModel(best_model)
    response = model.generate_content(
        prompt,
        generation_config={"response_mime_type": "application/json", "temperature": 0.7}
    )
    
    new_quizzes = json.loads(response.text)
    
    # データ読み込みとマージ
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
    
    print(f"✨ 完遂！ {target_category} の 100 問を保存したぜ。")

except Exception as e:
    print(f"❌ 生成失敗: {e}")
    sys.exit(1)
