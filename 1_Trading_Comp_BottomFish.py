import os
import functools
import operator
import itertools
from time import sleep
import signal
import requests
import pandas as pd
import pandas_ta as ta
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

def calc_spread_cushion(order_books_stats):
    bid_vol = order_books_stats['Cumulative Vol Bid']
    ask_vol = order_books_stats['Cumulative Vol Ask']

    reduction_factor = 20
    price_cushion_factor = (bid_vol - ask_vol) / ask_vol / reduction_factor

    return price_cushion_factor

def buy_order(session, ticker, quantity, price, price_cushion):
    buy_param = {'ticker': ticker, 'type': 'LIMIT', 'quantity': quantity, 'action': 'BUY', 'price': price + (price * price_cushion)}
    session.post('http://localhost:9999/v1/orders', params = buy_param)

def sell_order(session, ticker, quantity, price, price_cushion):
    buy_param = {'ticker': ticker, 'type': 'LIMIT', 'quantity': quantity, 'action': 'SELL', 'price': price + (price * price_cushion)}
    session.post('http://localhost:9999/v1/orders', params = buy_param)

# this helper method gets all the orders of a given type (OPEN/TRANSACTED/CANCELLED)
def get_orders(session, status):
    payload = {'status': status}
    resp = session.get('http://localhost:9999/v1/orders', params=payload)
    if resp.status_code == 401:
        raise ApiException('The API key provided in this Python code must match that in the RIT client (please refer to the API hyperlink in the client toolbar and/or the RIT – User Guide – REST API Documentation.pdf)')
    orders = resp.json()
    return orders

# this is the main method containing the actual order routing logic
def main():

    with requests.Session() as s:
        # add the API key to the session to authenticate during requests
        s.headers.update(API_KEY)
        # get the current time of the case
        tick = get_tick(s)
        
        while 5 <= tick <= 300:
            
            orders = get_orders(s, 'OPEN')
                
            if len(orders) < 12:
                # s.post('http://localhost:9999/commands/cancel', params={'all': 1, 'ticker': 'CRZY'})
                # s.post('http://localhost:9999/commands/cancel', params={'all': 1, 'ticker': 'TAME'})
                # s.post('http://localhost:9999/commands/cancel', params={'all': 1, 'ticker': 'BBSN'})

                s.post('http://localhost:9999/v1/orders', params={'ticker': 'CRZY', 'type': 'LIMIT', 'quantity': 5000, 'action': 'SELL', 'price': 35.00})
                s.post('http://localhost:9999/v1/orders', params={'ticker': 'CRZY', 'type': 'LIMIT', 'quantity': 5000, 'action': 'SELL', 'price': 25.00})
                s.post('http://localhost:9999/v1/orders', params={'ticker': 'CRZY', 'type': 'LIMIT', 'quantity': 5000, 'action': 'SELL', 'price': 17.00})
                s.post('http://localhost:9999/v1/orders', params={'ticker': 'CRZY', 'type': 'LIMIT', 'quantity': 5000, 'action': 'SELL', 'price': 15.00})
                s.post('http://localhost:9999/v1/orders', params={'ticker': 'CRZY', 'type': 'LIMIT', 'quantity': 5000, 'action': 'BUY', 'price': 9.00})
                s.post('http://localhost:9999/v1/orders', params={'ticker': 'CRZY', 'type': 'LIMIT', 'quantity': 5000, 'action': 'BUY', 'price': 6.00})
                s.post('http://localhost:9999/v1/orders', params={'ticker': 'CRZY', 'type': 'LIMIT', 'quantity': 5000, 'action': 'BUY', 'price': 3.00})
                s.post('http://localhost:9999/v1/orders', params={'ticker': 'CRZY', 'type': 'LIMIT', 'quantity': 5000, 'action': 'BUY', 'price': 2.00})

                s.post('http://localhost:9999/v1/orders', params={'ticker': 'TAME', 'type': 'LIMIT', 'quantity': 5000, 'action': 'SELL', 'price': 45.00})
                s.post('http://localhost:9999/v1/orders', params={'ticker': 'TAME', 'type': 'LIMIT', 'quantity': 5000, 'action': 'SELL', 'price': 40.00})
                s.post('http://localhost:9999/v1/orders', params={'ticker': 'TAME', 'type': 'LIMIT', 'quantity': 5000, 'action': 'SELL', 'price': 33.00})
                s.post('http://localhost:9999/v1/orders', params={'ticker': 'TAME', 'type': 'LIMIT', 'quantity': 5000, 'action': 'SELL', 'price': 25.00})
                s.post('http://localhost:9999/v1/orders', params={'ticker': 'TAME', 'type': 'LIMIT', 'quantity': 5000, 'action': 'BUY', 'price': 14.00})
                s.post('http://localhost:9999/v1/orders', params={'ticker': 'TAME', 'type': 'LIMIT', 'quantity': 5000, 'action': 'BUY', 'price': 12.00})
                s.post('http://localhost:9999/v1/orders', params={'ticker': 'TAME', 'type': 'LIMIT', 'quantity': 5000, 'action': 'BUY', 'price': 10.00})
                # s.post('http://localhost:9999/v1/orders', params={'ticker': 'TAME', 'type': 'LIMIT', 'quantity': 5000, 'action': 'BUY', 'price': 10.00})

                s.post('http://localhost:9999/v1/orders', params={'ticker': 'BBSN', 'type': 'LIMIT', 'quantity': 5000, 'action': 'SELL', 'price': 100.00})
                s.post('http://localhost:9999/v1/orders', params={'ticker': 'BBSN', 'type': 'LIMIT', 'quantity': 5000, 'action': 'SELL', 'price': 90.00})
                s.post('http://localhost:9999/v1/orders', params={'ticker': 'BBSN', 'type': 'LIMIT', 'quantity': 5000, 'action': 'SELL', 'price': 110.00})
                s.post('http://localhost:9999/v1/orders', params={'ticker': 'BBSN', 'type': 'LIMIT', 'quantity': 5000, 'action': 'SELL', 'price': 95.00})
                s.post('http://localhost:9999/v1/orders', params={'ticker': 'BBSN', 'type': 'LIMIT', 'quantity': 5000, 'action': 'BUY', 'price': 15.00})
                s.post('http://localhost:9999/v1/orders', params={'ticker': 'BBSN', 'type': 'LIMIT', 'quantity': 5000, 'action': 'BUY', 'price': 30.50})
                s.post('http://localhost:9999/v1/orders', params={'ticker': 'BBSN', 'type': 'LIMIT', 'quantity': 5000, 'action': 'BUY', 'price': 55.00})
                s.post('http://localhost:9999/v1/orders', params={'ticker': 'BBSN', 'type': 'LIMIT', 'quantity': 5000, 'action': 'BUY', 'price': 65.50})

                sleep(1)

if __name__ == '__main__':
    signal.signal(signal.SIGINT, signal_handler)
    main()