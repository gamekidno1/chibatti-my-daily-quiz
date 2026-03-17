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
categories = ["世界情勢", "日本の政治", "文化", "エンタテイメント", "ゲーム", "アニメ", "AI"]
yesterday_str = (datetime.now() - timedelta(days=1)).strftime("%Y年%m月%d日")

all_quiz_data = []
print(f"🚀 {yesterday_str} のクイズ生成を開始（一括生成モード）")

for category in categories:
    print(f"\n📦 ジャンル: 【{category}】をまとめて生成中...")
    
    # 1回の注文で10問分まとめて考えさせる！
    prompt = f"""
    Google検索を使用して、{yesterday_str}の「{category}」に関する最新ニュースをいくつか調べ、
    難易度レベル1から10まで、それぞれ1問ずつ（合計10問）の4択クイズを作成してください。
    
    【ルール】
    - Level 1は一般常識、Level 10は超マニアックな専門知識としてください。
    - 各問題のニュースが重複しないように工夫してください。
    
    出力は必ず以下のJSON配列形式のみとしてください。余計な文章は一切含めないでください：
    [
      {{ "category": "{category}", "difficulty": 1, "question": "問題文", "choices": ["肢1", "肢2", "肢3", "肢4"], "answer": "正解", "explanation": "解説" }},
      ...（難易度10まで10個のオブジェクトを並べる）
    ]
    """
    
    success = False
    for attempt in range(3): # 失敗しても3回までリトライ
        try:
            response = client.models.generate_content(
                model='gemini-2.0-flash',
                contents=prompt,
                config=types.GenerateContentConfig(
                    tools=[{"google_search": {}}], 
                    temperature=0.7
                )
            )
            # JSON部分だけを抽出
            text = response.text.strip().replace('```json', '').replace('```', '').strip()
            data = json.loads(text)
            
            if isinstance(data, list) and len(data) > 0:
                all_quiz_data.extend(data)
                print(f"  ✅ {category}: 10問生成に成功したぜ！")
                success = True
                break
        except Exception as e:
            print(f"  ⚠️ {category}: リトライ中... (エラー: {e})")
            time.sleep(30) # 429回避のために長めに休む
    
    if not success:
        print(f"  ❌ {category}: 最終的に失敗。このジャンルは飛ばします。")
    
    # ジャンルごとに20秒休ませてGeminiの怒りを鎮める
    print("  💤 Geminiを休ませています（20秒）...")
    time.sleep(20)

# 最後に保存（1問でもあれば保存する）
if len(all_quiz_data) > 0:
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(all_quiz_data, f, ensure_ascii=False, indent=2)
    print(f"\n✨ 合計 {len(all_quiz_data)} 問のクイズを納品したぜ！")
else:
    print("\n😱 1問も作られなかった。ビルドを失敗させます。")
    exit(1)
