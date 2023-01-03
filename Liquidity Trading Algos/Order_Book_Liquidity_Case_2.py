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

# this helper method gets all the orders of a given type (OPEN/TRANSACTED/CANCELLED)
def get_orders(session, status):
    payload = {'status': status}
    resp = session.get('http://localhost:9999/v1/orders', params=payload)
    if resp.status_code == 401:
        raise ApiException('The API key provided in this Python code must match that in the RIT client (please refer to the API hyperlink in the client toolbar and/or the RIT – User Guide – REST API Documentation.pdf)')
    orders = resp.json()
    return orders

# this helper method returns the bid and ask for a given security
def ticker_bid_ask(session, ticker):
    payload = {'ticker': ticker}
    resp = session.get('http://localhost:9999/v1/securities/book', params=payload)
    if resp.ok:
        book = resp.json()
        return book['bids'][0]['price'], book['asks'][0]['price']
    raise ApiException('Error getting bid / ask: The API key provided in this Python code must match that in the RIT client')

# this is the main method containing the actual order routing logic
def main():
    
    with requests.Session() as s:
        # add the API key to the session to authenticate during requests
        s.headers.update(API_KEY)
        # get the current time of the case
        tick = get_tick(s)
        
        while 3 <= tick <= 300:
            tick = get_tick(s)

            # get the current bid and ask for the security
            orders = get_orders(s, 'OPEN')
            
            # submit orders if there are less than 32 open orders
            # these orders are placed at key locations to provide liquidity at a premium when it dries up
            if len(orders) < 32:

                s.post('http://localhost:9999/v1/orders', params={'ticker': 'CRZY_A', 'type': 'LIMIT', 'quantity': 5000, 'action': 'SELL', 'price': 18.00})
                s.post('http://localhost:9999/v1/orders', params={'ticker': 'CRZY_A', 'type': 'LIMIT', 'quantity': 5000, 'action': 'SELL', 'price': 24.00})
                s.post('http://localhost:9999/v1/orders', params={'ticker': 'CRZY_A', 'type': 'LIMIT', 'quantity': 5000, 'action': 'SELL', 'price': 35.00})
                s.post('http://localhost:9999/v1/orders', params={'ticker': 'CRZY_A', 'type': 'LIMIT', 'quantity': 5000, 'action': 'SELL', 'price': 45.00})
                s.post('http://localhost:9999/v1/orders', params={'ticker': 'CRZY_M', 'type': 'LIMIT', 'quantity': 5000, 'action': 'SELL', 'price': 18.00})
                s.post('http://localhost:9999/v1/orders', params={'ticker': 'CRZY_M', 'type': 'LIMIT', 'quantity': 5000, 'action': 'SELL', 'price': 24.00})
                s.post('http://localhost:9999/v1/orders', params={'ticker': 'CRZY_M', 'type': 'LIMIT', 'quantity': 5000, 'action': 'SELL', 'price': 35.00})
                s.post('http://localhost:9999/v1/orders', params={'ticker': 'CRZY_M', 'type': 'LIMIT', 'quantity': 5000, 'action': 'SELL', 'price': 45.00})

                s.post('http://localhost:9999/v1/orders', params={'ticker': 'CRZY_M', 'type': 'LIMIT', 'quantity': 5000, 'action': 'BUY', 'price': 10.00})
                s.post('http://localhost:9999/v1/orders', params={'ticker': 'CRZY_M', 'type': 'LIMIT', 'quantity': 5000, 'action': 'BUY', 'price': 9.00})
                s.post('http://localhost:9999/v1/orders', params={'ticker': 'CRZY_M', 'type': 'LIMIT', 'quantity': 5000, 'action': 'BUY', 'price': 4.00})
                s.post('http://localhost:9999/v1/orders', params={'ticker': 'CRZY_M', 'type': 'LIMIT', 'quantity': 5000, 'action': 'BUY', 'price': 2.00})
                s.post('http://localhost:9999/v1/orders', params={'ticker': 'CRZY_A', 'type': 'LIMIT', 'quantity': 5000, 'action': 'BUY', 'price': 10.00})
                s.post('http://localhost:9999/v1/orders', params={'ticker': 'CRZY_A', 'type': 'LIMIT', 'quantity': 5000, 'action': 'BUY', 'price': 9.00})
                s.post('http://localhost:9999/v1/orders', params={'ticker': 'CRZY_A', 'type': 'LIMIT', 'quantity': 5000, 'action': 'BUY', 'price': 4.00})
                s.post('http://localhost:9999/v1/orders', params={'ticker': 'CRZY_A', 'type': 'LIMIT', 'quantity': 5000, 'action': 'BUY', 'price': 2.00})
                
                s.post('http://localhost:9999/v1/orders', params={'ticker': 'TAME_A', 'type': 'LIMIT', 'quantity': 5000, 'action': 'SELL', 'price': 30.00})
                s.post('http://localhost:9999/v1/orders', params={'ticker': 'TAME_A', 'type': 'LIMIT', 'quantity': 5000, 'action': 'SELL', 'price': 35.00})
                s.post('http://localhost:9999/v1/orders', params={'ticker': 'TAME_A', 'type': 'LIMIT', 'quantity': 5000, 'action': 'SELL', 'price': 85.00})
                s.post('http://localhost:9999/v1/orders', params={'ticker': 'TAME_A', 'type': 'LIMIT', 'quantity': 5000, 'action': 'SELL', 'price': 100.00})
                s.post('http://localhost:9999/v1/orders', params={'ticker': 'TAME_M', 'type': 'LIMIT', 'quantity': 5000, 'action': 'SELL', 'price': 30.00})
                s.post('http://localhost:9999/v1/orders', params={'ticker': 'TAME_M', 'type': 'LIMIT', 'quantity': 5000, 'action': 'SELL', 'price': 35.00})
                s.post('http://localhost:9999/v1/orders', params={'ticker': 'TAME_M', 'type': 'LIMIT', 'quantity': 5000, 'action': 'SELL', 'price': 85.00})
                s.post('http://localhost:9999/v1/orders', params={'ticker': 'TAME_M', 'type': 'LIMIT', 'quantity': 5000, 'action': 'SELL', 'price': 100.00})

                s.post('http://localhost:9999/v1/orders', params={'ticker': 'TAME_A', 'type': 'LIMIT', 'quantity': 5000, 'action': 'BUY', 'price': 21.00})
                s.post('http://localhost:9999/v1/orders', params={'ticker': 'TAME_A', 'type': 'LIMIT', 'quantity': 5000, 'action': 'BUY', 'price': 18.00})
                s.post('http://localhost:9999/v1/orders', params={'ticker': 'TAME_A', 'type': 'LIMIT', 'quantity': 5000, 'action': 'BUY', 'price': 6.00})
                s.post('http://localhost:9999/v1/orders', params={'ticker': 'TAME_A', 'type': 'LIMIT', 'quantity': 5000, 'action': 'BUY', 'price': 9.00})
                s.post('http://localhost:9999/v1/orders', params={'ticker': 'TAME_M', 'type': 'LIMIT', 'quantity': 5000, 'action': 'BUY', 'price': 21.00})
                s.post('http://localhost:9999/v1/orders', params={'ticker': 'TAME_M', 'type': 'LIMIT', 'quantity': 5000, 'action': 'BUY', 'price': 6.00})
                s.post('http://localhost:9999/v1/orders', params={'ticker': 'TAME_M', 'type': 'LIMIT', 'quantity': 5000, 'action': 'BUY', 'price': 21.00})
                s.post('http://localhost:9999/v1/orders', params={'ticker': 'TAME_M', 'type': 'LIMIT', 'quantity': 5000, 'action': 'BUY', 'price': 9.00})

if __name__ == '__main__':
    signal.signal(signal.SIGINT, signal_handler)
    main()