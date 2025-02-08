import requests
from bs4 import BeautifulSoup
import pandas as pd
import smtplib
from email.mime.text import MIMEText
import json
import time
import os

# Email settings
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
EMAIL_SENDER = os.getenv("EMAIL_SENDER")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
EMAIL_RECIPIENT = os.getenv("EMAIL_RECIPIENT")

# Discord Webhook URL
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")

# Cache file to store the last known trades
CACHE_FILE = "trade_cache.json"

# Function to load cached data
def load_cache():
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, "r") as f:
            return json.load(f)
    return []

# Function to save cache data
def save_cache(data):
    with open(CACHE_FILE, "w") as f:
        json.dump(data, f)

# Function to fetch market news for context
def get_market_context(stock_ticker):
    """
    Fetches recent news headlines related to the stock ticker.
    This helps explain why a politician might be trading the stock.
    """
    try:
        news_api_url = f"https://newsapi.org/v2/everything?q={stock_ticker}&sortBy=publishedAt&apiKey=YOUR_NEWS_API_KEY"
        response = requests.get(news_api_url)
        articles = response.json().get("articles", [])

        if articles:
            latest_news = articles[0]["title"]  # Get the most recent article
            return f"Market Context: {latest_news}"
        else:
            return "Market Context: No major recent news found."
    except Exception:
        return "Market Context: Could not fetch news at this time."

# Function to scrape CapitolTrades
def scrape_capitol_trades():
    url = "https://www.capitoltrades.com/"
    response = requests.get(url)
    soup = BeautifulSoup(response.text, "html.parser")

    trades = []
    rows = soup.select("table tbody tr")
    
    for row in rows:
        cols = row.find_all("td")
        if len(cols) < 7:  # Ensure the expected number of columns exist
            continue

        politician = cols[0].text.strip()
        stock = cols[1].text.strip()
        ticker = cols[2].text.strip()
        trade_type = cols[3].text.strip()
        shares = cols[4].text.strip()
        price = cols[5].text.strip()
        trade_date = cols[6].text.strip()

        try:
            total_amount = float(shares.replace(",", "")) * float(price.replace("$", "").replace(",", ""))
        except ValueError:
            total_amount = "N/A"

        market_context = get_market_context(ticker)

        trades.append({
            "politician": politician,
            "stock": stock,
            "ticker": ticker,
            "trade_type": trade_type,
            "shares": shares,
            "price": price,
            "total_amount": total_amount,
            "trade_date": trade_date,
            "market_context": market_context
        })

    return trades

# Function to send an email alert
def send_email(trades):
    df = pd.DataFrame(trades)
    email_body = df.to_html(index=False)

    msg = MIMEText(email_body, "html")
    msg["Subject"] = "New Political Stock Transactions Detected"
    msg["From"] = EMAIL_SENDER
    msg["To"] = EMAIL_RECIPIENT

    with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
        server.starttls()
        server.login(EMAIL_SENDER, EMAIL_PASSWORD)
        server.sendmail(EMAIL_SENDER, EMAIL_RECIPIENT, msg.as_string())

# Function to send a Discord webhook notification
def send_discord_notification(trades):
    df = pd.DataFrame(trades)
    message = "**New Political Stock Trades Detected:**\n\n" + df.to_string(index=False)

    payload = {"content": f"```{message}```"}
    requests.post(DISCORD_WEBHOOK_URL, data=json.dumps(payload), headers={"Content-Type": "application/json"})

# Function to monitor trades and notify when there are new transactions
def monitor_trades():
    last_trades = load_cache()
    new_trades = scrape_capitol_trades()

    # Only notify if new trades are detected
    if new_trades and new_trades != last_trades:
        send_email(new_trades)
        send_discord_notification(new_trades)
        save_cache(new_trades)  # Update the cache with new trades

# Run monitoring
monitor_trades()
