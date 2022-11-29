import os
import functools
import operator
import itertools
from time import sleep
import signal
import requests
import pandas as pd
#import pandas_ta as ta
import re
import json

# this class definition allows printing error messages and stopping the program
class ApiException(Exception):
    pass

# this signal handler allows for a graceful shutdown when CTRL+C is pressed
def signal_handler(signum, frame):
    global shutdown
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    shutdown = True

# set your API key to authenticate to the RIT client
API_KEY = {'X-API-Key': 'KZJ94OPT'}
shutdown = False

# this helper method returns the current 'tick' of the running case
def get_tick(session):
    resp = session.get('http://localhost:9999/v1/case')
    if resp.status_code == 401:
        raise ApiException('Error getting tick: The API key provided in this Python code must match that in the RIT client')
    case = resp.json()
    return case['tick']

# this helper method returns the last close price for the given security, one tick ago
def ticker_close(session, ticker):
    payload = {'ticker': ticker, 'limit': 1}
    resp = session.get('http://localhost:9999/v1/securities/history', params=payload)
    if resp.status_code == 401:
        raise ApiException('The API key provided in this Python code must match that in the RIT client (please refer to the API hyperlink in the client toolbar and/or the RIT – User Guide – REST API Documentation.pdf)')
    ticker_history = resp.json()
    if ticker_history:
        return ticker_history[0]['close']
    else:
        raise ApiException('Response error. Unexpected JSON response.')

# this function submits a buy order
def buy_order(session, ticker, quantity, price, price_cushion):
    buy_param = {'ticker': ticker, 'type': 'LIMIT', 'quantity': quantity, 'action': 'BUY', 'price': price + (price * price_cushion)}
    session.post('http://localhost:9999/v1/orders', params = buy_param)

# this function submits a sell order
def sell_order(session, ticker, quantity, price, price_cushion):
    buy_param = {'ticker': ticker, 'type': 'LIMIT', 'quantity': quantity, 'action': 'SELL', 'price': price + (price * price_cushion)}
    session.post('http://localhost:9999/v1/orders', params = buy_param)

# this function liquidates the entire portfolio
def liquidate_portfolio():
    pass

# this function fetches the position size for a given ticker
def get_position(session, ticker):
    positions = session.get('http://localhost:9999/v1/securities', params={'ticker': ticker})
    position = positions.json()[0]['position']
    return position

# this is the main method containing the actual order routing logic
def main():

    with requests.Session() as s:
        # add the API key to the session to authenticate during requests
        s.headers.update(API_KEY)
        t = 'ALGO'
        # get the current time of the case
        tick = get_tick(s)
       
        while 0 <= tick <= 601:
            
            assets = s.get('http://localhost:9999/v1/assets')
            assets = assets.json()

            ak_pipe_price = 0
            nyc_pipe_price = 0

            # get pipeline price
            for i in assets:
                if i['ticker'] == 'AK-CS-PIPE':
                    ak_pipe_price = i['lease_price']
                if i['ticker'] == 'CS-NYC-PIPE':
                    nyc_pipe_price = i['lease_price']

            # get oil prices
            cl_price = ticker_close(s, 'CL')
            cl_ak_price = ticker_close(s, 'CL-AK')
            cl_nyc_price = ticker_close(s, 'CL-NYC')

            get_cl_1f = s.get('http://localhost:9999/v1/securities', params = {'ticker': 'CL-1F'})
            cl_1f_price = get_cl_1f.json()[0]['ask']
            cl_2f_price = ticker_close(s, 'CL-2F')
            print(cl_1f_price)

            if cl_nyc_price > cl_price - nyc_pipe_price:
                
                # RENT STORAGE
                for i in range(5):
                    s.post('http://localhost:9999/v1/leases', params = {'ticker': 'CL-STORAGE', 'from': 'CONTAINER'})
                    sleep(.1)

                # BUY OIL
                s.post('http://localhost:9999/v1/orders', params = {'ticker': 'CL', 'type': 'MARKET', 'quantity': 50, 'action': 'BUY'})

                # BUY FUTURE
                if cl_1f_price > 0:
                    s.post('http://localhost:9999/v1/orders', params = {'ticker': 'CL-1F', 'type': 'MARKET', 'quantity': 50, 'action': 'SELL'})
                else:
                    s.post('http://localhost:9999/v1/orders', params = {'ticker': 'CL-2F', 'type': 'MARKET', 'quantity': 50, 'action': 'SELL'})

                # BUY PIPELINE
                s.post('http://localhost:9999/v1/leases', params = {'ticker': 'CS-NYC-PIPE', 'from': 'PIPELINE'})

                # USE PIPELINE
                leases = s.get('http://localhost:9999/v1/leases')

                pipeline_id = -1

                for i in leases.json():
                    if i['ticker'] == 'CS-NYC-PIPE':
                        pipeline_id = i['id']

                if pipeline_id == -1:
                    s.post('http://localhost:9999/v1/leases', params = {'ticker': 'CS-NYC-PIPE', 'from':'PIPELINE', 'quantity': 50})
                    for i in leases.json():
                        if i['ticker'] == 'CS-NYC-PIPE':
                            pipeline_id = i['id']

                s.post(f'http://localhost:9999/v1/leases/{pipeline_id}?from1=CL&quantity1=50')

                sleep(31)

                # SELL NYC AND FUTURE POSITION

                # cl_nyc = session.get('http://localhost:9999/v1/securities', params = {'ticker': 'CL-NYC'})
                # cl_nyc_position = cl_nyc.json()[0]['position']
                # if cl_nyc_position

                s.post('http://localhost:9999/v1/orders', params = {'ticker': 'CL_NYC', 'type': 'MARKET', 'quantity': 50, 'action': 'SELL'})
                
                cl_1f = s.get('http://localhost:9999/v1/securities', params = {'ticker': 'CL-1F'})
                cl_1f_position = cl_1f.json()[0]['position']
                cl_2f = s.get('http://localhost:9999/v1/securities', params = {'ticker': 'CL-2F'})
                cl_2f_position = cl_2f.json()[0]['position']

                if cl_1f_position > 0:
                    s.post('http://localhost:9999/v1/orders', params = {'ticker': 'CL-1F', 'type': 'MARKET', 'quantity': cl_1f_position, 'action': 'BUY'})
                if cl_2f_position > 0:
                    s.post('http://localhost:9999/v1/orders', params = {'ticker': 'CL-2F', 'type': 'MARKET', 'quantity': cl_2f_position, 'action': 'BUY'})

            if cl_price + 1000000 > cl_ak_price - ak_pipe_price:
                
                # RENT STORAGE
                for i in range(5):
                    s.post('http://localhost:9999/v1/leases', params = {'ticker': 'AK-STORAGE'})
                    sleep(.1)

                # BUY OIL
                s.post('http://localhost:9999/v1/orders', params = {'ticker': 'CL-AK', 'type': 'MARKET', 'quantity': 50, 'action': 'BUY'})

                # BUY FUTURE
                if cl_1f_price > 0:
                    s.post('http://localhost:9999/v1/orders', params = {'ticker': 'CL-1F', 'type': 'MARKET', 'quantity': 50, 'action': 'SELL'})
                else:
                    s.post('http://localhost:9999/v1/orders', params = {'ticker': 'CL-2F', 'type': 'MARKET', 'quantity': 50, 'action': 'SELL'})

                # BUY PIPELINE
                s.post('http://localhost:9999/v1/leases', params = {'ticker': 'AK-CS-PIPE', 'from': 'PIPELINE'})

                # USE PIPELINE
                leases = s.get('http://localhost:9999/v1/leases')

                pipeline_id = -1

                for i in leases.json():
                    if i['ticker'] == 'AK-CS-PIPE':
                        pipeline_id = i['id']

                if pipeline_id == -1:
                    s.post('http://localhost:9999/v1/leases', params = {'ticker': 'AK-CS-PIPE', 'from':'PIPELINE', 'quantity': 50})
                    for i in leases.json():
                        if i['ticker'] == 'AK-CS-PIPE':
                            pipeline_id = i['id']

                s.post(f'http://localhost:9999/v1/leases/{pipeline_id}?from1=CL&quantity1=50')

                sleep(31)

                # SELL NYC AND FUTURE POSITION

                # cl_nyc = session.get('http://localhost:9999/v1/securities', params = {'ticker': 'CL-NYC'})
                # cl_nyc_position = cl_nyc.json()[0]['position']
                # if cl_nyc_position

                s.post('http://localhost:9999/v1/orders', params = {'ticker': 'CL', 'type': 'MARKET', 'quantity': 50, 'action': 'SELL'})
                
                cl_1f = s.get('http://localhost:9999/v1/securities', params = {'ticker': 'CL-1F'})
                cl_1f_position = cl_1f.json()[0]['position']
                cl_2f = s.get('http://localhost:9999/v1/securities', params = {'ticker': 'CL-2F'})
                cl_2f_position = cl_2f.json()[0]['position']

                if cl_1f_position > 0:
                    s.post('http://localhost:9999/v1/orders', params = {'ticker': 'CL-1F', 'type': 'MARKET', 'quantity': cl_1f_position, 'action': 'BUY'})
                if cl_2f_position > 0:
                    s.post('http://localhost:9999/v1/orders', params = {'ticker': 'CL-2F', 'type': 'MARKET', 'quantity': cl_2f_position, 'action': 'BUY'})

if __name__ == '__main__':
    signal.signal(signal.SIGINT, signal_handler)
    main()