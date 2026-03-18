import json
import time
import os
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from google import genai
from google.genai import types

# APIキー設定
API_KEY = os.environ.get("GEMINI_API_KEY")
client = genai.Client(api_key=API_KEY)

output_file = 'quiz_data.json'
categories = ["世界情勢", "日本の政治", "文化", "エンタテイメント", "ゲーム", "アニメ", "AI"]
yesterday_str = (datetime.now() - timedelta(days=1)).strftime("%Y年%m月%d日")

# --- ニュース取得関数（千葉ちゃんロジック採用！） ---
def fetch_news_text(category):
    """GoogleニュースのRSSから最新ニュースの見出しをサクッと取得する"""
    query = urllib.parse.quote(f"{category} ニュース")
    url = f"https://news.google.com/rss/search?q={query}&hl=ja&gl=JP&ceid=JP:ja"
    
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req) as response:
            xml_data = response.read()
            
        root = ET.fromstring(xml_data)
        news_text = ""
        count = 0
        
        # 最新15件の見出しだけを抽出
        for item in root.findall('.//item'):
            if count >= 15:
                break
            title = item.find('title').text
            news_text += f"・{title}\n"
            count += 1
            
        return news_text
    except Exception as e:
        print(f"  ⚠️ ニュース取得エラー ({category}): {e}")
        return ""
# --------------------------------------

all_quiz_data = []
print(f"🚀 {yesterday_str} のクイズ生成を開始（一括生成・軽量モード）")

for category in categories:
    print(f"\n📦 ジャンル: 【{category}】のニュースを取得中...")
    
    # 1. まずPython側でニュースを取得する
    news_text = fetch_news_text(category)
    if not news_text:
        news_text = "（ニュースの取得に失敗したため、一般的な知識でクイズを作成してください）"
    
    print(f"  ✅ ニュース取得完了！Geminiにクイズ作成を依頼します...")

    # 2. 取得したテキストをプロンプトに埋め込む
    prompt = f"""
    以下の最新ニュース見出しを参考にして、{yesterday_str}の「{category}」に関する4択クイズを
    難易度レベル1から10まで、それぞれ1問ずつ（合計10問）作成してください。
    
    【参考ニュース】
    {news_text}
    
    【ルール】
    - Level 1は一般常識、Level 10は超マニアックな専門知識としてください。
    - ニュースの内容をベースにしつつ、情報が足りない場合は一般知識を補って問題を作ってください。
    - 各問題のテーマが重複しないように工夫してください。
    
    出力は以下のJSON配列形式のみとしてください：
    [
      {{ "category": "{category}", "difficulty": 1, "question": "問題文", "choices": ["肢1", "肢2", "肢3", "肢4"], "answer": "正解", "explanation": "解説" }},
      ...（難易度10まで10個のオブジェクトを並べる）
    ]
    """
    
    success = False
    for attempt in range(3): # 失敗しても3回までリトライ
        try:
            # 3. 検索ツールを外し、JSON出力を強制する！
            response = client.models.generate_content(
                model='gemini-2.0-flash',
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.7,
                    response_mime_type="application/json" # ← ★ここが最強の保険！
                )
            )
            
            # JSON形式が保証されているので、そのまま安全に読み込める
            data = json.loads(response.text)
            
            if isinstance(data, list) and len(data) > 0:
                all_quiz_data.extend(data)
                print(f"  ✅ {category}: 10問生成に成功したぜ！")
                success = True
                break
        except Exception as e:
            print(f"  ⚠️ {category}: リトライ中... (エラー: {e})")
            time.sleep(30)
    
    if not success:
        print(f"  ❌ {category}: 最終的に失敗。このジャンルは飛ばします。")
    
    # 処理が劇的に軽くなったので、インターバルは20秒で十分！
    print("  💤 次のジャンルへ行く前に少し待機（20秒）...")
    time.sleep(20)

# 最後に保存（1問でもあれば保存する）
if len(all_quiz_data) > 0:
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(all_quiz_data, f, ensure_ascii=False, indent=2)
    print(f"\n✨ 合計 {len(all_quiz_data)} 問のクイズを納品したぜ！")
else:
    print("\n😱 1問も作られなかった。ビルドを失敗させます。")
    exit(1)
