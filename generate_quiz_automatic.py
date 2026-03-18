import json
import os
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
import sys
import google.generativeai as genai

# --- 1. 初期設定 ---
API_KEY = os.environ.get("GEMINI_API_KEY")
genai.configure(api_key=API_KEY)

output_file = 'quiz_data.json'
target_category = sys.argv[1] if len(sys.argv) > 1 else "世界情勢"

# --- 2. 使えるモデルを「現場」で直接リストアップ ---
print("🔍 千葉ちゃんのAPIキーで使えるモデルを調査中...")
available_models = []
try:
    for m in genai.list_models():
        if 'generateContent' in m.supported_generation_methods:
            # 'models/' プレフィックスが付いていてもいなくても対応できるように保存
            available_models.append(m.name)
            print(f"  -> 見つけたぜ: {m.name}")

    # 優先順位をつけて最適なモデルを自動選択
    best_model = None
    for priority in ['gemini-1.5-flash', 'gemini-1.5-pro', 'gemini-1.0-pro']:
        for am in available_models:
            if priority in am:
                best_model = am
                break
        if best_model: break

    if not best_model:
        if available_models:
            best_model = available_models[0]
        else:
            raise Exception("使えるモデルが一つも見つからないぜ。APIキーの設定を確認してくれ。")

    print(f"🎯 ターゲット決定: 【 {best_model} 】")

except Exception as e:
    print(f"❌ モデル調査でエラーだ: {e}")
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
    except: return "一般的なニュース知識で作成してください"

news = fetch_news(target_category)

# --- 4. クイズ生成（100問） ---
prompt = f"「{target_category}」に関する4択クイズを難易度1〜10で各10問、計100問作成して。JSON配列のみで出力して。\n【ニュース】\n{news}"

try:
    print(f"🚀 {best_model} を使って100問生成を開始するぜ。ちょっと待っててな...")
    model = genai.GenerativeModel(best_model)
    response = model.generate_content(
        prompt,
        generation_config={"response_mime_type": "application/json", "temperature": 0.7}
    )
    
    new_quizzes = json.loads(response.text)
    
    # マージして保存
    full_data = []
    if os.path.exists(output_file):
        with open(output_file, "r", encoding="utf-8") as f:
            try: full_data = json.load(f)
            except: full_data = []

    filtered = [q for q in full_data if q.get('category') != target_category]
    updated = filtered + new_quizzes
    
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(updated, f, ensure_ascii=False, indent=2)
    
    print(f"✨ ✅ 成功！ {target_category} の 100 問を保存したぜ。千葉ちゃん、やったな！")

except Exception as e:
    print(f"🔥 最後の最後でエラーだ: {e}")
    sys.exit(1)
