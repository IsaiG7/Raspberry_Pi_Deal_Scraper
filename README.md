# 📡 Local Deal Hub: Raspberry Pi 5 Scraper & Dashboard

A locally hosted web application and automated web scraping engine built for the Raspberry Pi 5 and others with optimization. This project tracks specific products across major retailers (like Sam's Club), bypasses enterprise grade bot protection using a remote debugging "Hijack" strategy, and alerts the user of price drops via a real time Discord Webhook.

## 🚀 Features

* **Stealth Scraping Engine:** Utilizes Selenium via Chromium Remote Debugging to connect to a live, human authenticated browser session, successfully evading advanced canvas fingerprinting and PerimeterX bot protections.
* **Smart Price Parsing:** Uses Regular Expressions (`re`) to extract raw numerical values from retailer HTML, immune to sudden string changes like "Sale" or "Now $X.XX".
* **Automated Scheduler:** Runs background scraping cycles automatically at randomized intervals using the Python `schedule` library.
* **Discord Integration:** Sends detailed embedded push notifications directly to a Discord server the moment a price drop is calculated.
* **Local Web Dashboard:** Serves a responsive, dark mode dashboard built with Flask and Tailwind CSS to display the Watchlist inventory and historical timestamps in local MDT format.
* **Self-Cleaning Database:** Built on SQLite with automated cleanup functions to prevent duplicate entries and purge broken HTML pulls.

## 🛠️ Technology Stack

* **Backend:** Python 3, Flask, SQLite3
* **Scraping:** Selenium WebDriver, Chrome DevTools Protocol (CDP)
* **Frontend:** HTML5, Tailwind CSS (via CDN), Jinja2 Templating
* **Hardware:** Raspberry Pi 5 (running Debian Bookworm / Raspberry Pi OS)

## 📦 Installation & Setup

### 1. System Requirements (Raspberry Pi OS)
You must install the native Chromium browser and the corresponding WebDriver bridge.
```bash
sudo apt update
sudo apt install chromium-browser chromium-chromedriver
```

### 2. Python Environment
Clone this repository, set up a virtual environment, and install the required dependencies.
```bash
git clone https://github.com/IsaiG7/Rasberry_Pi_Deal_Scraper.git
cd my_deal_hub
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 3. Discord Webhook Configuration
1. Create a Discord Webhook in your server settings (`Integrations` -> `Webhooks`).
2. Copy the Webhook URL.
3. Open `deal_hub.py` and paste the URL into the `DISCORD_WEBHOOK_URL` variable at the top of the file.

## 🕹️ Usage: The "Hijack" Strategy

Because enterprise retailers use aggressive bot protection (PerimeterX), standard headless scraping will result in blocked IPs and CAPTCHAs. This project uses a "Trust Inheritance" strategy.

**Step 1: Launch the Backdoor Browser**
Open a terminal and launch the native Chromium browser with a remote debugging port open:
```bash
chromium --remote-debugging-port=9222 --user-data-dir="/home/YOUR_PI_USER/.config/chromium" &
```

**Step 2: Authenticate**
Navigate to your target URL in the browser that opens. If a "Press & Hold" CAPTCHA appears, solve it manually to generate a native trust cookie. **Leave the browser open.**

**Step 3: Run the Engine**
In a separate terminal, launch the Python application:
```bash
python deal_hub.py
```
The script will hijack the open browser on port 9222, utilize your native trust tokens to cycle through the Watchlist URLs, and serve the dashboard locally at `http://localhost:5000`.

## ⚠️ Disclaimer
This project was built for educational purposes to demonstrate Python automation, HTML parsing, and local networking on a Raspberry Pi. Ensure your scraping activities comply with the Terms of Service of the targeted websites. 