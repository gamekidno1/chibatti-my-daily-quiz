import json
import time
import os
from datetime import datetime, timedelta
from google import genai
from google.genai import types

# APIキー設定
API_KEY = os.environ.get("GEMINI_API_KEY")
client = genai.Client(api_key=API_KEY)

output_file = 'quiz_data.json'
# テストのために、まずはジャンルを絞るのもアリだぜ！
categories = ["AI"]
yesterday_str = (datetime.now() - timedelta(days=1)).strftime("%Y年%m月%d日")

all_quiz_data = []
print(f"🚀 {yesterday_str} のクイズ生成を開始します...")

for category in categories:
    print(f"\n📂 ジャンル: 【{category}】")
    # 負荷を分散するため、1つのジャンルごとに1問ずつ確実に作っていくぞ
    for difficulty in range(1, 11):
        prompt = f"""
        Google検索を使用して、{yesterday_str}の「{category}」に関する最新ニュースを調べ、
        そのニュースに基づいた4択クイズを1問作成してください。
        難易度はレベル{difficulty}（1=一般常識, 10=超マニアック）としてください。
        
        出力は必ず以下のJSON配列形式のみとしてください。余計な解説は不要です：
        [{{ "category": "{category}", "difficulty": {difficulty}, "question": "問題文", "choices": ["選択肢1", "選択肢2", "選択肢3", "選択肢4"], "answer": "正解の選択肢", "explanation": "解説文" }}]
        """
        
        success = False
        for attempt in range(2): # 失敗しても2回まで粘るぜ
            try:
                response = client.models.generate_content(
                    model='gemini-2.0-flash', # 高速・安定モデル
                    contents=prompt,
                    config=types.GenerateContentConfig(tools=[{"google_search": {}}], temperature=0.7)
                )
                # JSONだけを抜き出す魔法の処理
                text = response.text.strip().replace('```json', '').replace('```', '').strip()
                data = json.loads(text)
                if isinstance(data, list) and len(data) > 0:
                    all_quiz_data.extend(data)
                    print(f"  ✅ Level {difficulty}: 成功")
                    success = True
                    break
            except Exception as e:
                print(f"  ⚠️ Level {difficulty}: リトライ中... ({e})")
                time.sleep(5)
        
        if not success:
            print(f"  ❌ Level {difficulty}: 失敗。スキップします。")
        
        time.sleep(1) # サーバーに優しく

# 最後に「中身があるときだけ」保存する！
if len(all_quiz_data) > 0:
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(all_quiz_data, f, ensure_ascii=False, indent=2)
    print(f"\n✨ 合計 {len(all_quiz_data)} 問のクイズを保存したぜ！")
else:
    print("\n😱 クイズが1問も作られなかったぜ。保存を中止してエラーを出します。")
    exit(1) # これでGitHub Actions側に「失敗（❌）」と知らせる
