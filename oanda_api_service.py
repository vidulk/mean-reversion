import oandapyV20
import oandapyV20.endpoints.pricing as pricing
import oandapyV20.endpoints.instruments as instruments
import oandapyV20.endpoints.orders as orders
import oandapyV20.endpoints.trades as trades
import oandapyV20.endpoints.accounts as accounts
import oandapyV20.endpoints.transactions as transactions # <-- Add this import
from oandapyV20.contrib.requests import MarketOrderRequest, StopLossDetails, TakeProfitDetails
import pandas as pd

from live_trader_config import OANDA_API_KEY, OANDA_ACCOUNT_ID, OANDA_ENVIRONMENT

def get_oanda_client():
    """Initializes and returns an OANDA API client."""
    return oandapyV20.API(access_token=OANDA_API_KEY, environment=OANDA_ENVIRONMENT)

def get_instrument_details(api_client, instrument_name: str):
    """Fetches instrument details like pip location and display precision."""
    # The pricing.PricingInfo endpoint doesn't reliably return instrument properties.
    # Using accounts.AccountInstruments is the correct way to get static instrument data.
    r = accounts.AccountInstruments(accountID=OANDA_ACCOUNT_ID)
    try:
        response = api_client.request(r)
        # The response contains a list of all tradable instruments
        for instrument_data in response.get('instruments', []):
            if instrument_data['name'] == instrument_name:
                pip_location = instrument_data['pipLocation']
                display_precision = instrument_data['displayPrecision']
                return pip_location, display_precision
        # If the loop finishes without finding the instrument
        print(f"Error: Instrument '{instrument_name}' not found in tradable instruments for the account.")
        return None, None
    except Exception as e:
        print(f"Error fetching instrument details for {instrument_name}: {e}")
        return None, None


def get_historical_candles(api_client, instrument: str, count: int, granularity: str) -> pd.DataFrame:
    """Fetches historical candle data from OANDA."""
    params = {
        "count": count,
        "granularity": granularity,
        "price": "M",  # Midpoint candles
    }
    r = instruments.InstrumentsCandles(instrument=instrument, params=params)
    try:
        api_client.request(r)
        candles = []
        for candle_data in r.response.get('candles', []):
            candles.append({
                'time': pd.to_datetime(candle_data['time']),
                'open': float(candle_data['mid']['o']),
                'high': float(candle_data['mid']['h']),
                'low': float(candle_data['mid']['l']),
                'close': float(candle_data['mid']['c']),
                'volume': int(candle_data['volume'])
            })
        df = pd.DataFrame(candles)
        if not df.empty:
            df.set_index('time', inplace=True)
        return df
    except Exception as e:
        print(f"Error fetching candles for {instrument}: {e}")
        return pd.DataFrame()

def place_trade(api_client, instrument: str, units: int, direction: str, sl_price: str, tp_price: str):
    """Places a market order with SL and TP."""
    trade_units = units if direction == "BUY" else -units
    
    order_request = MarketOrderRequest(
        instrument=instrument,
        units=trade_units,
        stopLossOnFill=StopLossDetails(price=sl_price).data,
        takeProfitOnFill=TakeProfitDetails(price=tp_price).data
    )
    r = orders.OrderCreate(accountID=OANDA_ACCOUNT_ID, data=order_request.data)
    try:
        response = api_client.request(r)
        print(f"Trade placed: {response}")
        return response
    except oandapyV20.exceptions.V20Error as e:
        print(f"OANDA API Error placing trade: {e}")
        if hasattr(e, 'msg') and 'message' in e.msg:
            print(f"Error details: {e.msg['message']}")
        return None
    except Exception as e:
        print(f"General Error placing trade: {e}")
        return None

def get_open_trades(api_client, instrument_name: str):
    """Checks for open trades for a specific instrument."""
    r = trades.OpenTrades(accountID=OANDA_ACCOUNT_ID)
    try:
        api_client.request(r)
        for trade in r.response.get('trades', []):
            if trade['instrument'] == instrument_name:
                return trade # Returns the first open trade found for the instrument
        return None
    except Exception as e:
        print(f"Error fetching open trades: {e}")
        return None

def get_transactions_in_range(api_client, from_date: str, to_date: str):
    """
    Fetches account transactions within a given date range.
    Dates should be in RFC3339 format (e.g., '2025-06-01T00:00:00Z').
    NOTE: This function fetches up to 1000 transactions, which is the API limit
    per request. For more, pagination would be required.
    """
    params = {
        "from": from_date,
        "to": to_date,
        "pageSize": 1000  # Max page size
    }
    
    # The correct, instantiable class is transactions.TransactionIDRange
    r = transactions.TransactionIDRange(accountID=OANDA_ACCOUNT_ID, params=params)
    try:
        api_client.request(r)
        all_transactions = r.response.get('transactions', [])
        
        
        if len(all_transactions) == 1000:
            print("Warning: Fetched 1000 transactions, the maximum per request. Some older trades might be missing.")
            
        return all_transactions
    except Exception as e:
        print(f"Error fetching transactions: {e}")
        return []

def get_recent_transactions(api_client, count=500):
    """
    Fetches the most recent transactions for the account.
    """
    params = {
        "pageSize": count  # Fetch up to 'count' transactions
    }
    # Using TransactionIDRange without date params should return the most recent transactions.
    r = transactions.TransactionIDRange(accountID=OANDA_ACCOUNT_ID, params=params)
    try:
        api_client.request(r)
        return r.response.get('transactions', [])
    except Exception as e:
        print(f"Error fetching recent transactions: {e}")
        return []

def get_closed_trades(api_client, count=50):
    """
    Fetches the most recently closed trades for the account. This is much more
    reliable than parsing the full transaction history.
    """
    params = {
        "state": "CLOSED",  # Specify that we only want closed trades
        "count": count      # The number of recent trades to get
    }
    r = trades.TradesList(accountID=OANDA_ACCOUNT_ID, params=params)
    try:
        api_client.request(r)
        return r.response.get('trades', [])
    except Exception as e:
        print(f"Error fetching closed trades: {e}")
        return []