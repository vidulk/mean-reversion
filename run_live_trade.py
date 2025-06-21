import os
import smtplib
import ssl
from email.message import EmailMessage
import time
import pandas as pd
from live_trader_config import (
    INSTRUMENTS, TRADE_UNITS, CANDLE_GRANULARITY, CANDLES_TO_FETCH,
    EMAIL_NOTIFICATIONS_ENABLED, EMAIL_SENDER, EMAIL_RECIPIENT
)
from oanda_api_service import (
    get_oanda_client, get_historical_candles, place_trade, 
    get_open_trades, get_instrument_details
)
from technical_indicator_service import add_all_technical_indicators
from trading_logic_service import load_model_and_features, get_trade_decision

from datetime import datetime
#*/15 * * * 1-5 cd /Users/vidhulkhanna/trading-test && EMAIL_APP_PASSWORD="nhut jobn kfde dtto" venv/bin/python3 run_live_trade.py >> tradebot.log 2>&1
def tprint(*args, **kwargs):
    print(datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "-", *args, **kwargs)

def send_email_notification(subject, body):
    """Sends an email notification using Gmail."""
    if not EMAIL_NOTIFICATIONS_ENABLED:
        return

    sender = EMAIL_SENDER
    recipient = EMAIL_RECIPIENT
    # Get the secure password from the environment variable
    password = os.getenv("EMAIL_APP_PASSWORD")

    if not all([sender, recipient, password]):
        tprint("Email notification failed: Missing sender, recipient, or EMAIL_APP_PASSWORD environment variable.")
        return

    msg = EmailMessage()
    msg.set_content(body)
    msg['Subject'] = subject
    msg['From'] = sender
    msg['To'] = recipient

    context = ssl.create_default_context()
    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context) as server:
            server.login(sender, password)
            server.send_message(msg)
            tprint("Email notification sent successfully.")
    except Exception as e:
        tprint(f"Failed to send email notification: {e}")


def main():
    tprint("Starting trading bot...")
    api_client = get_oanda_client()
    if not api_client:
        tprint("Failed to initialize OANDA client. Exiting.")
        return

    model, model_features = load_model_and_features()
    if not model or not model_features:
        tprint("Failed to load model or features. Exiting.")
        return

    for instrument in INSTRUMENTS:
        tprint(f"\n=== Checking {instrument} ===")
        pip_location, display_precision = get_instrument_details(api_client, instrument)
        if pip_location is None or display_precision is None:
            tprint(f"Failed to get instrument details for {instrument}. Skipping.")
            continue

        df_candles = get_historical_candles(api_client, instrument, CANDLES_TO_FETCH, CANDLE_GRANULARITY)
        if df_candles.empty or len(df_candles) < 30:
            tprint(f"Not enough candle data for {instrument}. Skipping.")
            continue

        df_with_indicators = add_all_technical_indicators(df_candles)
        if df_with_indicators.iloc[-2:][['bb_upper', 'bb_lower', 'bb_middle']].isnull().values.any():
            tprint("NaN values found in Bollinger Bands for recent candles. Skipping.")
            continue

        trade_direction, sl_price, tp_price = get_trade_decision(
            df_with_indicators, model, model_features, pip_location, display_precision
        )

        if trade_direction:
            tprint(f"Signal: {trade_direction} {instrument} {TRADE_UNITS} units SL={sl_price} TP={tp_price}")
            current_open_trade = get_open_trades(api_client, instrument)
            if current_open_trade:
                tprint(f"Open trade exists for {instrument}. Skipping new trade.")
            else:
                trade_response = place_trade(api_client, instrument, TRADE_UNITS, trade_direction, sl_price, tp_price)
                if trade_response and ("orderFillTransaction" in trade_response or "orderCreateTransaction" in trade_response):
                    tprint("Trade executed successfully.")
                    # --- Send email notification on success ---
                    notif_title = f"Trade Executed: {instrument}"
                    notif_msg = f"A trade has been executed.\n\nDirection: {trade_direction}\nInstrument: {instrument}\nUnits: {TRADE_UNITS}\nSL: {sl_price}\nTP: {tp_price}"
                    send_email_notification(notif_title, notif_msg)
                else:
                    tprint("Trade execution may have failed or was rejected.")
        else:
            tprint("No trade signal for this instrument.")

    tprint("Trading bot cycle finished.")

if __name__ == "__main__":
    # This script is designed to run once per execution.
    # You would schedule this script to run at the desired frequency (e.g., every 15 minutes via cron or Task Scheduler).
    # For example, if granularity is M15, run it shortly after every 15-minute candle closes.
    main()
    # Example: To run every 15 minutes, you might add a loop with a sleep,
    # but ensure the sleep aligns with candle close times.
    # A cron job is generally better for scheduled execution.
    # while True:
    #     main()
    #     tprint(f"Next check in 15 minutes...")
    #     time.sleep(15 * 60)