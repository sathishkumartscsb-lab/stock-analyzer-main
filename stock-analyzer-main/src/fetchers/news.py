import requests
import xml.etree.ElementTree as ET
import logging
from datetime import datetime
from src.config import MARKETAUX_API_TOKEN, NEWSAPI_KEY

logger = logging.getLogger(__name__)

class NewsFetcher:
    def __init__(self):
        self.sources = []
        # Create a session for NSE requests (helps with cookies)
        self.nse_session = requests.Session()
        self.nse_session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'application/json',
            'Accept-Language': 'en-US,en;q=0.9'
        })
        
        if MARKETAUX_API_TOKEN:
            self.sources.append(self.fetch_marketaux)
        if NEWSAPI_KEY:
            self.sources.append(self.fetch_newsapi)
        
        # Always include multiple free news sources
        self.sources.append(self.fetch_nse_news)
        self.sources.append(self.fetch_google_rss)
        # Add specialized data sources (priority sources)
        self.sources.append(self.fetch_screener_shareholding)
        self.sources.append(self.fetch_nse_corporate_filings)
        self.sources.append(self.fetch_moneycontrol_bulk_deals)
        self.sources.append(self.fetch_trendlyne_fii_dii)
        self.sources.append(self.fetch_stockedge_news)
        # Keep other sources but they may fail silently
        self.sources.append(self.fetch_moneycontrol)
        self.sources.append(self.fetch_economic_times)
        self.sources.append(self.fetch_yahoo_finance)
        self.sources.append(self.fetch_business_standard)
        self.sources.append(self.fetch_screener_announcements)

    def fetch_latest_news(self, symbol):
        """
        Aggregates news from available sources.
        """
        all_news = []
        seen_titles = set()
        
        logger.info(f"Fetching news for {symbol} from {len(self.sources)} sources")
        
        for fetch_method in self.sources:
            try:
                items = fetch_method(symbol)
                logger.info(f"Source {fetch_method.__name__} returned {len(items)} items for {symbol}")
                if len(items) == 0:
                    logger.debug(f"Source {fetch_method.__name__} returned no items for {symbol}")
                for item in items:
                    # Deduplicate by title (case-insensitive)
                    title_lower = item.get('title', '').lower()
                    if title_lower and title_lower not in seen_titles:
                        all_news.append(item)
                        seen_titles.add(title_lower)
                    elif title_lower in seen_titles:
                        logger.debug(f"Duplicate news item skipped: {title_lower[:50]}")
            except Exception as e:
                logger.error(f"Error in news source {fetch_method.__name__} for {symbol}: {e}", exc_info=True)
                
        # Sentiment Analysis (Simple Keyword Match)
        for item in all_news:
            if 'sentiment' not in item:
                item['sentiment'] = self._analyze_sentiment(item.get('title', ''))
            if 'category' not in item:
                item['category'] = 'General'
            
        # If we have very few items, try to get more from Google News with additional queries
        if len(all_news) < 10:
            logger.info(f"Low news count ({len(all_news)}), fetching additional Google News items...")
            additional_queries = [
                f"{symbol}+India+market",
                f"{symbol}+share+price+update",
                f"{symbol}+stock+analysis",
                f"{symbol}+financial+results"
            ]
            for query in additional_queries:
                try:
                    url = f"https://news.google.com/rss/search?q={query}&hl=en-IN&gl=IN&ceid=IN:en"
                    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
                    response = requests.get(url, headers=headers, timeout=10)
                    if response.status_code == 200:
                        root = ET.fromstring(response.content)
                        for item in root.findall('./channel/item')[:3]:
                            title_elem = item.find('title')
                            if title_elem is not None and title_elem.text:
                                title = title_elem.text
                                if " - " in title:
                                    title = title.split(" - ")[0]
                                title_lower = title.lower()
                                if title_lower and title_lower not in seen_titles:
                                    all_news.append({
                                        'source': 'Google News',
                                        'title': title,
                                        'link': item.find('link').text if item.find('link') is not None else '',
                                        'pubDate': item.find('pubDate').text if item.find('pubDate') is not None else datetime.now().strftime('%a, %d %b %Y %H:%M:%S GMT'),
                                        'category': 'General'
                                    })
                                    seen_titles.add(title_lower)
                except:
                    continue
        
        logger.info(f"Total unique news items for {symbol}: {len(all_news)}")
        return all_news[:15] # Return top 15

    def fetch_nse_news(self, symbol):
        """
        Fetch corporate announcements and news from NSE India
        """
        items = []
        try:
            # Try to fetch corporate actions first
            corporate_actions = self.fetch_corporate_actions(symbol)
            items.extend(corporate_actions)
        except Exception as e:
            logger.warning(f"NSE corporate actions fetch error for {symbol}: {e}")
        
        try:
            # First visit the main page to get cookies
            main_url = f"https://www.nseindia.com/get-quotes/equity?symbol={symbol}"
            self.nse_session.get(main_url, timeout=10)
            
            # Now fetch the API
            url = f"https://www.nseindia.com/api/quote-equity?symbol={symbol}"
            self.nse_session.headers.update({
                'Referer': main_url
            })
            response = self.nse_session.get(url, timeout=15)
            
            if response.status_code != 200:
                logger.warning(f"NSE API returned {response.status_code} for {symbol}")
                return items[:5]  # Return corporate actions if available
            
            data = response.json()
            
            # Extract corporate actions and info
            info = data.get('info', {})
            metadata = data.get('metadata', {})
            
            # Create news items from corporate actions
            if info.get('purpose'):
                items.append({
                    'source': 'NSE India',
                    'title': f"{symbol}: {info.get('purpose', 'Corporate Action')}",
                    'link': main_url,
                    'pubDate': datetime.now().strftime('%a, %d %b %Y %H:%M:%S GMT'),
                    'category': 'Corporate Action'
                })
            
            # Add listing date info if recent
            if metadata.get('listingDate'):
                items.append({
                    'source': 'NSE India',
                    'title': f"{symbol}: Listed on NSE - {metadata.get('listingDate')}",
                    'link': main_url,
                    'pubDate': datetime.now().strftime('%a, %d %b %Y %H:%M:%S GMT'),
                    'category': 'General'
                })
            
            return items[:5]  # Return max 5 items from NSE
        except Exception as e:
            logger.error(f"NSE news fetch error for {symbol}: {e}")
            return items[:5]  # Return what we have (corporate actions)
    
    def fetch_google_rss(self, symbol):
        """Fetch news from Google News RSS with multiple search queries"""
        items = []
        search_queries = [
            f"{symbol}+stock+NSE+India",
            f"{symbol}+share+price+India",
            f"{symbol}+company+news",
            f"{symbol}+results+earnings"
        ]
        
        for query in search_queries:
            try:
                url = f"https://news.google.com/rss/search?q={query}&hl=en-IN&gl=IN&ceid=IN:en"
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                }
                response = requests.get(url, headers=headers, timeout=15)
                if response.status_code != 200: 
                    continue
                
                root = ET.fromstring(response.content)
                for item in root.findall('./channel/item')[:5]:  # Get 5 from each query
                    title_elem = item.find('title')
                    link_elem = item.find('link')
                    pubdate_elem = item.find('pubDate')
                    
                    if title_elem is not None and title_elem.text:
                        # Remove " - " and source name from title if present
                        title = title_elem.text
                        if " - " in title:
                            title = title.split(" - ")[0]
                        
                        items.append({
                            'source': 'Google News',
                            'title': title,
                            'link': link_elem.text if link_elem is not None else '',
                            'pubDate': pubdate_elem.text if pubdate_elem is not None else datetime.now().strftime('%a, %d %b %Y %H:%M:%S GMT'),
                            'category': 'General'
                        })
            except Exception as e:
                logger.warning(f"Google RSS query error for {query}: {e}")
                continue
        
        logger.info(f"Fetched {len(items)} items from Google RSS for {symbol}")
        return items[:10]  # Return top 10 from all queries

    def fetch_marketaux(self, symbol):
        # Free Tier: 3 requests/day limit usually, handle with care or check quota
        url = f"https://api.marketaux.com/v1/news/all?symbols={symbol}.NS&filter_entities=true&language=en&api_token={MARKETAUX_API_TOKEN}"
        try:
            resp = requests.get(url, timeout=10)
            if resp.status_code != 200: return []
            
            data = resp.json()
            items = []
            for article in data.get('data', [])[:3]:
                items.append({
                    'source': 'MarketAux',
                    'title': article.get('title'),
                    'link': article.get('url'),
                    'pubDate': article.get('published_at')
                })
            return items
        except: return []

    def fetch_newsapi(self, symbol):
        url = f"https://newsapi.org/v2/everything?q={symbol}+India+Stock&sortBy=publishedAt&apiKey={NEWSAPI_KEY}"
        try:
            resp = requests.get(url, timeout=10)
            if resp.status_code != 200: return []
            
            data = resp.json()
            items = []
            for article in data.get('articles', [])[:3]:
                items.append({
                    'source': 'NewsAPI',
                    'title': article.get('title'),
                    'link': article.get('url'),
                    'pubDate': article.get('publishedAt')
                })
            return items
        except: return []
    
    def fetch_corporate_actions(self, symbol):
        """
        Fetch corporate actions from NSE (dividends, splits, buybacks)
        """
        try:
            # First visit main page for cookies
            main_url = f"https://www.nseindia.com/get-quotes/equity?symbol={symbol}"
            self.nse_session.get(main_url, timeout=10)
            
            url = f"https://www.nseindia.com/api/corporates-corporateActions?index=equities&symbol={symbol}"
            self.nse_session.headers.update({
                'Referer': main_url
            })
            response = self.nse_session.get(url, timeout=15)
            
            if response.status_code != 200:
                logger.warning(f"NSE Corporate Actions API returned {response.status_code} for {symbol}")
                return []
            
            data = response.json()
            items = []
            # Get latest 5 actions instead of 3
            if isinstance(data, list):
                for action in data[:5]:
                    purpose = action.get('subject', action.get('purpose', ''))
                    ex_date = action.get('exDate', '')
                    if purpose:  # Only add if there's actual content
                        items.append({
                            'category': 'Corporate Action',
                            'source': 'NSE India',
                            'title': f"{symbol}: {purpose}",
                            'detail': f"Ex-Date: {ex_date}" if ex_date else '',
                            'link': main_url,
                            'pubDate': datetime.now().strftime('%a, %d %b %Y %H:%M:%S GMT')
                        })
            return items
        except Exception as e:
            logger.error(f"Corporate actions fetch error for {symbol}: {e}")
            return []
    
    def categorize_news(self, news_items):
        """
        Categorize news into specific types based on keywords
        """
        categories = {
            'Corporate Action': ['dividend', 'buyback', 'split', 'bonus', 'merger', 'acquisition', 'corporate action'],
            'Results': ['Q1', 'Q2', 'Q3', 'Q4', 'quarterly', 'results', 'earnings', 'profit', 'revenue', 'financial results', 'annual results'],
            'Analyst': ['buy', 'sell', 'rating', 'target price', 'recommendation', 'upgrade', 'downgrade', 'analyst', 'brokerage', 'maintains'],
            'Orders/Contracts': ['order', 'contract', 'deal', 'partnership', 'agreement', 'wins', 'bags', 'awarded', 'tender'],
            'Management': ['CEO', 'CFO', 'Board', 'Director', 'resignation', 'appointed', 'management', 'executive', 'leadership'],
            'Regulatory': ['SEBI', 'regulatory', 'compliance', 'approval', 'license', 'permit', 'clearance', 'investigation'],
            'IPO/Listing': ['IPO', 'listing', 'public offer', 'issue', 'subscription']
        }
        
        categorized = []
        for item in news_items:
            title_lower = item.get('title', '').lower()
            item['category'] = item.get('category', 'General')  # Keep existing category if set
            
            # Only recategorize if it's General
            if item['category'] == 'General':
                for category, keywords in categories.items():
                    if any(keyword.lower() in title_lower for keyword in keywords):
                        item['category'] = category
                        break
            
            categorized.append(item)
        
        return categorized
    
    def fetch_comprehensive_news(self, symbol):
        """
        Fetch and categorize all news types
        """
        all_news = []
        seen_titles = set()
        
        # 1. Corporate Actions (highest priority)
        corporate_actions = self.fetch_corporate_actions(symbol)
        for item in corporate_actions:
            title_lower = item.get('title', '').lower()
            if title_lower and title_lower not in seen_titles:
                all_news.append(item)
                seen_titles.add(title_lower)
        
        # 2. Regular news sources (categorized)
        regular_news = self.fetch_latest_news(symbol)
        categorized_news = self.categorize_news(regular_news)
        for item in categorized_news:
            title_lower = item.get('title', '').lower()
            if title_lower and title_lower not in seen_titles:
                all_news.append(item)
                seen_titles.add(title_lower)
        
        # Sort by priority: Corporate Action > Analyst > Orders > Management > Results > General
        priority_order = {
            'Corporate Action': 1,
            'Analyst': 2,
            'Orders/Contracts': 3,
            'Management': 4,
            'Results': 5,
            'General': 6
        }
        
        all_news.sort(key=lambda x: priority_order.get(x.get('category', 'General'), 6))
        
        logger.info(f"Comprehensive news fetch for {symbol}: {len(all_news)} items from {len(set(item.get('source', 'Unknown') for item in all_news))} sources (returning top 15)")
        return all_news[:15]  # Return top 15 categorized news items
    
    def fetch_moneycontrol(self, symbol):
        """Fetch news from Moneycontrol"""
        items = []
        try:
            # Try multiple URL patterns
            urls_to_try = [
                f"https://www.moneycontrol.com/rss/{symbol.lower()}.xml",
                f"https://www.moneycontrol.com/rss/latestnews.xml",
                f"https://www.moneycontrol.com/rss/business.xml"
            ]
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            for url in urls_to_try:
                try:
                    response = requests.get(url, headers=headers, timeout=10)
                    if response.status_code == 200:
                        root = ET.fromstring(response.content)
                        for item in root.findall('./channel/item')[:10]:
                            title_elem = item.find('title')
                            link_elem = item.find('link')
                            pubdate_elem = item.find('pubDate')
                            
                            if title_elem is not None and title_elem.text:
                                title = title_elem.text
                                # Filter for symbol if not specific feed
                                if symbol.upper() in title.upper() or 'rss' in url.lower():
                                    items.append({
                                        'source': 'Moneycontrol',
                                        'title': title,
                                        'link': link_elem.text if link_elem is not None else '',
                                        'pubDate': pubdate_elem.text if pubdate_elem is not None else datetime.now().strftime('%a, %d %b %Y %H:%M:%S GMT'),
                                        'category': 'General'
                                    })
                        if len(items) > 0:
                            break
                except:
                    continue
        except Exception as e:
            logger.warning(f"Moneycontrol RSS fetch error for {symbol}: {e}")
        
        # Also try web scraping if RSS fails
        if len(items) == 0:
            try:
                url = f"https://www.moneycontrol.com/company-article/{symbol.lower()}/news"
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                }
                response = requests.get(url, headers=headers, timeout=15)
                if response.status_code == 200:
                    from bs4 import BeautifulSoup
                    soup = BeautifulSoup(response.content, 'html.parser')
                    # Try multiple selectors
                    news_items = (soup.find_all('div', class_='news_list') or 
                                soup.find_all('div', class_='news-item') or
                                soup.find_all('article') or
                                soup.find_all('h2') or
                                soup.find_all('h3'))[:8]
                    for news_item in news_items:
                        title_elem = news_item.find('h2') or news_item.find('h3') or news_item.find('a') or news_item
                        if title_elem:
                            title = title_elem.get_text(strip=True) if hasattr(title_elem, 'get_text') else str(title_elem).strip()
                            if title and len(title) > 10 and symbol.upper() in title.upper():
                                items.append({
                                    'source': 'Moneycontrol',
                                    'title': title[:150],
                                    'link': title_elem.get('href', '') if hasattr(title_elem, 'get') else '',
                                    'pubDate': datetime.now().strftime('%a, %d %b %Y %H:%M:%S GMT'),
                                    'category': 'General'
                                })
            except Exception as e:
                logger.warning(f"Moneycontrol web scrape error for {symbol}: {e}")
        
        logger.info(f"Fetched {len(items)} items from Moneycontrol for {symbol}")
        return items[:8]
    
    def fetch_economic_times(self, symbol):
        """Fetch news from Economic Times"""
        items = []
        try:
            # Try different Economic Times RSS feeds
            urls_to_try = [
                f"https://economictimes.indiatimes.com/markets/stocks/rssfeeds/2146842.cms",
                f"https://economictimes.indiatimes.com/markets/rssfeeds/1977021501.cms",
                f"https://economictimes.indiatimes.com/industry/rssfeeds/13352306.cms"
            ]
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            for url in urls_to_try:
                try:
                    response = requests.get(url, headers=headers, timeout=10)
                    if response.status_code == 200:
                        # Try to parse, handle XML errors
                        try:
                            root = ET.fromstring(response.content)
                            for item in root.findall('./channel/item')[:10]:
                                title_elem = item.find('title')
                                link_elem = item.find('link')
                                pubdate_elem = item.find('pubDate')
                                
                                if title_elem is not None and title_elem.text:
                                    title = title_elem.text
                                    # Filter for symbol
                                    if symbol.upper() in title.upper():
                                        items.append({
                                            'source': 'Economic Times',
                                            'title': title,
                                            'link': link_elem.text if link_elem is not None else '',
                                            'pubDate': pubdate_elem.text if pubdate_elem is not None else datetime.now().strftime('%a, %d %b %Y %H:%M:%S GMT'),
                                            'category': 'General'
                                        })
                        except ET.ParseError as pe:
                            logger.debug(f"XML parse error for ET feed: {pe}")
                            continue
                        if len(items) >= 5:
                            break
                except:
                    continue
        except Exception as e:
            logger.warning(f"Economic Times fetch error for {symbol}: {e}")
        
        logger.info(f"Fetched {len(items)} items from Economic Times for {symbol}")
        return items[:8]
    
    def fetch_yahoo_finance(self, symbol):
        """Fetch news from Yahoo Finance"""
        items = []
        try:
            # Try multiple Yahoo Finance RSS feeds
            urls_to_try = [
                f"https://feeds.finance.yahoo.com/rss/2.0/headline?s={symbol}.NS&region=IN&lang=en-IN",
                f"https://feeds.finance.yahoo.com/rss/2.0/headline?s={symbol}.BO&region=IN&lang=en-IN",
                f"https://in.finance.yahoo.com/quote/{symbol}.NS/news"
            ]
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            for url in urls_to_try:
                try:
                    if 'rss' in url:
                        response = requests.get(url, headers=headers, timeout=10)
                        if response.status_code == 200:
                            root = ET.fromstring(response.content)
                            for item in root.findall('./channel/item')[:8]:
                                title_elem = item.find('title')
                                link_elem = item.find('link')
                                pubdate_elem = item.find('pubDate')
                                
                                if title_elem is not None and title_elem.text:
                                    items.append({
                                        'source': 'Yahoo Finance',
                                        'title': title_elem.text,
                                        'link': link_elem.text if link_elem is not None else '',
                                        'pubDate': pubdate_elem.text if pubdate_elem is not None else datetime.now().strftime('%a, %d %b %Y %H:%M:%S GMT'),
                                        'category': 'General'
                                    })
                            if len(items) > 0:
                                break
                    else:
                        # Try web scraping for news page
                        response = requests.get(url, headers=headers, timeout=10)
                        if response.status_code == 200:
                            from bs4 import BeautifulSoup
                            soup = BeautifulSoup(response.content, 'html.parser')
                            news_items = soup.find_all(['h3', 'h2', 'div'], class_=['news', 'article'])[:5]
                            for news_item in news_items:
                                title = news_item.get_text(strip=True)
                                if title and symbol.upper() in title.upper():
                                    items.append({
                                        'source': 'Yahoo Finance',
                                        'title': title[:150],
                                        'link': url,
                                        'pubDate': datetime.now().strftime('%a, %d %b %Y %H:%M:%S GMT'),
                                        'category': 'General'
                                    })
                except:
                    continue
        except Exception as e:
            logger.warning(f"Yahoo Finance fetch error for {symbol}: {e}")
        
        logger.info(f"Fetched {len(items)} items from Yahoo Finance for {symbol}")
        return items[:8]
    
    def fetch_business_standard(self, symbol):
        """Fetch news from Business Standard"""
        items = []
        try:
            # Business Standard RSS
            url = f"https://www.business-standard.com/rss/markets-106.rss"
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            response = requests.get(url, headers=headers, timeout=15)
            if response.status_code == 200:
                root = ET.fromstring(response.content)
                for item in root.findall('./channel/item')[:10]:
                    title_elem = item.find('title')
                    link_elem = item.find('link')
                    pubdate_elem = item.find('pubDate')
                    
                    if title_elem is not None and title_elem.text:
                        title = title_elem.text
                        # Filter for relevant news about the symbol
                        if symbol.upper() in title.upper() or symbol.lower() in title.lower():
                            items.append({
                                'source': 'Business Standard',
                                'title': title,
                                'link': link_elem.text if link_elem is not None else '',
                                'pubDate': pubdate_elem.text if pubdate_elem is not None else datetime.now().strftime('%a, %d %b %Y %H:%M:%S GMT'),
                                'category': 'General'
                            })
        except Exception as e:
            logger.warning(f"Business Standard fetch error for {symbol}: {e}")
        
        logger.info(f"Fetched {len(items)} items from Business Standard for {symbol}")
        return items[:5]
    
    def fetch_screener_announcements(self, symbol):
        """Fetch announcements from Screener.in"""
        items = []
        try:
            from bs4 import BeautifulSoup
            url = f"https://www.screener.in/company/{symbol}/announcements/"
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            response = requests.get(url, headers=headers, timeout=15)
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')
                # Find announcement sections
                announcements = soup.find_all('div', class_='announcement')[:8]
                for ann in announcements:
                    title_elem = ann.find('h3') or ann.find('a') or ann.find('div', class_='title')
                    if title_elem:
                        title = title_elem.get_text(strip=True)
                        if title:
                            items.append({
                                'source': 'Screener.in',
                                'title': title,
                                'link': url,
                                'pubDate': datetime.now().strftime('%a, %d %b %Y %H:%M:%S GMT'),
                                'category': 'General'
                            })
        except Exception as e:
            logger.warning(f"Screener.in fetch error for {symbol}: {e}")
        
        logger.info(f"Fetched {len(items)} items from Screener.in for {symbol}")
        return items[:5]
    
    def fetch_screener_shareholding(self, symbol):
        """Fetch Promoter Pledging from Screener.in Shareholding section"""
        items = []
        try:
            from bs4 import BeautifulSoup
            url = f"https://www.screener.in/company/{symbol}/"
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            response = requests.get(url, headers=headers, timeout=15)
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Look for shareholding section
                shareholding_section = soup.find('section', id='shareholding')
                if not shareholding_section:
                    shareholding_section = soup.find('div', class_='shareholding') or soup.find('div', id='shareholding')
                
                if shareholding_section:
                    # Look for promoter pledging data
                    tables = shareholding_section.find_all('table')
                    for table in tables:
                        rows = table.find_all('tr')
                        for row in rows:
                            cells = row.find_all(['td', 'th'])
                            if len(cells) >= 2:
                                text = ' '.join([cell.get_text(strip=True) for cell in cells])
                                if 'pledge' in text.lower() or 'promoter' in text.lower():
                                    pledge_val = text
                                    if 'pledge' in text.lower():
                                        items.append({
                                            'source': 'Screener.in',
                                            'title': f"{symbol}: Promoter Pledging - {pledge_val[:80]}",
                                            'link': url + '#shareholding',
                                            'pubDate': datetime.now().strftime('%a, %d %b %Y %H:%M:%S GMT'),
                                            'category': 'Regulatory'
                                        })
                                        break
                
                # Also check for FII/DII data
                fii_dii_section = soup.find('div', class_='fii-dii') or soup.find('section', class_='fii-dii')
                if fii_dii_section:
                    fii_text = fii_dii_section.get_text(strip=True)
                    if 'FII' in fii_text or 'DII' in fii_text:
                        items.append({
                            'source': 'Screener.in',
                            'title': f"{symbol}: FII/DII Activity Update",
                            'link': url + '#shareholding',
                            'pubDate': datetime.now().strftime('%a, %d %b %Y %H:%M:%S GMT'),
                            'category': 'General'
                        })
        except Exception as e:
            logger.warning(f"Screener.in shareholding fetch error for {symbol}: {e}")
        
        logger.info(f"Fetched {len(items)} items from Screener.in shareholding for {symbol}")
        return items[:3]
    
    def fetch_nse_corporate_filings(self, symbol):
        """Fetch Quarterly Results from NSE Corporate Filings"""
        items = []
        try:
            # First visit main page for cookies
            main_url = f"https://www.nseindia.com/get-quotes/equity?symbol={symbol}"
            self.nse_session.get(main_url, timeout=10)
            
            # Try corporate filings API
            url = f"https://www.nseindia.com/api/corporate-announcements?index=equities&symbol={symbol}"
            self.nse_session.headers.update({
                'Referer': main_url
            })
            response = self.nse_session.get(url, timeout=15)
            
            if response.status_code == 200:
                data = response.json()
                # Look for quarterly results
                if isinstance(data, list):
                    for filing in data[:10]:
                        subject = filing.get('subject', '')
                        purpose = filing.get('purpose', '')
                        title_text = subject or purpose
                        
                        if title_text and ('result' in title_text.lower() or 'quarterly' in title_text.lower() or 
                                         'Q1' in title_text or 'Q2' in title_text or 'Q3' in title_text or 'Q4' in title_text):
                            items.append({
                                'source': 'NSE Corporate Filings',
                                'title': f"{symbol}: {title_text[:100]}",
                                'link': main_url,
                                'pubDate': filing.get('date', datetime.now().strftime('%a, %d %b %Y %H:%M:%S GMT')),
                                'category': 'Results'
                            })
                elif isinstance(data, dict):
                    filings = data.get('data', []) or data.get('announcements', [])
                    for filing in filings[:10]:
                        subject = filing.get('subject', filing.get('title', ''))
                        if subject and ('result' in subject.lower() or 'quarterly' in subject.lower()):
                            items.append({
                                'source': 'NSE Corporate Filings',
                                'title': f"{symbol}: {subject[:100]}",
                                'link': main_url,
                                'pubDate': filing.get('date', datetime.now().strftime('%a, %d %b %Y %H:%M:%S GMT')),
                                'category': 'Results'
                            })
        except Exception as e:
            logger.warning(f"NSE Corporate Filings fetch error for {symbol}: {e}")
        
        logger.info(f"Fetched {len(items)} items from NSE Corporate Filings for {symbol}")
        return items[:5]
    
    def fetch_moneycontrol_bulk_deals(self, symbol):
        """Fetch Bulk/Block Deals from Moneycontrol"""
        items = []
        try:
            from bs4 import BeautifulSoup
            # Try bulk deals page
            url = f"https://www.moneycontrol.com/stocks/marketstats/bulk-deals/index.php"
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            response = requests.get(url, headers=headers, timeout=15)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')
                # Look for the symbol in bulk deals table
                tables = soup.find_all('table')
                for table in tables:
                    rows = table.find_all('tr')
                    for row in rows:
                        cells = row.find_all(['td', 'th'])
                        row_text = ' '.join([cell.get_text(strip=True) for cell in cells])
                        if symbol.upper() in row_text.upper():
                            # Found bulk deal for this symbol
                            deal_info = row_text[:150]
                            items.append({
                                'source': 'Moneycontrol',
                                'title': f"{symbol}: Bulk/Block Deal - {deal_info}",
                                'link': url,
                                'pubDate': datetime.now().strftime('%a, %d %b %Y %H:%M:%S GMT'),
                                'category': 'Orders/Contracts'
                            })
                            break
                
                # Also try API if available
                api_url = f"https://www.moneycontrol.com/mcapi/bulk-deals/get-list?symbol={symbol}"
                api_response = requests.get(api_url, headers=headers, timeout=10)
                if api_response.status_code == 200:
                    api_data = api_response.json()
                    if isinstance(api_data, dict) and 'data' in api_data:
                        for deal in api_data['data'][:5]:
                            items.append({
                                'source': 'Moneycontrol',
                                'title': f"{symbol}: Bulk Deal - {deal.get('buyer', '')} / {deal.get('seller', '')}",
                                'link': url,
                                'pubDate': deal.get('date', datetime.now().strftime('%a, %d %b %Y %H:%M:%S GMT')),
                                'category': 'Orders/Contracts'
                            })
        except Exception as e:
            logger.warning(f"Moneycontrol bulk deals fetch error for {symbol}: {e}")
        
        logger.info(f"Fetched {len(items)} items from Moneycontrol bulk deals for {symbol}")
        return items[:5]
    
    def fetch_trendlyne_fii_dii(self, symbol):
        """Fetch FII/DII Change from Trendlyne"""
        items = []
        try:
            from bs4 import BeautifulSoup
            # Trendlyne shareholding page
            url = f"https://trendlyne.com/equity/{symbol}/shareholding/"
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            response = requests.get(url, headers=headers, timeout=15)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Look for FII/DII section
                fii_dii_section = soup.find('div', class_='fii-dii') or soup.find('section', class_='shareholding')
                if not fii_dii_section:
                    # Try to find any section with FII or DII text
                    all_sections = soup.find_all(['div', 'section'])
                    for section in all_sections:
                        text = section.get_text()
                        if 'FII' in text or 'DII' in text or 'Foreign' in text:
                            fii_dii_section = section
                            break
                
                if fii_dii_section:
                    fii_text = fii_dii_section.get_text(strip=True)
                    # Extract FII/DII change information
                    if 'FII' in fii_text or 'DII' in fii_text:
                        # Try to find tables with FII/DII data
                        tables = fii_dii_section.find_all('table')
                        for table in tables:
                            rows = table.find_all('tr')
                            for row in rows:
                                row_text = row.get_text(strip=True)
                                if symbol.upper() in row_text.upper() and ('FII' in row_text or 'DII' in row_text):
                                    items.append({
                                        'source': 'Trendlyne',
                                        'title': f"{symbol}: FII/DII Activity - {row_text[:100]}",
                                        'link': url,
                                        'pubDate': datetime.now().strftime('%a, %d %b %Y %H:%M:%S GMT'),
                                        'category': 'General'
                                    })
                                    break
                    
                    # If no specific data found, add general update
                    if len(items) == 0 and ('FII' in fii_text or 'DII' in fii_text):
                        items.append({
                            'source': 'Trendlyne',
                            'title': f"{symbol}: FII/DII Shareholding Update Available",
                            'link': url,
                            'pubDate': datetime.now().strftime('%a, %d %b %Y %H:%M:%S GMT'),
                            'category': 'General'
                        })
        except Exception as e:
            logger.warning(f"Trendlyne FII/DII fetch error for {symbol}: {e}")
        
        logger.info(f"Fetched {len(items)} items from Trendlyne for {symbol}")
        return items[:3]
    
    def fetch_stockedge_news(self, symbol):
        """Fetch New Buy Orders/News from StockEdge"""
        items = []
        try:
            from bs4 import BeautifulSoup
            # StockEdge might have different URL structure, try common patterns
            urls_to_try = [
                f"https://www.stockedge.com/share/{symbol}",
                f"https://stockedge.com/stock/{symbol}",
                f"https://www.stockedge.com/stock/{symbol}/news"
            ]
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            for url in urls_to_try:
                try:
                    response = requests.get(url, headers=headers, timeout=10)
                    if response.status_code == 200:
                        soup = BeautifulSoup(response.content, 'html.parser')
                        
                        # Look for news section
                        news_section = soup.find('div', class_='news') or soup.find('section', class_='news')
                        if not news_section:
                            news_section = soup.find('div', id='news')
                        
                        if news_section:
                            news_items = news_section.find_all(['div', 'article', 'li'], class_=['news-item', 'article', 'news'])
                            for news_item in news_items[:5]:
                                title_elem = news_item.find('h3') or news_item.find('h2') or news_item.find('a')
                                if title_elem:
                                    title = title_elem.get_text(strip=True)
                                    if title and symbol.upper() in title.upper():
                                        items.append({
                                            'source': 'StockEdge',
                                            'title': f"{symbol}: {title[:100]}",
                                            'link': url,
                                            'pubDate': datetime.now().strftime('%a, %d %b %Y %H:%M:%S GMT'),
                                            'category': 'General'
                                        })
                        
                        # Look for daily scans or buy orders
                        scans_section = soup.find('div', class_='scans') or soup.find('div', id='scans')
                        if scans_section:
                            scan_items = scans_section.find_all(['div', 'li'])
                            for scan_item in scan_items[:3]:
                                scan_text = scan_item.get_text(strip=True)
                                if symbol.upper() in scan_text.upper() and ('buy' in scan_text.lower() or 'order' in scan_text.lower()):
                                    items.append({
                                        'source': 'StockEdge',
                                        'title': f"{symbol}: {scan_text[:100]}",
                                        'link': url,
                                        'pubDate': datetime.now().strftime('%a, %d %b %Y %H:%M:%S GMT'),
                                        'category': 'Orders/Contracts'
                                    })
                        
                        if len(items) > 0:
                            break  # Found data, no need to try other URLs
                except:
                    continue
        except Exception as e:
            logger.warning(f"StockEdge fetch error for {symbol}: {e}")
        
        logger.info(f"Fetched {len(items)} items from StockEdge for {symbol}")
        return items[:5]
    
    def _analyze_sentiment(self, text):
        text = text.lower()
        positive_words = ['gain', 'jump', 'surge', 'rise', 'profit', 'high', 'buy', 'upgrade', 
                         'growth', 'strong', 'beat', 'outperform', 'bullish', 'rally', 'soar',
                         'record', 'exceeds', 'positive', 'boost', 'increase', 'higher']
        negative_words = ['loss', 'fall', 'drop', 'decline', 'crash', 'sell', 'downgrade', 'weak',
                          'plunge', 'slump', 'concern', 'worry', 'risk', 'negative', 'lower',
                          'miss', 'disappoint', 'bearish', 'slide', 'tumble', 'decrease']
        
        pos_count = sum(1 for w in positive_words if w in text)
        neg_count = sum(1 for w in negative_words if w in text)
        
        if pos_count > neg_count:
            return 'Positive'
        elif neg_count > pos_count:
            return 'Negative'
        return 'Neutral'
