"""
Test all news sources to see which ones are working
"""
import logging
from src.fetchers.news import NewsFetcher

# Setup detailed logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

symbol = 'RELIANCE'
print(f"\n{'='*80}")
print(f"Testing ALL News Sources for {symbol}")
print(f"{'='*80}\n")

nf = NewsFetcher()

# Test each source individually
for i, source_func in enumerate(nf.sources, 1):
    print(f"\n{i}. Testing {source_func.__name__}...")
    try:
        result = source_func(symbol)
        print(f"   [OK] Returned {len(result)} items")
        if len(result) > 0:
            for item in result[:2]:
                print(f"      - {item.get('source', 'Unknown')}: {item.get('title', 'No title')[:60]}")
        else:
            print(f"   [FAIL] No items returned")
    except Exception as e:
        print(f"   [ERROR] {e}")

print(f"\n{'='*80}")
print("Testing comprehensive fetch...")
print(f"{'='*80}\n")

news_data = nf.fetch_comprehensive_news(symbol)

# Group by source
by_source = {}
for item in news_data:
    source = item.get('source', 'Unknown')
    if source not in by_source:
        by_source[source] = []
    by_source[source].append(item)

print(f"\nRESULTS: Found {len(news_data)} total news items from {len(by_source)} sources")
print("\nNews by Source:")
for source, items in sorted(by_source.items()):
    print(f"  {source}: {len(items)} items")

