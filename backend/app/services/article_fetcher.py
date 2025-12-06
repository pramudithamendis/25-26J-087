import requests
import feedparser
from newspaper import Article
import time
import re
from typing import List, Dict
#from app.config import settings
from datetime import datetime
import json

GNEWS_API_KEY="dff26edec4353fecfdfeeb50ebec103c"
RSS_FEEDS = {
    "tech_news": [
        "https://medium.com/feed/topic/technology",
        "https://hackernoon.com/feed",
        "https://www.reddit.com/r/programming/.rss"
    ],
}

ARTICLES_PER_TOPIC = 50

def clean_text(text: str) -> str:
    if not text:
        return ""
    text = re.sub(r"\n+", " ", text)
    text = re.sub(r"\s{2,}", " ", text)
    return text.strip()

def get_full_article(url: str) -> str:
    try:
        a = Article(url)
        a.download()
        a.parse()
        return clean_text(a.text)
    except:
        return ""

def fetch_gnews_articles(topics: List[str]) -> List[Dict]:
    articles = []
    for topic in topics:
        url = f"https://gnews.io/api/v4/search?q={topic}&token={GNEWS_API_KEY}&lang=en&max={ARTICLES_PER_TOPIC}"
        try:
            r = requests.get(url, timeout=10)
            r.raise_for_status()
            data = r.json()
        except Exception as e:
            print(f"Error fetching GNews: {e}")
            continue

        for art in data.get("articles", []):
            title = art.get("title", "")
            summary = art.get("description", "")
            link = art.get("url", "")
            full_text = get_full_article(link) or summary
            articles.append({
                "title": title,
                "summary": summary,
                "full_text": full_text,
                "topic": topic,
                "published_date": art.get("publishedAt", ""),
                "source_type": "gnews"
            })
            time.sleep(0.1)
    return articles

def fetch_rss_articles(max_per_feed=20) -> List[Dict]:
    articles = []
    for category, urls in RSS_FEEDS.items():
        for feed_url in urls:
            try:
                parsed = feedparser.parse(feed_url)
            except Exception as e:
                print(f"Failed to parse {feed_url}: {e}")
                continue
            for entry in parsed.entries[:max_per_feed]:
                url = entry.get("link", "")
                title = entry.get("title", "")
                summary = clean_text(entry.get("summary", ""))
                full_text = get_full_article(url) or summary
                articles.append({
                    "title": title,
                    "summary": summary,
                    "full_text": full_text,
                    "topic": category,
                    "published_date": entry.get("published", ""),
                    "source_type": "rss"
                })
                time.sleep(0.1)
    return articles

def fetch_all_articles(topics: List[str], save_to_file: bool = True) -> List[Dict]:
    articles = fetch_gnews_articles(topics)
    articles += fetch_rss_articles()
    print(f"Total articles fetched: {len(articles)}")

    if save_to_file:
        week_str = datetime.utcnow().strftime("%Y-%m-%d")
        filename = f"app/data/articles/articles_{week_str}.json"
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(articles, f, ensure_ascii=False, indent=2)
        print(f"Saved articles to {filename}")

    return articles
