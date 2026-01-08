from src.fetchers.news import NewsFetcher

nf = NewsFetcher()
news = nf.fetch_comprehensive_news('RELIANCE')
sources = {}
for item in news:
    s = item.get('source', 'Unknown')
    sources[s] = sources.get(s, 0) + 1

print(f'Total items: {len(news)}')
print(f'Unique sources: {len(sources)}')
print('\nItems by source:')
for source, count in sorted(sources.items()):
    print(f'  {source}: {count}')

