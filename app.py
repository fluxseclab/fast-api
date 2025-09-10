import os
import random
import requests
import cloudscraper

from bs4 import BeautifulSoup
from flask import (Flask,
    jsonify,
    request
)
from concurrent.futures import (
    ThreadPoolExecutor,
    as_completed
)
from openai import OpenAI


app = Flask(__name__)
scraper = cloudscraper.create_scraper()
AI_KEY = os.getenv('OPENAI_API_KEY')
client = OpenAI(api_key=AI_KEY)
cache = {}
MAX_THREADS = 10


def fetch_and_extract(url):
    if url in cache:
        return cache[url]

    try:
        response = scraper.get(url)
        response.raise_for_status()

        text = BeautifulSoup(response.text, "html.parser").get_text(separator=" ")
        clean_text = " ".join(text.split())
        
        response = client.responses.create(
            model='gpt-4o-mini',
            input= f'این متن رو به فارسی ترجمه کن به صورت تخصصی برای هکر ها و برنامه نویسان و بعد از اون فقط با html tag ها استایل دهیش کن بدون هیچگونه css و اینم بدون که این بخشی از یک فایل html است قراره این بین یک فایل base.html لود بشه محتواش پس نیاز نیست tag های تکراری html رو بنویسی فقط و فقط تگ main که محتواش رو هم خودت ترجمه میکنی  :"{clean_text}"'
        )
        
        cache[url] = response.output_text.strip('```html').strip('```')
        return response.output_text.strip('```html').strip('```')

    except Exception as e:
        print(f"Error extracting {url}: {e}")
        return clean_text


@app.route("/scrape")
def scrape():
    url = request.args.get("url")
    if not url:
        return jsonify({"error": "No URL provided"}), 400

    content = fetch_and_extract(url)
    if not content:
        return jsonify({"error": "Could not extract content. Maybe the page structure changed or URL is invalid."}), 500

    return jsonify({
        "url": url,
        "content": content
    })


@app.route("/")
def home():
    
    try:
        response = requests.get('https://thehackernews.com/')
        response.raise_for_status()
        urls = set()
        lines = response.text.split('\n')

        with ThreadPoolExecutor(max_workers=MAX_THREADS) as executor:
            futures = [executor.submit(extract_url, line) for line in lines if 'https://thehackernews.com' in line and '.html' in line]

            for future in as_completed(futures):
                url = future.result()
                if url:
                    urls.add(url)

        url_cache = list(urls)
        return jsonify({"urls": url_cache})

    except Exception as e:
        print(f"Home Page Fetch Error: {e}")
        return jsonify({"error": str(e)}), 500


def extract_url(line):
    soup = BeautifulSoup(line, "html.parser")
    a = soup.find("a", href=True)
    return a['href'] if a and a['href'].endswith('.html') else None



@app.route("/ping")
def ping():
    return jsonify({"status": "ok"})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
