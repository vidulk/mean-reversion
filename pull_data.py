
print(client)
# Define the instrument and granularity
instrument = 'EUR_USD'  # EUR/USD currency pair
granularity = 'M15'  # 15-minute data

all_data = pd.DataFrame()
yest_date = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')

from_date = '2024-06-01'
last_date = yest_date

while last_date <= yest_date:

  params = {
    "granularity": granularity,
    "from":from_date,
    'count':5000
  }

  r = instruments.InstrumentsCandles(instrument=instrument, params=params)

  client.request(r)

  hist_data = pd.DataFrame()

  for candle in r.response['candles']:
      hist_data.at[candle['time'], 'open'] = candle['mid']['o']
      hist_data.at[candle['time'], 'high'] = candle['mid']['h']
      hist_data.at[candle['time'], 'low'] = candle['mid']['l']
      hist_data.at[candle['time'], 'close'] = candle['mid']['c']

  hist_data = hist_data.reset_index()

  # rename index to datetime
  hist_data = hist_data.rename(columns={'index': 'dt'})
  hist_data['dt'] = pd.to_datetime(hist_data['dt'])

  # append to all_data
  all_data = pd.concat([all_data, hist_data], ignore_index=True)

  # get the last date
  last_date = all_data['dt'].max()
  print(last_date)
  from_date = last_date

  try:
    last_date = last_date.strftime('%Y-%m-%d')
    from_date = from_date.strftime('%Y-%m-%d')
  except:
    pass

all_data.to_csv('EURUSD_15min_data.csv', index=False)