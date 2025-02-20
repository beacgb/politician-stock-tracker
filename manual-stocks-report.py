import requests
from bs4 import BeautifulSoup
import pandas as pd
import json
import os
from datetime import datetime, timedelta

# Discord Webhook URL
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")
NEWS_API_KEY = os.getenv("NEWS_API_KEY")  # Required for market context analysis

# Function to fetch market news for context
def get_market_context(stock_ticker):
    """
    Fetches recent news headlines related to the stock ticker.
    Helps explain why a politician might be trading the stock.
    """
    try:
        news_api_url = f"https://newsapi.org/v2/everything?q={stock_ticker}&sortBy=publishedAt&apiKey={NEWS_API_KEY}"
        response = requests.get(news_api_url)
        articles = response.json().get("articles", [])

        if articles:
            latest_news = articles[0]["title"]  # Get the most recent article
            return f"Market Context: {latest_news}"
        else:
            return "Market Context: No major recent news found."
    except Exception:
        return "Market Context: Could not fetch news at this time."

# Function to fetch a politician’s recent transactions
def get_politician_recent_trades(politician_name, all_trades):
    """
    Finds recent transactions by the same politician within the last 30 days.
    Helps determine if this trade is part of a larger trend.
    """
    thirty_days_ago = (datetime.today() - timedelta(days=30)).strftime("%Y-%m-%d")
    recent_trades = [
        trade for trade in all_trades
        if trade["politician"] == politician_name and trade["trade_date"] >= thirty_days_ago
    ]
    return recent_trades

# Function to analyze potential motivation behind the trade
def analyze_trade_motivation(trade, recent_trades):
    """
    Analyzes why a politician might have made a particular trade
    based on recent trades, market context, and external events.
    """
    market_context = get_market_context(trade["ticker"])
    trend_summary = "No clear trend detected."

    if recent_trades:
        trade_types = [t["trade_type"] for t in recent_trades]
        if trade_types.count("Buy") > trade_types.count("Sell"):
            trend_summary = "This politician has been consistently buying this stock in recent weeks."
        elif trade_types.count("Sell") > trade_types.count("Buy"):
            trend_summary = "This politician has been offloading shares of this stock recently."

    return f"{market_context}\nTrend Analysis: {trend_summary}"

# Function to scrape CapitolTrades
def scrape_capitol_trades():
    url = "https://www.capitoltrades.com/"
    response = requests.get(url)
    soup = BeautifulSoup(response.text, "html.parser")

    trades = []
    rows = soup.select("table tbody tr")
    
    for row in rows:
        cols = row.find_all("td")
        if len(cols) < 7:
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

        trades.append({
            "politician": politician,
            "stock": stock,
            "ticker": ticker,
            "trade_type": trade_type,
            "shares": shares,
            "price": price,
            "total_amount": total_amount,
            "trade_date": trade_date
        })

    return trades

print("Sending the following data to Discord:")
# Get trades
trades = scrape_capitol_trades()

# Debugging: Print trades before sending to Discord
print("Scraped Trades:", trades)  

# Function to send a Discord webhook notification
def send_discord_notification(trades):
    if not trades:
        messages = ["**Today's Political Stock Transactions:**\n\nNo transactions reported today."]
    else:
        df = pd.DataFrame(trades)
        messages = []
        chunk_size = 1800  # Keep under 2000-character limit

        report = "**Today's Political Stock Transactions:**\n\n" + df.to_string(index=False)
        while report:
            messages.append(report[:chunk_size])  # Split message
            report = report[chunk_size:]

    for message in messages:
        payload = {"content": f"```{message}```"}
        response = requests.post(DISCORD_WEBHOOK_URL, json=payload, headers={"Content-Type": "application/json"})
        print(f"Discord Response: {response.status_code}, {response.text}")  # Debugging

# Function to filter today's trades and add analysis
def get_todays_trades():
    all_trades = scrape_capitol_trades()
    today = datetime.today().strftime("%Y-%m-%d")
    todays_trades = [trade for trade in all_trades if trade["trade_date"] == today]

    # Enhance each trade with market context and trend analysis
    for trade in todays_trades:
        recent_trades = get_politician_recent_trades(trade["politician"], all_trades)
        trade["analysis"] = analyze_trade_motivation(trade, recent_trades)

    return todays_trades

# Run monitoring for today's trades
todays_trades = get_todays_trades()
send_discord_notification(todays_trades)

# Print report to console
if todays_trades:
    df = pd.DataFrame(todays_trades)
    print("Today's Political Stock Transactions with Market Context:")
    print(df.to_string(index=False))
else:
    print("No political stock transactions reported today.")
