import os
import json
import time
from openai import OpenAI

# 初始化 DeepSeek 客户端
client = OpenAI(
    api_key=os.environ.get("DEEPSEEK_API_KEY"),
    base_url="https://api.deepseek.com"
)

def get_category_image(category, item_id):
    """根据分类智能匹配高品质的高清宠物/生态大图"""
    image_map = {
        "Feeding Guide": "https://images.unsplash.com/photo-1534567153574-2b12153a87f0?auto=format&fit=crop&w=1200&q=80",
        "Habitat Setup": "https://images.unsplash.com/photo-1543852786-1cf6624b9987?auto=format&fit=crop&w=1200&q=80",
        "Troubleshooting": "https://images.unsplash.com/photo-1583337130417-3346a1be7dee?auto=format&fit=crop&w=1200&q=80"
    }
    # 如果没有匹配到分类，则使用带有随机种子的高清图备用
    return image_map.get(category, f"https://picsum.photos/1200/600?seed={item_id}")

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
       - An organic recommendation paragraph for the product: "{affiliate}" with a high-conversion call-to-action link `<a href="#" style="background:#ff9900; color:#fff; padding:10px 20px; text-decoration:none; border-radius:5px; font-weight:bold; display:inline-block; margin-top:10px;">Check Price & Reviews on Amazon</a>`.
       - FAQ section with 2-3 common questions.
    3. Tone: Informative, authoritative, friendly, and practical (E-E-A-T compliant).
    """
    
    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = client.chat.completions.create(
                model="deepseek-chat",
                messages=[
                    {"role": "system", "content": "You are a professional SEO content writer and expert pet blogger."},
                    {"role": "user", "content": prompt}
                ],
                stream=False
            )
            return response.choices[0].message.content
        except Exception as e:
            print(f"第 {attempt + 1} 次请求遇到波动: {e}")
            if attempt < max_retries - 1:
                time.sleep(5)
            else:
                raise e

def main():
    if not os.path.exists("keywords.json"):
        print("keywords.json not found")
        return
        
    with open("keywords.json", "r", encoding="utf-8") as f:
        keywords = json.load(f)
        
    posts_list = []
    
    for item in keywords:
        file_name = f"{item['id']}.html"
        img_url = get_category_image(item['category'], item['id'])
        meta_desc = f"Expert guide on {item['target_keyword']}. Learn best practices, care tips, and recommended products."
        
        print(f"Generating article for: {item['target_keyword']}")
        body_content = generate_article_html(item)
        
        html_doc = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{item['target_keyword'].title()} | Exotic Pet Care Guide</title>
    <meta name="description" content="{meta_desc}">
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; line-height: 1.7; color: #2c3e50; max-width: 840px; margin: 0 auto; padding: 20px; background: #f8f9fa; }}
        .container {{ background: #fff; padding: 40px; border-radius: 12px; box-shadow: 0 6px 15px rgba(0,0,0,0.05); }}
        .hero-img {{ width: 100%; height: 380px; object-fit: cover; border-radius: 8px; margin-bottom: 25px; }}
        h1 {{ color: #1a252f; font-size: 2.2em; margin-bottom: 20px; line-height: 1.3; }}
        h2 {{ color: #2c3e50; margin-top: 35px; border-bottom: 2px solid #eaecef; padding-bottom: 8px; font-size: 1.5em; }}
        p, li {{ margin-bottom: 16px; font-size: 1.05em; color: #4a5568; }}
        table {{ width: 100%; border-collapse: collapse; margin: 25px 0; }}
        th, td {{ border: 1px solid #e2e8f0; padding: 14px; text-align: left; }}
        th {{ background: #edf2f7; color: #2d3748; }}
        .back-link {{ display: inline-block; margin-bottom: 25px; color: #3182ce; text-decoration: none; font-weight: 500; }}
        .back-link:hover {{ text-decoration: underline; }}
    </style>
</head>
<body>
    <div class="container">
        <a href="index.html" class="back-link">&larr; Back to Home Hub</a>
        <img src="{img_url}" alt="{item['target_keyword']}" class="hero-img">
        {body_content}
    </div>
</body>
</html>
"""
        with open(file_name, "w", encoding="utf-8") as f:
            f.write(html_doc)
            
        posts_list.append({"title": item['target_keyword'].title(), "url": file_name, "category": item['category'], "img": img_url})
        time.sleep(2)
        
    # 生成现代感十足的首页网格
    index_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Exotic Pet Care & Guide Hub | Expert Advice for Rare Pets</title>
    <meta name="description" content="Your ultimate automated guide to raising jumping spiders, geckos, isopods, and rare exotic pets.">
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; line-height: 1.6; color: #2c3e50; max-width: 1000px; margin: 0 auto; padding: 40px 20px; background: #f4f7f6; }}
        header {{ text-align: center; margin-bottom: 50px; }}
        h1 {{ color: #1a252f; font-size: 2.8em; margin-bottom: 10px; }}
        .subtitle {{ color: #718096; font-size: 1.2em; }}
        .post-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 30px; }}
        .post-card {{ background: #fff; border-radius: 10px; overflow: hidden; box-shadow: 0 4px 10px rgba(0,0,0,0.05); transition: transform 0.2s, box-shadow 0.2s; display: flex; flex-direction: column; }}
        .post-card:hover {{ transform: translateY(-5px); box-shadow: 0 8px 20px rgba(0,0,0,0.1); }}
        .card-img {{ width: 100%; height: 180px; object-fit: cover; }}
        .card-content {{ padding: 20px; display: flex; flex-direction: column; flex-grow: 1; }}
        .post-card h2 {{ margin: 0 0 15px 0; font-size: 1.25em; line-height: 1.4; }}
        .post-card h2 a {{ color: #2b6cb0; text-decoration: none; }}
        .post-card h2 a:hover {{ text-decoration: underline; }}
        .tag {{ display: inline-block; background: #edf2f7; color: #4a5568; padding: 4px 12px; border-radius: 20px; font-size: 0.8em; font-weight: 500; margin-top: auto; align-self: flex-start; }}
    </style>
</head>
<body>
    <header>
        <h1>Exotic Pet Care Hub</h1>
        <p class="subtitle">Your ultimate guide to raising jumping spiders, geckos, and rare pets.</p>
    </header>
    <main class="post-grid">
"""
    for p in posts_list:
        index_html += f"""
        <div class="post-card">
            <img src="{p['img']}" alt="{p['title']}" class="card-img">
            <div class="card-content">
                <h2><a href="{p['url']}">{p['title']}</a></h2>
                <span class="tag">{p['category']}</span>
            </div>
        </div>
        """
        
    index_html += """
    </main>
</body>
</html>
"""
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(index_html)
    print("index.html generated successfully with responsive grid and images!")

if __name__ == "__main__":
    main()
