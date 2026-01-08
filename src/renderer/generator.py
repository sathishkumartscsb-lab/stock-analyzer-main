from PIL import Image, ImageDraw, ImageFont
import os
import logging
from datetime import datetime
import math

logger = logging.getLogger(__name__)

class InfographicGenerator:
    def __init__(self):
        self.width = 1400  # Wider for better layout
        self.height = 3800  # Increased height for more news
        self.bg_color = "#0F172A"
        self.text_color = "#FFFFFF"
        self.green = "#22C55E"
        self.yellow = "#FACC15"
        self.red = "#EF4444"
        self.blue = "#3B82F6"
        self.card_bg = "#1E293B"
        self.card_border = "#334155"
        self.accent_blue = "#60A5FA"
        
        # Load Fonts
        try:
            self.title_font = ImageFont.truetype("arial.ttf", 72)
            self.header_font = ImageFont.truetype("arial.ttf", 48)
            self.subheader_font = ImageFont.truetype("arial.ttf", 32)
            self.body_font = ImageFont.truetype("arial.ttf", 24)
            self.small_font = ImageFont.truetype("arial.ttf", 18)
            self.tiny_font = ImageFont.truetype("arial.ttf", 16)
        except:
            self.title_font = ImageFont.load_default()
            self.header_font = ImageFont.load_default()
            self.subheader_font = ImageFont.load_default()
            self.body_font = ImageFont.load_default()
            self.small_font = ImageFont.load_default()
            self.tiny_font = ImageFont.load_default()

    def draw_progress_bar(self, draw, x, y, width, height, percentage, color, bg_color="#334155"):
        """Draw a progress bar"""
        # Background
        draw.rounded_rectangle([x, y, x + width, y + height], radius=height//2, fill=bg_color)
        # Fill
        if percentage > 0:
            fill_width = int(width * min(percentage / 100, 1))
            draw.rounded_rectangle([x, y, x + fill_width, y + height], radius=height//2, fill=color)

    def draw_metric_card(self, draw, x, y, width, height, label, value, score, status="", icon=""):
        """Draw a compact metric card"""
        # Card background
        draw.rounded_rectangle([x, y, x + width, y + height], radius=8, fill=self.card_bg, outline=self.card_border, width=1)
        
        # Score color
        dot_color = self.green if score >= 1 else (self.yellow if score == 0.5 else self.red)
        
        # Icon/Status dot
        if icon:
            draw.text((x + 10, y + 8), icon, font=self.body_font, fill=dot_color)
        else:
            draw.ellipse([x + 8, y + 8, x + 20, y + 20], fill=dot_color)
        
        # Label
        draw.text((x + 30, y + 8), label, font=self.tiny_font, fill="#94A3B8")
        
        # Value
        value_str = str(value)
        if len(value_str) > 12:
            value_str = value_str[:9] + "..."
        draw.text((x + 10, y + 28), value_str, font=self.small_font, fill=self.text_color)
        
        # Progress bar
        progress_pct = score * 100
        self.draw_progress_bar(draw, x + 10, y + height - 12, width - 20, 6, progress_pct, dot_color)
        
        # Status text if provided
        if status:
            status_short = status[:15] + "..." if len(status) > 15 else status
            draw.text((x + 10, y + height - 25), status_short, font=self.tiny_font, fill="#64748B")

    def generate_report(self, stock_name, data, output_path):
        img = Image.new('RGB', (self.width, self.height), color=self.bg_color)
        draw = ImageDraw.Draw(img)
        
        # ========== 1. ENHANCED HEADER ==========
        header_y = 30
        
        # Gradient-like background for header
        draw.rectangle([0, 0, self.width, 200], fill="#1A2332")
        
        # Stock Name with icon
        draw.text((60, header_y), "📈", font=self.title_font, fill=self.yellow)
        draw.text((120, header_y), stock_name, font=self.title_font, fill=self.text_color)
        
        # CMP with better styling
        cmp = data.get('cmp', 0)
        draw.rounded_rectangle([60, header_y + 80, 400, header_y + 140], radius=12, 
                              fill=self.card_bg, outline=self.accent_blue, width=2)
        draw.text((80, header_y + 95), "Current Price", font=self.tiny_font, fill="#94A3B8")
        draw.text((80, header_y + 115), f"₹{cmp:.2f}", font=self.header_font, fill=self.accent_blue)
        
        # Score Badge (Enhanced)
        score = data.get('total_score', 0)
        risk_label = data.get('health_label', 'Unknown')
        score_color = self.green if score > 25 else (self.yellow if score > 15 else self.red)
        
        # Large score badge
        badge_x = 450
        badge_y = header_y + 30
        badge_w = 280
        badge_h = 150
        
        draw.rounded_rectangle([badge_x, badge_y, badge_x + badge_w, badge_y + badge_h], 
                              radius=20, fill=self.card_bg, outline=score_color, width=4)
        
        # Score circle/arc
        center_x = badge_x + badge_w // 2
        center_y = badge_y + 50
        radius = 45
        
        # Background circle
        draw.ellipse([center_x - radius, center_y - radius, center_x + radius, center_y + radius], 
                    fill="#0F172A", outline=score_color, width=3)
        
        # Score percentage arc
        score_pct = (score / 37) * 100
        for angle in range(0, int(360 * score_pct / 100), 5):
            rad = math.radians(angle - 90)
            x1 = center_x + (radius - 5) * math.cos(rad)
            y1 = center_y + (radius - 5) * math.sin(rad)
            x2 = center_x + radius * math.cos(rad)
            y2 = center_y + radius * math.sin(rad)
            draw.line([(x1, y1), (x2, y2)], fill=score_color, width=2)
        
        # Score text in center
        draw.text((center_x - 35, center_y - 20), f"{score:.1f}", font=self.header_font, fill=score_color)
        draw.text((center_x - 50, center_y + 15), "/37", font=self.body_font, fill="#94A3B8")
        draw.text((badge_x + 20, badge_y + 110), risk_label, font=self.body_font, fill=score_color)
        
        # Quick stats on right
        stats_x = 760
        draw.text((stats_x, header_y + 30), "📊 Quick Stats", font=self.subheader_font, fill=self.yellow)
        
        fund_score = data.get('fundamental_score', 0)
        tech_score = data.get('technical_score', 0)
        news_score = data.get('news_score', 0)
        
        # Mini progress bars for scores
        y_offset = header_y + 75
        for label, val, max_val, color in [("Fundamental", fund_score, 24, self.blue), 
                                           ("Technical", tech_score, 5, self.yellow),
                                           ("News", news_score, 8, self.green)]:
            draw.text((stats_x, y_offset), label, font=self.tiny_font, fill="#94A3B8")
            pct = (val / max_val) * 100 if max_val > 0 else 0
            self.draw_progress_bar(draw, stats_x + 100, y_offset + 3, 200, 8, pct, color)
            draw.text((stats_x + 310, y_offset), f"{val:.1f}", font=self.tiny_font, fill=color)
            y_offset += 25

        # ========== 2. COMPACT 3-COLUMN DATA GRID ==========
        y_start = 250
        details = data.get('details', {})
        
        # Section header
        draw.text((60, y_start), "📋 DETAILED ANALYSIS", font=self.subheader_font, fill=self.yellow)
        y_start += 50
        
        # Card dimensions
        card_w = 420
        card_h = 85
        card_spacing = 20
        col_spacing = 30
        
        # Organize keys into 3 columns
        all_fund_keys = [
            'Market Cap', 'CMP vs 52W', 'P/E Ratio', 'PEG Ratio', 'EPS Trend', 
            'EBITDA Trend', 'Debt / Equity', 'Dividend Yield', 'Intrinsic Value',
            'Current Ratio', 'Promoter Holding', 'FII/DII Trend', 'Operating Cash Flow',
            'ROCE', 'ROE', 'Revenue CAGR', 'Profit CAGR', 'Interest Coverage',
            'Free Cash Flow', 'Equity Dilution', 'Pledged Shares', 'Contingent Liab',
            'Piotroski Score', 'Working Cap Cycle', 'CFO / PAT', 'Book Value Analysis'
        ]
        
        tech_keys = ['Trend (DMA)', 'RSI', 'MACD', 'Pivot Support', 'Volume Trend']
        news_keys = ['Orders / Business', 'Dividend / Buyback', 'Results Performance',
                    'Regulatory / Credit', 'Sector vs Nifty', 'Peer Comparison', 
                    'Promoter Pledge', 'Management']
        
        all_keys = all_fund_keys + tech_keys + news_keys
        
        # Draw in 3 columns
        col1_x = 60
        col2_x = 60 + card_w + col_spacing
        col3_x = 60 + (card_w + col_spacing) * 2
        
        current_y = y_start
        col_heights = [0, 0, 0]
        
        for idx, key in enumerate(all_keys):
            if key not in details:
                continue
                
            val = details[key]
            col_idx = idx % 3
            col_x = [col1_x, col2_x, col3_x][col_idx]
            col_y = current_y + col_heights[col_idx]
            
            # Get icon based on category
            icon = ""
            if 'Trend' in key or 'RSI' in key or 'MACD' in key:
                icon = "📈"
            elif 'Debt' in key or 'Pledge' in key:
                icon = "⚠️"
            elif 'Cash' in key or 'Flow' in key:
                icon = "💰"
            elif 'Holding' in key or 'Promoter' in key:
                icon = "👥"
            elif 'Dividend' in key or 'Buyback' in key:
                icon = "💵"
            elif 'ROCE' in key or 'ROE' in key:
                icon = "📊"
            else:
                icon = "•"
            
            self.draw_metric_card(draw, col_x, col_y, card_w, card_h, key, val['value'], 
                                 val['score'], val.get('status', ''), icon)
            
            col_heights[col_idx] += card_h + card_spacing
        
        y_cards = y_start + max(col_heights) + 60

        # ========== 3. ENHANCED SUMMARY CARDS ==========
        draw.text((60, y_cards), "💡 KEY INSIGHTS", font=self.subheader_font, fill=self.yellow)
        y_cards += 50
        
        f_summary = data.get('fundamental_summary', 'No summary.')
        t_summary = data.get('technical_summary', 'No summary.')
        n_summary = data.get('news_summary', 'No summary.')
        
        def draw_enhanced_summary_box(title, text, icon, x, y, width, height):
            # Determine colors
            if "Bullish" in text or "🟢" in text:
                border_color = self.green
                icon_color = self.green
            elif "Bearish" in text or "🔴" in text:
                border_color = self.red
                icon_color = self.red
            else:
                border_color = self.yellow
                icon_color = self.yellow
            
            # Card with gradient effect
            draw.rounded_rectangle([x, y, x + width, y + height], radius=15, 
                                  fill=self.card_bg, outline=border_color, width=3)
            
            # Icon and title
            draw.text((x + 20, y + 15), icon, font=self.header_font, fill=icon_color)
            draw.text((x + 80, y + 20), title, font=self.body_font, fill=icon_color)
            
            # Text with wrapping
            import textwrap
            wrapped = textwrap.fill(text, width=40)
            draw.text((x + 20, y + 60), wrapped, font=self.small_font, fill="#E2E8F0")

        box_w = 420
        box_h = 180
        draw_enhanced_summary_box("Fundamental", f_summary, "📊", 60, y_cards, box_w, box_h)
        draw_enhanced_summary_box("Technical", t_summary, "📈", 500, y_cards, box_w, box_h)
        draw_enhanced_summary_box("News", n_summary, "📰", 940, y_cards, box_w, box_h)
        
        y_cards += box_h + 40

        # ========== 4. DECISION CARDS (Enhanced) ==========
        draw.text((60, y_cards), "🎯 TRADING DECISIONS", font=self.subheader_font, fill=self.yellow)
        y_cards += 50
        
        # Swing Card
        swing_verdict = data.get('swing_verdict', 'WAIT')
        s_color = self.green if "BUY" in swing_verdict else (self.red if "AVOID" in swing_verdict else self.yellow)
        
        swing_w = 650
        swing_h = 280  # Increased height for more content
        draw.rounded_rectangle([60, y_cards, 60 + swing_w, y_cards + swing_h], radius=20, 
                              fill=self.card_bg, outline=s_color, width=4)
        
        draw.text((90, y_cards + 20), "⚡ Swing Trading", font=self.body_font, fill="#94A3B8")
        draw.text((90, y_cards + 60), swing_verdict, font=self.header_font, fill=s_color)
        
        swing_action = data.get('swing_action', '')
        swing_reason = data.get('swing_reason', '')
        
        # Enhanced reason display with better formatting
        import textwrap
        if swing_reason:
            # Make reason more prominent
            draw.text((90, y_cards + 120), "📋 Reason:", font=self.small_font, fill=self.yellow)
            wrapped_reason = textwrap.fill(swing_reason, width=60)
            draw.text((90, y_cards + 145), wrapped_reason, font=self.small_font, fill="#E2E8F0")
        
        if swing_action:
            draw.text((90, y_cards + 200), "💡 Action:", font=self.small_font, fill=self.yellow)
            wrapped_action = textwrap.fill(swing_action, width=60)
            draw.text((90, y_cards + 225), wrapped_action, font=self.small_font, fill="#E2E8F0")
        
        # Long Term Card
        lt_verdict = data.get('long_term_verdict', 'AVOID')
        l_color = self.green if "BUY" in lt_verdict else (self.red if "AVOID" in lt_verdict else self.yellow)
        
        lt_w = 650
        lt_h = 280  # Increased height for more content
        draw.rounded_rectangle([730, y_cards, 730 + lt_w, y_cards + lt_h], radius=20, 
                              fill=self.card_bg, outline=l_color, width=4)
        
        draw.text((760, y_cards + 20), "📅 Long-Term Investment", font=self.body_font, fill="#94A3B8")
        draw.text((760, y_cards + 60), lt_verdict, font=self.header_font, fill=l_color)
        
        lt_reason = data.get('long_term_reason', '')
        import textwrap
        
        # Enhanced reason display
        if lt_reason:
            draw.text((760, y_cards + 120), "📋 Reason:", font=self.small_font, fill=self.yellow)
            lt_wrapped = textwrap.fill(lt_reason, width=60)
            draw.text((760, y_cards + 145), lt_wrapped, font=self.small_font, fill="#E2E8F0")
        
        # Add key metrics summary for long-term
        total_score = data.get('total_score', 0)
        fund_score = data.get('fundamental_score', 0)
        if total_score > 0:
            score_text = f"Overall Score: {total_score:.1f}/37 | Fundamental: {fund_score:.1f}/24"
            draw.text((760, y_cards + 220), score_text, font=self.tiny_font, fill="#94A3B8")
        
        y_cards += swing_h + 40

        # ========== 5. NEWS SECTION (Card-based) ==========
        draw.text((60, y_cards), "📰 LATEST NEWS & UPDATES", font=self.subheader_font, fill=self.yellow)
        y_cards += 50
        
        news_items = data.get('news_items', [])
        
        if not news_items or len(news_items) == 0:
            draw.rounded_rectangle([60, y_cards, 1340, y_cards + 80], radius=12, 
                                  fill=self.card_bg, outline=self.card_border)
            draw.text((90, y_cards + 30), "No recent news available. Check exchange filings for updates.", 
                     font=self.small_font, fill="#94A3B8")
            y_cards += 100
        else:
            # 2-column news layout
            news_w = 620
            news_h = 100
            news_spacing = 20
            current_news_y = y_cards
            
            # Show up to 12 news items (6 rows x 2 columns)
            for i, news in enumerate(news_items[:12]):
                if i % 2 == 0:
                    news_x = 60
                    if i > 0:
                        current_news_y += news_h + news_spacing
                else:
                    news_x = 680
                
                source = news.get('source', 'News')
                title = news.get('title', 'No title')
                category = news.get('category', 'General')
                sentiment = news.get('sentiment', 'Neutral')
                
                # Truncate title
                if len(title) > 60:
                    title = title[:57] + "..."
                
                # Sentiment color
                sentiment_color = self.green if sentiment == 'Positive' else (self.red if sentiment == 'Negative' else "#94A3B8")
                
                # News card
                draw.rounded_rectangle([news_x, current_news_y, news_x + news_w, current_news_y + news_h], 
                                      radius=12, fill=self.card_bg, outline=sentiment_color, width=2)
                
                # Category badge
                if category != 'General':
                    badge_w = len(category) * 7 + 10
                    draw.rounded_rectangle([news_x + 15, current_news_y + 10, news_x + 15 + badge_w, current_news_y + 30], 
                                          radius=4, fill=sentiment_color + "40", outline=sentiment_color)
                    draw.text((news_x + 20, current_news_y + 12), category, font=self.tiny_font, fill=sentiment_color)
                
                # Title
                title_y = current_news_y + 35
                sentiment_icon = "🟢" if sentiment == 'Positive' else ("🔴" if sentiment == 'Negative' else "⚪")
                draw.text((news_x + 15, title_y), f"{sentiment_icon} {title}", 
                         font=self.small_font, fill="#E2E8F0")
                
                # Source
                draw.text((news_x + 15, current_news_y + 75), f"📌 {source}", 
                         font=self.tiny_font, fill="#64748B")
            
            y_cards = current_news_y + news_h + news_spacing + 40

        # ========== 6. VISUAL METRICS (Enhanced Charts) ==========
        draw.text((60, y_cards), "📊 KEY METRICS VISUALIZATION", font=self.subheader_font, fill=self.yellow)
        y_cards += 50
        
        # Larger, better charts in 2x2 grid
        chart_size = 280
        chart_spacing = 40
        chart_y = y_cards
        
        # Chart 1: Promoter Holding
        chart1_x = 60
        promoter = float(data.get('details', {}).get('Promoter Holding', {}).get('value', '0').replace('%', '') or 0)
        self.draw_large_chart(draw, chart1_x, chart_y, chart_size, "Promoter Holding", 
                            promoter, 100, self.green, f"{promoter:.1f}%")
        
        # Chart 2: Fundamental Score
        chart2_x = 60 + chart_size + chart_spacing
        fund_score_val = data.get('fundamental_score', 0)
        fund_pct = (fund_score_val / 24) * 100
        self.draw_large_chart(draw, chart2_x, chart_y, chart_size, "Fundamental", 
                            fund_pct, 100, self.blue, f"{fund_score_val:.1f}/24")
        
        # Chart 3: Debt Level
        chart3_x = 60 + (chart_size + chart_spacing) * 2
        debt = float(data.get('details', {}).get('Debt / Equity', {}).get('value', '0') or 0)
        debt_pct = min((debt / 2) * 100, 100) if debt > 0 else 0
        debt_color = self.red if debt > 1 else self.green
        self.draw_large_chart(draw, chart3_x, chart_y, chart_size, "Debt/Equity", 
                            debt_pct, 100, debt_color, f"{debt:.2f}")
        
        # Chart 4: Technical Score
        chart4_x = 60 + (chart_size + chart_spacing) * 3
        tech_score_val = data.get('technical_score', 0)
        tech_pct = (tech_score_val / 5) * 100
        self.draw_large_chart(draw, chart4_x, chart_y, chart_size, "Technical", 
                            tech_pct, 100, self.yellow, f"{tech_score_val:.1f}/5")
        
        y_cards += chart_size + 60

        # ========== 7. FINAL VERDICT (Enhanced) ==========
        final_y = y_cards
        draw.rounded_rectangle([60, final_y, 1340, final_y + 180], radius=20, 
                              fill="#1A2332", outline=self.yellow, width=4)
        
        draw.text((90, final_y + 20), "🎯 FINAL VERDICT", font=self.subheader_font, fill=self.yellow)
        
        health_label = data.get('health_label', '')
        health_color = self.green if "High" in health_label else (self.red if "Risk" in health_label else self.yellow)
        draw.text((90, final_y + 70), health_label, font=self.header_font, fill=health_color)
        
        final_action = data.get('final_action', 'Analyze more data.')
        retail_conc = data.get('retail_conclusion', '')
        
        import textwrap
        verdict_text = f"{final_action}\n\n{retail_conc}"
        wrapped_verdict = textwrap.fill(verdict_text, width=80)
        draw.text((90, final_y + 120), wrapped_verdict, font=self.small_font, fill="#E2E8F0")
        
        # Footer
        draw.text((60, self.height - 40), "Generated by Samvruddhi Stock Analyzer | Educational Purpose Only", 
                 font=self.tiny_font, fill="#64748B")
        
        img.save(output_path)
        return output_path

    def draw_large_chart(self, draw, x, y, size, label, percentage, max_val, color, value_text):
        """Draw a large donut chart"""
        center_x = x + size // 2
        center_y = y + size // 2
        radius = size // 2 - 20
        
        # Background circle
        draw.ellipse([center_x - radius, center_y - radius, center_x + radius, center_y + radius], 
                    fill="#1E293B", outline=self.card_border, width=3)
        
        # Donut slice
        if percentage > 0:
            end_angle = int(360 * (percentage / max_val))
            for angle in range(0, end_angle, 2):
                rad = math.radians(angle - 90)
                x1 = center_x + (radius - 8) * math.cos(rad)
                y1 = center_y + (radius - 8) * math.sin(rad)
                x2 = center_x + radius * math.cos(rad)
                y2 = center_y + radius * math.sin(rad)
                draw.line([(x1, y1), (x2, y2)], fill=color, width=3)
        
        # Inner circle (donut effect)
        inner_radius = radius * 0.65
        draw.ellipse([center_x - inner_radius, center_y - inner_radius, 
                     center_x + inner_radius, center_y + inner_radius], 
                    fill=self.bg_color)
        
        # Center text
        draw.text((center_x - 40, center_y - 25), value_text, font=self.body_font, fill=color)
        
        # Label below
        label_width = draw.textlength(label, font=self.small_font)
        draw.text((center_x - label_width // 2, y + size - 30), label, font=self.small_font, fill="#94A3B8")
