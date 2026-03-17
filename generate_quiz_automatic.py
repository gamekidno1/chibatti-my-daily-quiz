import json
import time
import os
from datetime import datetime, timedelta
from google import genai
from google.genai import types

# GitHubの「金庫」からAPIキーを読み込む
API_KEY = os.environ.get("GEMINI_API_KEY")
client = genai.Client(api_key=API_KEY)

output_file = 'quiz_data.json' # 同じ場所に保存

categories = ["世界情勢", "日本の政治", "文化", "エンタテイメント", "ゲーム", "アニメ", "AI"]
yesterday_str = (datetime.now() - timedelta(days=1)).strftime("%Y年%m月%d日")

all_quiz_data = []
print(f"🌍 {yesterday_str} のニュースから生成開始...")

for category in categories:
    print(f"▶️ ジャンル: 【{category}】")
    for difficulty in range(1, 11):
        prompt = f"Google検索を使って、{yesterday_str}の「{category}」に関する最新ニュースから、重複のない話題で4択クイズを10問、難易度レベル{difficulty}で作成して。JSON配列形式で出力。"
        for attempt in range(3):
            try:
                response = client.models.generate_content(
                    model='gemini-2.5-flash',
                    contents=prompt,
                    config=types.GenerateContentConfig(tools=[{"google_search": {}}], temperature=0.7)
                )
                text = response.text.strip().replace('```json', '').replace('```', '').strip()
                all_quiz_data.extend(json.loads(text))
                print(f"  ✅ 難易度 {difficulty} : 成功")
                time.sleep(5)
                break
            except:
                time.sleep(15)

with open(output_file, "w", encoding="utf-8") as f:
    json.dump(all_quiz_data, f, ensure_ascii=False, indent=2)

print("🎉 完了！")
