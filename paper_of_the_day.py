"""Paper of the Day: one research paper per day from arXiv, per topic.

Usage:
    python paper_of_the_day.py                 # today's paper for the default topic
    python paper_of_the_day.py --topic NAME    # today's paper for another topic in topics.json
    python paper_of_the_day.py --new           # skip today's pick and get a different one
    python paper_of_the_day.py --open          # also open the paper in your browser
    python paper_of_the_day.py --list-topics   # show the topics you can pick from
    python paper_of_the_day.py --history       # show papers you've been given before
    python paper_of_the_day.py --all --build-site   # every topic, then write site/index.html
"""

import argparse
import json
import random
import sys
import textwrap
import urllib.parse
import urllib.request
import webbrowser
import xml.etree.ElementTree as ET
from datetime import date
from pathlib import Path

from site_builder import build_site

APP_DIR = Path(__file__).resolve().parent
TOPICS_FILE = APP_DIR / "topics.json"
HISTORY_FILE = APP_DIR / "history.json"
SITE_DIR = APP_DIR / "site"

ARXIV_API = "https://export.arxiv.org/api/query"
ATOM = {"a": "http://www.w3.org/2005/Atom"}

# How far back into the newest papers we're willing to reach, and how many to fetch per request.
MAX_OFFSET = 1500
BATCH_SIZE = 50


def load_json(path, default):
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return default


def save_history(history):
    HISTORY_FILE.write_text(json.dumps(history, indent=2, ensure_ascii=False), encoding="utf-8")


def fetch_papers(categories, start):
    query = " OR ".join(f"cat:{c}" for c in categories)
    params = urllib.parse.urlencode({
        "search_query": query,
        "start": start,
        "max_results": BATCH_SIZE,
        "sortBy": "submittedDate",
        "sortOrder": "descending",
    })
    request = urllib.request.Request(
        f"{ARXIV_API}?{params}", headers={"User-Agent": "paper-of-the-day/1.0"}
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        root = ET.fromstring(response.read())

    papers = []
    for entry in root.findall("a:entry", ATOM):
        def text(tag):
            return " ".join((entry.findtext(tag, default="", namespaces=ATOM)).split())

        pdf = next(
            (link.get("href") for link in entry.findall("a:link", ATOM) if link.get("title") == "pdf"),
            None,
        )
        papers.append({
            "id": text("a:id").rsplit("/abs/", 1)[-1],
            "title": text("a:title"),
            "authors": [text_of(a) for a in entry.findall("a:author", ATOM)],
            "published": text("a:published")[:10],
            "summary": text("a:summary"),
            "url": text("a:id"),
            "pdf": pdf,
            "categories": [c.get("term") for c in entry.findall("a:category", ATOM)],
        })
    return papers


def text_of(author):
    return author.findtext("a:name", default="", namespaces=ATOM).strip()


def pick_paper(topic, seen_ids, rng):
    # Try a few random spots in the recent-paper list, then fall back to the very newest.
    offsets = [rng.randrange(0, MAX_OFFSET, BATCH_SIZE) for _ in range(3)] + [0]
    for offset in offsets:
        papers = [p for p in fetch_papers(topic["categories"], offset) if p["id"] not in seen_ids]
        if papers:
            return rng.choice(papers)
    return None


def print_paper(paper, topic_name, day):
    width = 88
    print("=" * width)
    print(f"  Paper of the Day  |  {topic_name}  |  {day}")
    print("=" * width)
    print()
    print(textwrap.fill(paper["title"], width))
    print()
    authors = paper["authors"]
    shown = ", ".join(authors[:6]) + (f" + {len(authors) - 6} more" if len(authors) > 6 else "")
    print(textwrap.fill(f"Authors:    {shown}", width, subsequent_indent=" " * 12))
    print(f"Published:  {paper['published']}")
    print(f"Categories: {', '.join(paper['categories'])}")
    print()
    print(textwrap.fill(paper["summary"], width))
    print()
    print(f"Read it:    {paper['url']}")
    if paper.get("pdf"):
        print(f"PDF:        {paper['pdf']}")
    print("=" * width)


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    parser = argparse.ArgumentParser(description="Get one research paper per day.")
    parser.add_argument("--topic", help="topic key from topics.json")
    parser.add_argument("--new", action="store_true", help="replace today's pick with a different paper")
    parser.add_argument("--open", action="store_true", help="open the paper in your browser")
    parser.add_argument("--list-topics", action="store_true", help="list available topics")
    parser.add_argument("--history", action="store_true", help="list previously suggested papers")
    parser.add_argument("--all", action="store_true", help="get today's paper for every topic")
    parser.add_argument("--build-site", action="store_true", help="write the web page to site/index.html")
    args = parser.parse_args()

    config = load_json(TOPICS_FILE, None)
    if config is None:
        sys.exit(f"Missing {TOPICS_FILE.name}")
    topics = config["topics"]

    if args.list_topics:
        for key, topic in topics.items():
            print(f"{key:28} {topic['name']} - {topic.get('description', '')}")
        return

    history = load_json(HISTORY_FILE, [])

    if args.history:
        for item in history:
            print(f"{item['date']}  [{item['topic']}]  {item['paper']['title']}")
            print(f"{'':12}  {item['paper']['url']}")
        return

    if args.all:
        topic_keys = list(topics)
    else:
        topic_keys = [args.topic or config["default_topic"]]
        if topic_keys[0] not in topics:
            sys.exit(f"Unknown topic '{topic_keys[0]}'. Run with --list-topics to see options.")
    today = date.today().isoformat()

    for topic_key in topic_keys:
        topic = topics[topic_key]
        paper = get_todays_paper(topic_key, topic, history, today, args.new)
        print_paper(paper, topic["name"], today)
        if args.open:
            webbrowser.open(paper["url"])

    if args.build_site:
        page = build_site(history, topics, SITE_DIR)
        print(f"Web page written to {page}")


def get_todays_paper(topic_key, topic, history, today, new):
    todays = next((h for h in history if h["date"] == today and h["topic"] == topic_key), None)
    if todays and new:
        history.remove(todays)
        todays = None
    if todays:
        return todays["paper"]

    seen_ids = {h["paper"]["id"] for h in history}
    # Seeded by date + topic so a rerun on the same day is stable even if history is lost.
    rng = random.Random(f"{today}:{topic_key}" + (f":{random.random()}" if new else ""))
    try:
        paper = pick_paper(topic, seen_ids, rng)
    except OSError as err:
        sys.exit(f"Couldn't reach arXiv: {err}")
    if paper is None:
        sys.exit(f"No new papers found for '{topic_key}'. Try again later.")
    history.append({"date": today, "topic": topic_key, "paper": paper})
    save_history(history)
    return paper


if __name__ == "__main__":
    main()
