import sqlite3
import threading
import time
import random
import subprocess
from datetime import datetime
from flask import Flask, render_template_string, request

# ==========================================
# 1. CONFIGURATION & FLASK SETUP
# ==========================================
app = Flask(__name__)
DB_FILE = "deals.db"

# Your Discord Webhook URL
DISCORD_WEBHOOK_URL = "" 

# ==========================================
# 2. DATABASE INITIALIZATION
# ==========================================
def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS deals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            price TEXT NOT NULL,
            category TEXT NOT NULL,
            store TEXT NOT NULL,
            url TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # --- CLEANUP ---
    # Delete any lingering mock data (items with '#' as the URL) from previous testing
    cursor.execute("DELETE FROM deals WHERE url = '#'")
    # Delete broken/empty titles that cause ghost cards on the dashboard
    cursor.execute("DELETE FROM deals WHERE title = '' OR title IS NULL OR title = 'Tracked Sam''s Club Item'")
    
    conn.commit()
    conn.close()

# ==========================================
# 3. BACKGROUND SCRAPING & NOTIFICATION LOGIC
# ==========================================
def send_discord_alert(title, current_price, previous_price, url):
    """Sends a rich embedded message to a Discord server."""
    if not DISCORD_WEBHOOK_URL:
        return
        
    import requests
    
    data = {
        "content": "🚨 **PRICE DROP ALERT!** 🚨",
        "embeds": [{
            "title": title,
            "url": url,
            "color": 5814783,
            "fields": [
                {"name": "New Price", "value": current_price, "inline": True},
                {"name": "Old Price", "value": previous_price, "inline": True}
            ],
            "footer": {"text": "Raspberry Pi "}
        }]
    }
    
    try:
        requests.post(DISCORD_WEBHOOK_URL, json=data)
        print(f"[+] Discord alert sent for {title}!")
    except Exception as e:
        print(f"[!] Failed to send Discord alert: {e}")

def scrape_local_stores():
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Starting background scrape cycle via Remote Debugging...")
    
    deals_found_this_cycle = 0
    scraped_deals = []

    try:
        from selenium import webdriver
        from selenium.webdriver.chrome.service import Service
        from selenium.webdriver.chrome.options import Options
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        
        target_urls = [
            "https://www.samsclub.com/ip/Dove-Deep-Moisture-Body-Wash-with-Pump-30-6-fl-oz-2-ct/15268065690",
            "https://www.samsclub.com/ip/Dove-Nourish-Restore-5-in-1-Shampoo-33-8-fl-oz/16365919172",
            "https://www.samsclub.com/ip/Gatorade-Sports-Drinks-Variety-Pack-20-fl-oz-24-pk/13907722333"
        ]

        # --- THE HIJACK TACTIC ---
        options = Options()
        # Instead of starting a browser, connect to the human one we opened on port 9222
        options.add_experimental_option("debuggerAddress", "127.0.0.1:9222")
        
        service = Service('/usr/bin/chromedriver')
        
        print("[*] Connecting to existing native Chromium session...")
        driver = webdriver.Chrome(service=service, options=options)

        for i, url in enumerate(target_urls):
            print(f"[*] Steering human browser to: {url[:50]}...")
            
            try:
                driver.get(url)

                # Random human reading pause
                time.sleep(random.uniform(2.0, 4.0))
                print(f"[*] Page Title loaded as: '{driver.title}'")

                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.XPATH, "//*[@itemprop='price'] | //*[@data-seo-id='hero-price'] | //*[contains(@class, 'Price-characteristic')]"))
                )

                try:
                    price_elem = driver.find_element(By.XPATH, "//*[@itemprop='price']")
                except:
                    try:
                        price_elem = driver.find_element(By.XPATH, "//*[@data-seo-id='hero-price']")
                    except:
                        price_elem = driver.find_element(By.XPATH, "//*[contains(@class, 'Price-characteristic')]")

                try:
                    title_elem = driver.find_element(By.TAG_NAME, "h1")
                    title_text = title_elem.text.strip()
                except:
                    title_text = "Tracked Sam's Club Item"

                price_text = price_elem.text.strip()
                print(f"[+] Found {title_text} for {price_text}!")

                # --- Price Drop Logic ---
                conn = sqlite3.connect(DB_FILE)
                cursor = conn.cursor()
                cursor.execute('SELECT price FROM deals WHERE url = ? ORDER BY timestamp DESC LIMIT 1', (url,))
                last_record = cursor.fetchone()
                conn.close()

                if last_record:
                    previous_price_text = last_record[0]
                    try:
                        curr_val = float(price_text.replace('$', '').replace(',', ''))
                        prev_val = float(previous_price_text.replace('$', '').replace(',', ''))

                        if curr_val < prev_val:
                            print(f"[!] PRICE DROP DETECTED! {previous_price_text} -> {price_text}")
                            send_discord_alert(title_text, price_text, previous_price_text, url)
                    except ValueError:
                        pass

                scraped_deals.append({
                    "title": title_text,
                    "price": price_text,
                    "category": "Watchlist",
                    "store": "Sam's Club",
                    "url": url
                })

                # Safe hiding pause
                if i < len(target_urls) - 1:
                    delay = random.uniform(5.0, 9.0)
                    print(f"[*] Pausing for {delay:.1f} seconds to reset trust...")
                    time.sleep(delay)

            except Exception as wait_err:
                print(f"[!] Timeout waiting for price to load. Error: {wait_err}")

        # IMPORTANT: We DO NOT driver.quit() here! 
        # If we do, it closes the human browser. We just let it finish the loop.
        print(f"[+] Successfully parsed {len(scraped_deals)} items from Watchlist.")

    except Exception as e:
        print(f"[!] Error connecting to browser: {e}")

    # --- FALLBACK / SIMULATED DATA ---
    if not scraped_deals:
        print("[-] Using mock data because live scrape returned 0 items.")
        scraped_deals = [
            {"title": "65-inch 4K Smart TV", "price": "$299.99", "category": "Electronics", "store": "Best Buy Local", "url": "#"},
            {"title": "Ergonomic Mesh Office Chair", "price": "$89.50", "category": "Furniture", "store": "Office Max", "url": "#"},
            {"title": "Dove Body Wash Deep Moisture (Mock)", "price": "$14.98", "category": "Watchlist", "store": "Sam's Club", "url": "#"}
        ]

    deals_found_this_cycle = len(scraped_deals)

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    # Capture the Pi's local system time instead of relying on SQLite's UTC default
    local_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    for deal in scraped_deals:
        cursor.execute(
            'INSERT INTO deals (title, price, category, store, url, timestamp) VALUES (?, ?, ?, ?, ?, ?)',
            (deal["title"], deal["price"], deal["category"], deal["store"], deal["url"], local_time)
        )
    conn.commit()
    conn.close()
    print(f"[+] Scraped and saved {deals_found_this_cycle} new deals.")

def run_scheduler():
    import schedule

    scrape_local_stores()
    schedule.every(30).minutes.do(scrape_local_stores)

    while True:
        schedule.run_pending()
        time.sleep(1)

# ==========================================
# 4. WEB DASHBOARD (HTML / TAILWIND)
# ==========================================
DASHBOARD_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title> Hub - Local Deals</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <style>
        ::-webkit-scrollbar { display: none; }
        body { -ms-overflow-style: none; scrollbar-width: none; }
    </style>
</head>
<body class="bg-slate-900 text-slate-100 font-sans min-h-screen">
    <header class="bg-slate-800 shadow-md p-4 sticky top-0 z-50">
        <div class="max-w-6xl mx-auto flex flex-col md:flex-row justify-between items-center gap-4">
            <h1 class="text-2xl font-bold text-emerald-400 tracking-wide">
                <span class="text-white">📡</span> Local Deal Hub
            </h1>
            <nav class="flex flex-wrap gap-2 justify-center">
                <a href="/" class="px-4 py-2 rounded-full text-sm font-medium transition-colors {% if not active_category %}bg-emerald-500 text-white{% else %}bg-slate-700 hover:bg-slate-600 text-slate-300{% endif %}">
                    All Deals
                </a>
                {% for category in categories %}
                <a href="/?category={{ category|urlencode }}"
                   class="px-4 py-2 rounded-full text-sm font-medium transition-colors {% if active_category == category %}bg-emerald-500 text-white{% else %}bg-slate-700 hover:bg-slate-600 text-slate-300{% endif %}">
                    {{ category }}
                </a>
                {% endfor %}
            </nav>
        </div>
    </header>

    <main class="max-w-6xl mx-auto p-4 py-8">
        {% if active_category %}
            <h2 class="text-xl text-slate-400 mb-6 border-b border-slate-700 pb-2">Showing deals for: <span class="text-white font-semibold">{{ active_category }}</span></h2>
        {% endif %}

        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {% for deal in deals %}
            <div class="bg-slate-800 rounded-xl overflow-hidden shadow-lg border border-slate-700 hover:border-emerald-500 transition-all duration-300 flex flex-col">
                <div class="p-5 flex-grow">
                    <div class="flex justify-between items-start mb-2">
                        <span class="text-xs font-bold uppercase tracking-wider text-emerald-400 bg-emerald-900/30 px-2 py-1 rounded">
                            {{ deal.category }}
                        </span>
                        <!-- Updated to use the new formatted 12-hour time -->
                        <span class="text-xs text-slate-400">{{ deal.formatted_time }}</span>
                    </div>
                    <h3 class="text-lg font-bold text-white mb-2 leading-tight">{{ deal.title }}</h3>
                    <p class="text-sm text-slate-400 mb-4">📍 {{ deal.store }}</p>
                </div>
                <div class="bg-slate-900 p-4 border-t border-slate-700 flex justify-between items-center">
                    <span class="text-2xl font-black text-emerald-400">{{ deal.price }}</span>
                    <a href="{{ deal.url }}" target="_blank" class="bg-slate-700 hover:bg-slate-600 text-white text-sm px-4 py-2 rounded-lg transition-colors">
                        View Deal
                    </a>
                </div>
            </div>
            {% else %}
            <div class="col-span-full flex flex-col items-center justify-center py-20 text-slate-500">
                <p class="text-lg">No deals found for this category right now.</p>
            </div>
            {% endfor %}
        </div>
    </main>

    <footer class="fixed bottom-0 w-full bg-slate-900/90 backdrop-blur border-t border-slate-800 p-2 text-center text-xs text-slate-500">
        Updating automatically every 30 minutes • Hosted on Raspberry Pi
    </footer>
</body>
</html>
"""

@app.route("/")
def index():
    requested_category = request.args.get('category')

    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute('SELECT DISTINCT category FROM deals ORDER BY category')
    categories = [row['category'] for row in cursor.fetchall() if row['category'] != "Watchlist" and row['category'] != "Electronics" and row['category'] != "Furniture"]

    cursor.execute('SELECT COUNT(*) FROM deals WHERE category = "Watchlist"')
    if cursor.fetchone()[0] > 0 and "Watchlist" not in categories:
        categories.insert(0, "Watchlist")

    # Use MAX(id) to find the newest entry instead of MAX(timestamp) 
    # to prevent old UTC timestamps from overriding new local timestamps.
    if requested_category and requested_category in categories:
        cursor.execute('''
            SELECT * FROM deals 
            WHERE id IN (SELECT MAX(id) FROM deals WHERE category = ? GROUP BY title)
            ORDER BY id DESC
        ''', (requested_category,))
    else:
        cursor.execute('''
            SELECT * FROM deals 
            WHERE id IN (SELECT MAX(id) FROM deals GROUP BY title)
            ORDER BY id DESC
        ''')
        requested_category = None

    raw_deals = cursor.fetchall()
    conn.close()

    # Process and format the deals before sending them to the HTML template
    deals = []
    for row in raw_deals:
        deal_dict = dict(row)
        try:
            # Parse the standard SQL format and convert to 12-hour AM/PM
            dt = datetime.strptime(deal_dict['timestamp'], '%Y-%m-%d %H:%M:%S')
            deal_dict['formatted_time'] = dt.strftime('%I:%M %p') # e.g., '06:19 PM'
        except Exception:
            deal_dict['formatted_time'] = deal_dict['timestamp']
            
        deals.append(deal_dict)

    return render_template_string(
        DASHBOARD_HTML,
        deals=deals,
        categories=categories,
        active_category=requested_category
    )

# ==========================================
# 5. STARTUP SCRIPT
# ==========================================
if __name__ == "__main__":
    print("Initializing Database...")
    init_db()

    print("Starting background scraping scheduler thread...")
    scraper_thread = threading.Thread(target=run_scheduler, daemon=True)
    scraper_thread.start()

    print("Starting Web Dashboard. Access it at http://0.0.0.0:5000")
    app.run(host="0.0.0.0", port=5000, debug=False)
