"""
Test script to verify all news sources are working
"""
import logging
from src.fetchers.news import NewsFetcher

# Setup logging to see what's happening
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

symbol = 'RELIANCE'  # Test with RELIANCE
print(f"\n{'='*80}")
print(f"Testing News Sources for {symbol}")
print(f"{'='*80}\n")

nf = NewsFetcher()

print(f"Total sources configured: {len(nf.sources)}")
print("Sources:")
for i, source in enumerate(nf.sources, 1):
    print(f"  {i}. {source.__name__}")

print(f"\n{'='*80}")
print("Fetching comprehensive news...")
print(f"{'='*80}\n")

news_data = nf.fetch_comprehensive_news(symbol)

print(f"\n{'='*80}")
print(f"RESULTS: Found {len(news_data)} total news items")
print(f"{'='*80}\n")

# Group by source
by_source = {}
for item in news_data:
    source = item.get('source', 'Unknown')
    if source not in by_source:
        by_source[source] = []
    by_source[source].append(item)

print("News by Source:")
for source, items in sorted(by_source.items()):
    print(f"\n  {source}: {len(items)} items")
    for item in items[:3]:  # Show first 3
        print(f"    - {item.get('title', 'No title')[:80]}")
        print(f"      Category: {item.get('category', 'N/A')}, Sentiment: {item.get('sentiment', 'N/A')}")

print(f"\n{'='*80}")
print("Summary:")
print(f"  Total Sources: {len(by_source)}")
print(f"  Total Items: {len(news_data)}")
print(f"{'='*80}\n")

