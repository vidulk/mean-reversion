import pandas as pd
import numpy as np
from live_trader_config import (
    BOLLINGER_PERIOD, BOLLINGER_STD_DEV, RSI_PERIOD,
    MACD_FAST_PERIOD, MACD_SLOW_PERIOD, MACD_SIGNAL_PERIOD
)

def add_bollinger_bands(df: pd.DataFrame, period: int = BOLLINGER_PERIOD, std_dev: float = BOLLINGER_STD_DEV) -> pd.DataFrame:
    """Add Bollinger Bands manually"""
    df = df.copy()
    df['bb_middle'] = df['close'].rolling(window=period).mean()
    bb_std = df['close'].rolling(window=period).std()
    df['bb_upper'] = df['bb_middle'] + (bb_std * std_dev)
    df['bb_lower'] = df['bb_middle'] - (bb_std * std_dev)
    # Calculate bb_percent, handling potential division by zero or NaN in bb_upper/bb_lower
    bb_range = df['bb_upper'] - df['bb_lower']
    df['bb_percent'] = np.where(bb_range != 0, (df['close'] - df['bb_lower']) / bb_range, np.nan)
    return df

def add_all_technical_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """Add all technical indicators needed for the model."""
    df_out = df.copy()
    
    # Bollinger Bands
    df_out = add_bollinger_bands(df_out, period=BOLLINGER_PERIOD, std_dev=BOLLINGER_STD_DEV)
    
    # RSI
    delta = df_out['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=RSI_PERIOD, min_periods=1).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=RSI_PERIOD, min_periods=1).mean()
    rs = gain / loss
    df_out['rsi'] = 100 - (100 / (1 + rs))
    
    # MACD
    ema_fast = df_out['close'].ewm(span=MACD_FAST_PERIOD, adjust=False).mean()
    ema_slow = df_out['close'].ewm(span=MACD_SLOW_PERIOD, adjust=False).mean()
    df_out['macd'] = ema_fast - ema_slow
    df_out['macd_signal'] = df_out['macd'].ewm(span=MACD_SIGNAL_PERIOD, adjust=False).mean()
    
    # Volume indicators (if volume available)
    if 'volume' in df_out.columns:
        df_out['volume_sma'] = df_out['volume'].rolling(window=20, min_periods=1).mean()
        # Avoid division by zero for volume_ratio
        df_out['volume_ratio'] = np.where(df_out['volume_sma'] != 0, df_out['volume'] / df_out['volume_sma'], np.nan)

    # Price momentum
    df_out['price_change_1'] = df_out['close'].pct_change(1)
    df_out['price_change_5'] = df_out['close'].pct_change(5)
    df_out['volatility'] = df_out['close'].rolling(window=20, min_periods=1).std()
    
    # Time features (ensure index is DatetimeIndex before calling this)
    if isinstance(df_out.index, pd.DatetimeIndex):
        df_out['hour'] = df_out.index.hour
        df_out['day_of_week'] = df_out.index.dayofweek
    else:
        # Add NaN columns if index is not datetime, to match expected features
        print("Warning: DataFrame index is not DatetimeIndex. Time features will be NaN.")
        df_out['hour'] = np.nan
        df_out['day_of_week'] = np.nan
        
    return df_out