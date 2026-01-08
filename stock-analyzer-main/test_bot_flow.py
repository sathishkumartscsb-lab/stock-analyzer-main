"""
Test the complete bot flow to see where it might be failing
"""
import logging
import sys
import os

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

symbol = 'RAILTEL'
print(f"\n{'='*80}")
print(f"Testing Complete Bot Flow for {symbol}")
print(f"{'='*80}\n")

try:
    # 1. Fetch Data
    print("Step 1: Fetching Fundamentals...")
    from src.fetchers.fundamentals import FundamentalFetcher
    ff = FundamentalFetcher()
    fund_data = ff.get_data(symbol)
    print(f"  [OK] Fundamentals: {len(fund_data) if fund_data else 0} items")
    
    print("\nStep 2: Fetching Technicals...")
    from src.fetchers.technicals import TechnicalFetcher
    tf = TechnicalFetcher()
    tech_data = tf.get_data(symbol)
    print(f"  [OK] Technicals: {tech_data.get('indicators_available', False) if tech_data else False}")
    
    print("\nStep 3: Fetching News...")
    from src.fetchers.news import NewsFetcher
    nf = NewsFetcher()
    news_data = nf.fetch_comprehensive_news(symbol)
    print(f"  [OK] News: {len(news_data)} items")
    
    if not fund_data and not tech_data:
        print("\n[ERROR] No data fetched!")
        sys.exit(1)
    
    # 2. Analyze
    print("\nStep 4: Running Analysis Engine...")
    from src.analysis.engine import AnalysisEngine
    engine = AnalysisEngine()
    result = engine.evaluate_stock(fund_data, tech_data, news_data)
    result['cmp'] = fund_data.get('Current Price') if fund_data else tech_data.get('Close', 0)
    result['news_items'] = news_data
    print(f"  [OK] Analysis complete. Score: {result.get('total_score', 0):.1f}/37")
    
    # 3. Generate Image
    print("\nStep 5: Generating Infographic...")
    from src.renderer.generator import InfographicGenerator
    gen = InfographicGenerator()
    output_path = f"{symbol}_test_report.png"
    gen.generate_report(symbol, result, output_path)
    
    if os.path.exists(output_path):
        file_size = os.path.getsize(output_path)
        print(f"  [OK] Image generated: {output_path} ({file_size} bytes)")
    else:
        print(f"  [ERROR] Image file not created!")
        sys.exit(1)
    
    print(f"\n{'='*80}")
    print("[SUCCESS] ALL STEPS COMPLETED SUCCESSFULLY!")
    print(f"{'='*80}\n")
    
except Exception as e:
    print(f"\n[ERROR] {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

