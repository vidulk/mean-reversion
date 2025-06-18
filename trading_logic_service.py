import pandas as pd
import numpy as np
import joblib
import json
from live_trader_config import (
    MODEL_FILE_PATH, MODEL_FEATURES_FILE_PATH, SL_PIPS
)
from technical_indicator_service import add_all_technical_indicators

def load_model_and_features():
    """Loads the trained model and feature list."""
    try:
        model = joblib.load(MODEL_FILE_PATH)
        with open(MODEL_FEATURES_FILE_PATH, 'r') as f:
            model_features = json.load(f)
        return model, model_features
    except FileNotFoundError as e:
        print(f"Error: Model or features file not found: {e}")
        return None, None
    except Exception as e:
        print(f"Error loading model or features: {e}")
        return None, None

def prepare_features_for_prediction(feature_candle_data: pd.Series, 
                                    is_upper_break: bool, 
                                    is_lower_break: bool, 
                                    expected_feature_list: list) -> pd.DataFrame:
    """Prepares a single row DataFrame for model prediction."""
    features = {}
    
    # Basic features from the candle
    features['bb_percent'] = feature_candle_data.get('bb_percent', np.nan)
    features['rsi'] = feature_candle_data.get('rsi', np.nan)
    features['macd'] = feature_candle_data.get('macd', np.nan)
    features['macd_signal'] = feature_candle_data.get('macd_signal', np.nan)
    features['price_change_1'] = feature_candle_data.get('price_change_1', np.nan)
    features['price_change_5'] = feature_candle_data.get('price_change_5', np.nan)
    features['volatility'] = feature_candle_data.get('volatility', np.nan)
    
    if 'volume_ratio' in expected_feature_list and 'volume_ratio' in feature_candle_data:
        features['volume_ratio'] = feature_candle_data.get('volume_ratio', np.nan)
    elif 'volume_ratio' in expected_feature_list: # Ensure column exists if expected
         features['volume_ratio'] = np.nan

    # Time features
    if isinstance(feature_candle_data.name, pd.Timestamp):
        features['hour'] = feature_candle_data.name.hour
        features['day_of_week'] = feature_candle_data.name.dayofweek
    else: # Ensure columns exist if expected
        features['hour'] = np.nan
        features['day_of_week'] = np.nan

    # Break type
    if is_upper_break:
        features['break_type'] = 1
    elif is_lower_break:
        features['break_type'] = 0
    else: # Should not happen if called correctly, but as a fallback
        features['break_type'] = np.nan 

    # Profit Potential (distance to middle BB in pips)
    # This matches the logic from your create_ml_dataset for 'profit_potential'
    price_at_decision = feature_candle_data.get('close', np.nan)
    bb_middle_at_decision = feature_candle_data.get('bb_middle', np.nan)

    if pd.notna(price_at_decision) and pd.notna(bb_middle_at_decision):
        if is_upper_break: # Short trade, potential is price_at_decision - bb_middle
            profit_potential_raw = price_at_decision - bb_middle_at_decision
        elif is_lower_break: # Long trade, potential is bb_middle - price_at_decision
            profit_potential_raw = bb_middle_at_decision - price_at_decision
        else:
            profit_potential_raw = np.nan
        features['profit_potential'] = profit_potential_raw * 10000 # Convert to pips like in training
    else:
        features['profit_potential'] = np.nan

    # Create DataFrame in the order of model_features
    # Ensure all expected features are present, filling with NaN if not generated
    feature_values_ordered = []
    for feature_name in expected_feature_list:
        feature_values_ordered.append(features.get(feature_name, np.nan))
        
    features_df = pd.DataFrame([feature_values_ordered], columns=expected_feature_list)
    
    # Convert boolean columns to int if any (as done in training)
    for col in features_df.columns:
        if features_df[col].dtype == 'bool':
            features_df[col] = features_df[col].astype(int)
        # Ensure all columns are string type for LightGBM if they were during training
        # (This is usually handled by LightGBM if features are numeric)

    # Check for any NaNs in the final feature set
    if features_df.isnull().values.any():
        print("Warning: NaN values present in features for prediction:")
        print(features_df.isnull().sum())
        return None # Do not proceed if critical features are missing

    return features_df


def get_trade_decision(df_with_indicators: pd.DataFrame, model, model_features: list, pip_location: int, display_precision: int):
    """
    Determines if a trade should be made based on the latest candle data and model prediction.
    Returns: (trade_direction, sl_price_str, tp_price_str) or (None, None, None)
    """
    if len(df_with_indicators) < 2:
        print("Not enough data to check for signals (need at least 2 candles).")
        return None, None, None

    # Signal candle is the one that *just closed* (t-1, which is df.iloc[-1])
    # Features for the model are from this signal candle.
    # Trade entry is at the open of the *current forming* candle (t).
    # SL is based on close[t-1], TP is bb_middle[t-1].
    
    # The prompt's training code: "Signal is based on the close of the *previous* candle (t-1)"
    # "current_candle_series" (for features) is the candle *after* the break signal.
    # So, if candle C-2 breaks, features are from C-1. Trade at C (current).
    
    signal_eval_candle = df_with_indicators.iloc[-2] # Candle t-2 (potential signal)
    feature_extraction_candle = df_with_indicators.iloc[-1] # Candle t-1 (features extracted from here)

    # Check for NaNs in critical fields for signal detection and feature extraction
    critical_cols_signal = ['close', 'bb_upper', 'bb_lower']
    critical_cols_feature = ['close', 'bb_middle'] + model_features # Check all expected features
    
    if signal_eval_candle[critical_cols_signal].isnull().any():
        print(f"NaN values in critical signal fields for candle {signal_eval_candle.name}. Skipping.")
        return None, None, None
    
    # Check for NaNs in feature_extraction_candle for fields needed for SL/TP and features
    # Some features like 'rsi' might be NaN if not enough history, handled in prepare_features_for_prediction
    if feature_extraction_candle[['close', 'bb_middle']].isnull().any():
        print(f"NaN values in critical feature/SL/TP fields for candle {feature_extraction_candle.name}. Skipping.")
        return None, None, None

    is_upper_break = signal_eval_candle['close'] > signal_eval_candle['bb_upper']
    is_lower_break = signal_eval_candle['close'] < signal_eval_candle['bb_lower']

    if (is_upper_break or is_lower_break) and not (is_upper_break and is_lower_break):
        print(f"Bollinger Band break detected on candle {signal_eval_candle.name}: Upper={is_upper_break}, Lower={is_lower_break}")
        
        features_df = prepare_features_for_prediction(feature_extraction_candle, is_upper_break, is_lower_break, model_features)
        
        if features_df is None or features_df.isnull().values.any():
            print("Could not prepare valid features for prediction or NaN found. No trade.")
            return None, None, None

        try:
            prediction = model.predict(features_df)[0] # Get single prediction
            # proba = model.predict_proba(features_df)[0][1] # Probability for positive class
            # print(f"Model prediction: {prediction}, Probability: {proba:.4f}")
            print(f"Model prediction for features from {feature_extraction_candle.name}: {prediction}")
        except Exception as e:
            print(f"Error during model prediction: {e}")
            print("Features DataFrame that caused error:")
            print(features_df.to_string())
            return None, None, None

        if prediction == 1: # Model signals a reversion trade
            entry_price_reference = feature_extraction_candle['close']
            tp_price_raw = feature_extraction_candle['bb_middle']
            
            pip_value = 10**pip_location # e.g., 0.0001 for EUR_USD if pip_location is -4
            sl_offset = SL_PIPS * pip_value

            if is_upper_break: # Signal was close > upper BB, expect reversion (SELL)
                trade_direction = "SELL"
                sl_price_raw = entry_price_reference + sl_offset
            else: # Signal was close < lower BB, expect reversion (BUY)
                trade_direction = "BUY"
                sl_price_raw = entry_price_reference - sl_offset
            
            # Format prices to OANDA's required precision
            # display_precision is the number of decimal places, e.g., 5 for EUR_USD
            # The format string should be f"{price:.{display_precision}f}"
            sl_price_str = f"{sl_price_raw:.{display_precision}f}"
            tp_price_str = f"{tp_price_raw:.{display_precision}f}"

            print(f"Trade Signal: {trade_direction}, SL: {sl_price_str}, TP: {tp_price_str}")
            return trade_direction, sl_price_str, tp_price_str
        else:
            print("Model predicts no trade (prediction != 1).")
            return None, None, None
    else:
        # print(f"No clear Bollinger Band break on {signal_eval_candle.name}.")
        return None, None, None