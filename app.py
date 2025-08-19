import requests as req
import cloudscraper
import os
import random
from bs4 import BeautifulSoup
from flask import Flask, jsonify, request
from concurrent.futures import ThreadPoolExecutor, as_completed

app = Flask(__name__)
scraper = cloudscraper.create_scraper()

cache = {}

MAX_THREADS = 10

def fetch_and_extract(url):
    if url in cache:
        return cache[url]

    try:
        r = scraper.get(url)
        r.raise_for_status()

        start_idx = r.text.index('<h1')
        end_idx = r.text.index('Found this article interesting?')
        final_text = r.text[start_idx:end_idx].strip().replace('\n', '')
        final_text += '</div>'
        
        cache[url] = final_text
        return final_text

    except Exception as e:
        print(f"Error extracting {url}: {e}")
        return None

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
        response = req.get('https://thehackernews.com/')
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
    try:
        start_idx = line.index('href=') + 6
        end_idx = line.index('.html') + 5
        return line[start_idx:end_idx]
    except ValueError:
        return None

@app.route("/ping")
def ping():
    return jsonify({"status": "ok"})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
