import requests
import feedparser
from newspaper import Article
import time
import re
from typing import List, Dict
from datetime import datetime
from app.models.article_model import articles_collection

# -------------------------
# CONFIG
# -------------------------

GNEWS_API_KEY = "dff26edec4353fecfdfeeb50ebec103c"

RSS_FEEDS = {
    "tech_news": [
        "https://medium.com/feed/topic/technology",
        "https://hackernoon.com/feed",
        "https://www.reddit.com/r/programming/.rss"
    ]
}

ARTICLES_PER_TOPIC = 50

# -------------------------
# UTILITIES
# -------------------------

# Clean text by removing excessive whitespace and newlines
def clean_text(text: str) -> str:
    if not text:
        return ""
    text = re.sub(r"\n+", " ", text) # Replace newlines with space
    text = re.sub(r"\s{2,}", " ", text) # Replace multiple spaces with single space
    return text.strip()

# Fetch full article text using newspaper3k
def get_full_article(url: str) -> str:
    try:
        article = Article(url) # Initialize article object
        article.download()
        article.parse()
        return clean_text(article.text)
    except Exception:
        return ""

# Avoid refetching the same week
def current_week_id() -> str:
    """
    Returns ISO week id: 2025-W03
    """
    year, week, _ = datetime.utcnow().isocalendar()
    return f"{year}-W{week:02d}"


def current_month_id() -> str:
    """
    Returns month id: 2025-01
    """
    return datetime.utcnow().strftime("%Y-%m")


# -------------------------
# FETCHERS
# -------------------------

def fetch_gnews_articles(topics: List[str]) -> List[Dict]:
    articles = []

    for topic in topics:
        url = (
            f"https://gnews.io/api/v4/search?"
            f"q={topic}&lang=en&max={ARTICLES_PER_TOPIC}&token={GNEWS_API_KEY}"
        )

        try:
            r = requests.get(url, timeout=10)
            r.raise_for_status()
            data = r.json()
        except Exception as e:
            print(f"[WARN] GNews failed for topic '{topic}': {e}")
            continue

        for art in data.get("articles", []):
            full_text = get_full_article(art.get("url")) or art.get("description", "")

            articles.append({
                "title": art.get("title"),
                "summary": art.get("description"),
                "full_text": full_text,
                "topic": topic,
                "published_date": art.get("publishedAt"),
                "source_type": "gnews",
                "url": art.get("url"),
            })

            time.sleep(0.1)

    return articles


def fetch_rss_articles(max_per_feed: int = 20) -> List[Dict]:
    articles = []

    for category, feeds in RSS_FEEDS.items():
        for feed_url in feeds:
            try:
                parsed = feedparser.parse(feed_url)
            except Exception:
                continue

            for entry in parsed.entries[:max_per_feed]:
                full_text = get_full_article(entry.get("link")) or entry.get("summary", "")

                articles.append({
                    "title": entry.get("title"),
                    "summary": clean_text(entry.get("summary", "")),
                    "full_text": full_text,
                    "topic": category,
                    "published_date": entry.get("published"),
                    "source_type": "rss",
                    "url": entry.get("link"),
                })

                time.sleep(0.1)

    return articles


# -------------------------
# MAIN SERVICE
# -------------------------

def fetch_weekly_articles(
    topics: List[str],
    max_articles_per_topic: int = 50
) -> List[Dict]:
    """
    Fetches articles and stores them in MongoDB
    Grouped by week & month (safe for forecasting)
    """

    week_id = current_week_id()
    month_id = current_month_id()

    articles = []
    # TODO:how does the fetching switch between gnews and rss?
    articles += fetch_gnews_articles(topics)  
    articles += fetch_rss_articles()

    if max_articles_per_topic:
        articles = articles[:max_articles_per_topic]

    stored = []

    for art in articles:
        doc = {
            **art,
            "week_id": week_id,
            "month_id": month_id,
            "created_at": datetime.utcnow()
        }

        # prevent duplicate URLs
        if not articles_collection.find_one({"url": art["url"]}):
            articles_collection.insert_one(doc)
            stored.append(doc)

    print(f"✅ Stored {len(stored)} articles for {week_id}")
    return stored
