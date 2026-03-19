import json
import os
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
import sys
from datetime import datetime
import google.generativeai as genai

# 基本設定
API_KEY = os.environ.get("GEMINI_API_KEY")
genai.configure(api_key=API_KEY)
MODEL_NAME = "gemini-1.5-flash"  # Quota制限が最も緩く安定しているモデル
output_file = 'quiz_data.json'
target_category = sys.argv[1] if len(sys.argv) > 1 else "世界情勢"
today_str = datetime.now().strftime("%Y年%m月%d日")

def fetch_news(category):
    query = urllib.parse.quote(f"{category} 最新 ニュース")
    url = f"https://news.google.com/rss/search?q={query}&hl=ja&gl=JP&ceid=JP:ja"
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=10) as res:
            root = ET.fromstring(res.read())
            items = [item.find('title').text for item in root.findall('.//item')[:15]]
            return "\n".join(items)
    except: return ""

print(f"🚀 【{target_category}】の最新100問を生成中...")
news = fetch_news(target_category)

# 【修正ポイント①】JSONのフォーマット（ひな形）を完全に指定し、サボりを許さない
prompt = f"""
あなたは時事問題のプロです。提供された最新ニュースをもとに、{today_str}時点の「{target_category}」に関する4択クイズを100問作成してください。

【鉄則】
1. 一般常識（国連の場所、過去の人口統計など）は禁止です。
2. 必ず提供された最新ニュース、または2025年後半から2026年現在の動向に基づいて出題してください。
3. 出力は以下のJSON配列形式とキー構成を【完全に】守ること。これ以外のフォーマットはシステムエラーを引き起こすため絶対に避けてください。
4. 難易度(difficulty)は1から10まで、各レベル10問ずつ作成すること。

【必須JSONフォーマット】
[
  {{
    "category": "{target_category}",
    "difficulty": 1,
    "question": "ニュースに基づいた問題文",
    "choices": ["選択肢A", "選択肢B", "選択肢C", "選択肢D"],
    "answer": "正解の選択肢",
    "explanation": "解説（必ずいつのニュースかを含めること）"
  }}
]

【最新ニュース】
{news if news else "2026年現在の最新トレンド"}
"""

try:
    model = genai.GenerativeModel(MODEL_NAME)
    response = model.generate_content(
        prompt,
        generation_config={"response_mime_type": "application/json", "temperature": 0.7}
    )
    
    new_quizzes = json.loads(response.text)
    
    # 🛡️ 【修正ポイント②】絶対防衛ライン（バリデーション）
    # ここでデータを厳しくチェックし、ダメならエラーを出して上書きを阻止する
    if not isinstance(new_quizzes, list) or len(new_quizzes) == 0:
        raise ValueError("生成されたデータが空、または配列形式ではありません。")
        
    required_keys = {"category", "difficulty", "question", "choices", "answer", "explanation"}
    for i, q in enumerate(new_quizzes):
        # 必須項目が全て揃っているかチェック
        if not required_keys.issubset(q.keys()):
            raise ValueError(f"{i+1}問目のデータに必須項目が欠けています: {list(q.keys())}")
        # 選択肢がちゃんと4つあるかチェック
        if not isinstance(q["choices"], list) or len(q["choices"]) != 4:
            raise ValueError(f"{i+1}問目の選択肢が4つではありません。")
        # カテゴリ名がターゲットと一致しているかチェック（勝手な名前変更を許さない）
        if q["category"] != target_category:
            raise ValueError(f"{i+1}問目のカテゴリ名が '{target_category}' ではありません（実際: '{q.get('category')}'）。")
            
    print(f"🛡️ 検問クリア！正常な問題データ {len(new_quizzes)}問 を確認しました。上書き処理に移行します。")

    # 既存データの読み込みとマージ
    full_data = []
    if os.path.exists(output_file):
        with open(output_file, "r", encoding="utf-8") as f:
            try: full_data = json.load(f)
            except: full_data = []

    # 指定ジャンルのみ入れ替え
    filtered = [q for q in full_data if q.get('category') != target_category]
    updated = filtered + new_quizzes
    
    # カテゴリと難易度で綺麗に並べ替え
    updated.sort(key=lambda x: (x.get('category', ''), x.get('difficulty', 1)))

    # 検問をクリアした安全なデータだけを上書き保存
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(updated, f, ensure_ascii=False, indent=2)
    
    print(f"✅ {target_category} の更新が完了し、本番環境に反映されました！")

except Exception as e:
    # エラーが起きた場合はここに飛んでくるため、上書き処理（with open("w")）は実行されない
    print(f"❌ エラー発生: {e}")
    print("⚠️ 安全装置が作動しました。不良品データのため、既存の quiz_data.json は上書きされずに保護されました。")
    sys.exit(1)
