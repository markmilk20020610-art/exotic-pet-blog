import os
import json
import time
from google import genai

client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

def generate_article_html(keyword_data):
    topic = keyword_data["topic"]
    keyword = keyword_data["target_keyword"]
    affiliate = keyword_data["affiliate_product"]
    
    prompt = f"""
    You are an expert exotic pet care specialist and professional pet blogger. 
    Write a comprehensive, engaging, and SEO-optimized blog post in English based on the following target keyword:
    
    Target Keyword: "{keyword}"
    Main Topic: {topic}
    Recommended Affiliate Product to organically mention: {affiliate}
    
    Requirements:
    1. Output format: Clean HTML body content (use <h2>, <h3>, <p>, <ul>, <li>, <table>, <tr>, <th>, <td> tags, do NOT include markdown code blocks like ```html).
    2. Structure: 
       - Catchy <h1> Title containing the exact keyword.
       - Introduction hooking the reader with a common beginner pain point.
       - 3 to 4 detailed <h2> headings with actionable advice, steps, or bullet points.
       - A comparison table (<table>) for quick reading.
       - An organic recommendation paragraph for the product: "{affiliate}" with a link `<a href=" ">Check Price on Amazon</a >`.
       - FAQ section with 2-3 common questions.
    3. Tone: Informative, authoritative, friendly, and practical (E-E-A-T compliant).
    """
    
    # 使用更新后的最新模型
    response = client.models.generate_content(
        model='gemini-3.8-flash',
        contents=prompt,
    )
    return response.text

def main():
    if not os.path.exists("keywords.json"):
        print("keywords.json not found")
        return
        
    with open("keywords.json", "r", encoding="utf-8") as f:
        keywords = json.load(f)
        
    posts_list = []
    
    for item in keywords:
        file_name = f"{item['id']}.html"
        
        if os.path.exists(file_name):
            print(f"Skipping existing: {file_name}")
            posts_list.append({"title": item['target_keyword'].title(), "url": file_name, "category": item['category']})
            continue
            
        print(f"Generating article for: {item['target_keyword']}")
        body_content = generate_article_html(item)
        
        html_doc = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{item['target_keyword'].title()} | Exotic Pet Care Guide</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; line-height: 1.6; color: #333; max-width: 800px; margin: 0 auto; padding: 20px; background: #f9f9f9; }}
        .container {{ background: #fff; padding: 40px; border-radius: 8px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); }}
        h1 {{ color: #2c3e50; font-size: 2em; margin-bottom: 20px; }}
        h2 {{ color: #34495e; margin-top: 30px; border-bottom: 2px solid #ecf0f1; padding-bottom: 5px; }}
        p, li {{ margin-bottom: 15px; }}
        table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
        th, td {{ border: 1px solid #ddd; padding: 12px; text-align: left; }}
        th {{ background: #f4f6f7; }}
        .back-link {{ display: inline-block; margin-bottom: 20px; color: #3498db; text-decoration: none; }}
        .back-link:hover {{ text-decoration: underline; }}
    </style>
</head>
<body>
    <div class="container">
        <a href="index.html" class="back-link">&larr; Back to Home</a >
        {body_content}
    </div>
</body>
</html>
"""
        with open(file_name, "w", encoding="utf-8") as f:
            f.write(html_doc)
            
        posts_list.append({"title": item['target_keyword'].title(), "url": file_name, "category": item['category']})
        time.sleep(2)
        
    index_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Exotic Pet Care & Guide Hub</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; line-height: 1.6; color: #333; max-width: 900px; margin: 0 auto; padding: 40px 20px; background: #f4f7f6; }}
        header {{ text-align: center; margin-bottom: 40px; }}
        h1 {{ color: #2c3e50; font-size: 2.5em; }}
        .subtitle {{ color: #7f8c8d; font-size: 1.1em; }}
        .post-grid {{ display: grid; grid-template-columns: 1fr; gap: 20px; }}
        .post-card {{ background: #fff; padding: 25px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); transition: transform 0.2s; }}
        .post-card:hover {{ transform: translateY(-3px); box-shadow: 0 4px 8px rgba(0,0,0,0.1); }}
        .post-card h2 {{ margin: 0 0 10px 0; font-size: 1.4em; }}
        .post-card h2 a {{ color: #2980b9; text-decoration: none; }}
        .post-card h2 a:hover {{ text-decoration: underline; }}
        .tag {{ display: inline-block; background: #eef2f3; color: #555; padding: 4px 10px; border-radius: 4px; font-size: 0.85em; margin-top: 10px; }}
    </style>
</head>
<body>
    <header>
        <h1>Exotic Pet Care Hub</h1>
        <p class="subtitle">Your ultimate guide to raising jumping spiders, geckos, and rare pets.</p >
    </header>
    <main class="post-grid">
"""
    for p in posts_list:
        index_html += f"""
        <div class="post-card">
            <h2><a href="{p['url']}">{p['title']}</a ></h2>
            <span class="tag">{p['category']}</span>
        </div>
        """
        
    index_html += """
    </main>
</body>
</html>
"""
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(index_html)
    print("index.html generated successfully!")

if __name__ == "__main__":
    main()
