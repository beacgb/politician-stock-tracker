import requests
from bs4 import BeautifulSoup
import pandas as pd
import smtplib
from email.mime.text import MIMEText
import json
import time

# Email settings
SMTP_SERVER = "smtp.gmail.com"  # Change if using another provider
SMTP_PORT = 587
EMAIL_SENDER = "beatricecgomes@gmail.com"
EMAIL_PASSWORD = "pvcydhwmsmzbxwew"  # Use an app password if needed
EMAIL_RECIPIENT = "tjandring4@gmail.com"

# Discord Webhook URL
DISCORD_WEBHOOK_URL = "https://discord.com/api/webhooks/1337650682672709694/_KTb5cVs4cQ-SUdCO24N9pNEtK8xvDad3C3-1ihrdU8qZaMn9URhROeuBVhyiXTcie_U"

# Function to scrape CapitolTrades
def scrape_capitol_trades():
    url = "https://www.capitoltrades.com/"
    response = requests.get(url)
    soup = BeautifulSoup(response.text, "html.parser")
    
    trades = []
    rows = soup.select("table tbody tr")  
    for row in rows:
        cols = row.find_all("td")
        if len(cols) < 6:
            continue

        politician = cols[0].text.strip()
        stock = cols[1].text.strip()
        ticker = cols[2].text.strip()
        trade_type = cols[3].text.strip()
        shares = cols[4].text.strip()
        price = cols[5].text.strip()

        try:
            total_amount = float(shares.replace(",", "")) * float(price.replace("$", "").replace(",", ""))
        except ValueError:
            total_amount = "N/A"

        trades.append([politician, stock, ticker, trade_type, shares, price, total_amount])

    return trades

# Function to send an email alert
def send_email(trades):
    df = pd.DataFrame(trades, columns=["Politician", "Stock", "Ticker", "Type", "Shares", "Price", "Total Amount"])
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
    df = pd.DataFrame(trades, columns=["Politician", "Stock", "Ticker", "Type", "Shares", "Price", "Total Amount"])
    message = "**New Political Stock Trades Detected:**\n\n" + df.to_string(index=False)

    payload = {"content": f"```{message}```"}
    requests.post(DISCORD_WEBHOOK_URL, data=json.dumps(payload), headers={"Content-Type": "application/json"})

# Function to monitor trades and notify when there are new transactions
def monitor_trades():
    last_trades = []
    
    while True:
        trades = scrape_capitol_trades()
        
        if trades and trades != last_trades:  # Only notify if there are new trades
            send_email(trades)
            send_discord_notification(trades)
            last_trades = trades  # Update last known trades

        time.sleep(3600)  # Wait for 1 hour before checking again

# Start monitoring
monitor_trades()