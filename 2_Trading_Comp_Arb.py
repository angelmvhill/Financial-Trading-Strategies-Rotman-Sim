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

            # request 1st limit order on order book
            bid_ask_CRZY_A = s.get('http://localhost:9999/v1/securities/book', params={'ticker': 'CRZY_A', 'limit': 1})
            bid_ask_CRZY_M = s.get('http://localhost:9999/v1/securities/book', params={'ticker': 'CRZY_M', 'limit': 1})
            bid_ask_TAME_A = s.get('http://localhost:9999/v1/securities/book', params={'ticker': 'TAME_A', 'limit': 1})
            bid_ask_TAME_M = s.get('http://localhost:9999/v1/securities/book', params={'ticker': 'TAME_M', 'limit': 1})

            # parse bid and ask prices to get arbitraging price
            CRZY_A_bid_price = bid_ask_CRZY_A.json()['bids'][0]['price']
            CRZY_A_ask_price = bid_ask_CRZY_A.json()['asks'][0]['price']
            CRZY_M_bid_price = bid_ask_CRZY_M.json()['bids'][0]['price']
            CRZY_M_ask_price = bid_ask_CRZY_M.json()['asks'][0]['price']
            TAME_A_bid_price = bid_ask_TAME_A.json()['bids'][0]['price']
            TAME_A_ask_price = bid_ask_TAME_A.json()['asks'][0]['price']
            TAME_M_bid_price = bid_ask_TAME_M.json()['bids'][0]['price']
            TAME_M_ask_price = bid_ask_TAME_M.json()['asks'][0]['price']

            # check for arbitraging opportunity
            # if CRZY_A_bid_price - CRZY_M_bid_price < .1 and CRZY_M_ask_price - CRZY_A_bid_price < .1:
            if CRZY_A_ask_price + .08 < CRZY_M_bid_price and CRZY_M_ask_price + .03 > CRZY_A_bid_price:
                s.post('http://localhost:9999/v1/orders', params={'ticker': 'CRZY_A', 'type': 'MARKET', 'quantity': 250, 'action': 'BUY'})
                s.post('http://localhost:9999/v1/orders', params={'ticker': 'CRZY_M', 'type': 'MARKET', 'quantity': 250, 'action': 'SELL'})
            if CRZY_M_ask_price + .08 < CRZY_A_bid_price and CRZY_A_ask_price + .03 > CRZY_M_bid_price:
                s.post('http://localhost:9999/v1/orders', params={'ticker': 'CRZY_M', 'type': 'MARKET', 'quantity': 250, 'action': 'BUY'})
                s.post('http://localhost:9999/v1/orders', params={'ticker': 'CRZY_A', 'type': 'MARKET', 'quantity': 250, 'action': 'SELL'})

            # if TAME_A_bid_price - TAME_M_bid_price < .?1 and TAME_M_ask_price - TAME_A_bid_price < .1:
            if TAME_A_ask_price + .08 < TAME_M_bid_price and TAME_M_ask_price + .03 > TAME_A_bid_price:
                s.post('http://localhost:9999/v1/orders', params={'ticker': 'TAME_A', 'type': 'MARKET', 'quantity': 250, 'action': 'BUY'})
                s.post('http://localhost:9999/v1/orders', params={'ticker': 'TAME_M', 'type': 'MARKET', 'quantity': 250, 'action': 'SELL'})
            if TAME_M_ask_price + .08 < TAME_A_bid_price and TAME_A_ask_price + .03 > TAME_M_bid_price:
                s.post('http://localhost:9999/v1/orders', params={'ticker': 'TAME_M', 'type': 'MARKET', 'quantity': 250, 'action': 'BUY'})
                s.post('http://localhost:9999/v1/orders', params={'ticker': 'TAME_A', 'type': 'MARKET', 'quantity': 250, 'action': 'SELL'})

            # if CRZY_A_bid_price - CRZY_M_bid_price > .1 or CRZY_M_ask_price - CRZY_A_bid_price > .1:
            # if CRZY_A_ask_price + .02 < CRZY_M_bid_price:
            #     s.post('http://localhost:9999/v1/orders', params={'ticker': 'CRZY_A', 'type': 'LIMIT', 'price': CRZY_A_ask_price, 'quantity': 1000, 'action': 'BUY'})
            #     s.post('http://localhost:9999/v1/orders', params={'ticker': 'CRZY_M', 'type': 'LIMIT', 'price': CRZY_M_bid_price, 'quantity': 1000, 'action': 'SELL'})
            # if CRZY_M_ask_price + .02 < CRZY_A_bid_price:
            #     s.post('http://localhost:9999/v1/orders', params={'ticker': 'CRZY_M', 'type': 'LIMIT', 'price': CRZY_M_ask_price, 'quantity': 1000, 'action': 'BUY'})
            #     s.post('http://localhost:9999/v1/orders', params={'ticker': 'CRZY_A', 'type': 'LIMIT', 'price': CRZY_A_bid_price, 'quantity': 1000, 'action': 'SELL'})
                
            # # if TAME_A_bid_price - TAME_M_bid_price > .1 or TAME_M_ask_price - TAME_A_bid_price > .1:
            # if TAME_A_ask_price + .02 < TAME_M_bid_price:
            #     s.post('http://localhost:9999/v1/orders', params={'ticker': 'TAME_A', 'type': 'LIMIT', 'price': TAME_A_ask_price, 'quantity': 1000, 'action': 'BUY'})
            #     s.post('http://localhost:9999/v1/orders', params={'ticker': 'TAME_M', 'type': 'LIMIT', 'price': TAME_M_bid_price, 'quantity': 1000, 'action': 'SELL'})
            # if TAME_M_ask_price + .02 < TAME_A_bid_price:
            #     s.post('http://localhost:9999/v1/orders', params={'ticker': 'TAME_M', 'type': 'LIMIT', 'price': TAME_M_ask_price, 'quantity': 1000, 'action': 'BUY'})
            #     s.post('http://localhost:9999/v1/orders', params={'ticker': 'TAME_A', 'type': 'LIMIT', 'price': TAME_A_bid_price, 'quantity': 1000, 'action': 'SELL'})

            orders = get_orders(s, 'OPEN')
            
            if len(orders) < 32:
                # s.post('http://localhost:9999/commands/cancel', params={'all': 1, 'ticker': 'CRZY_A'})
                # s.post('http://localhost:9999/commands/cancel', params={'all': 1, 'ticker': 'CRZY_M'})
                # s.post('http://localhost:9999/commands/cancel', params={'all': 1, 'ticker': 'TAME_A'})
                # s.post('http://localhost:9999/commands/cancel', params={'all': 1, 'ticker': 'TAME_M'})

                s.post('http://localhost:9999/v1/orders', params={'ticker': 'CRZY_A', 'type': 'LIMIT', 'quantity': 5000, 'action': 'SELL', 'price': 26.00})
                s.post('http://localhost:9999/v1/orders', params={'ticker': 'CRZY_A', 'type': 'LIMIT', 'quantity': 5000, 'action': 'SELL', 'price': 22.00})
                s.post('http://localhost:9999/v1/orders', params={'ticker': 'CRZY_A', 'type': 'LIMIT', 'quantity': 5000, 'action': 'SELL', 'price': 35.00})
                s.post('http://localhost:9999/v1/orders', params={'ticker': 'CRZY_A', 'type': 'LIMIT', 'quantity': 5000, 'action': 'SELL', 'price': 45.00})
                s.post('http://localhost:9999/v1/orders', params={'ticker': 'CRZY_M', 'type': 'LIMIT', 'quantity': 5000, 'action': 'SELL', 'price': 26.00})
                s.post('http://localhost:9999/v1/orders', params={'ticker': 'CRZY_M', 'type': 'LIMIT', 'quantity': 5000, 'action': 'SELL', 'price': 22.00})
                s.post('http://localhost:9999/v1/orders', params={'ticker': 'CRZY_M', 'type': 'LIMIT', 'quantity': 5000, 'action': 'SELL', 'price': 35.00})
                s.post('http://localhost:9999/v1/orders', params={'ticker': 'CRZY_M', 'type': 'LIMIT', 'quantity': 5000, 'action': 'SELL', 'price': 45.00})

                s.post('http://localhost:9999/v1/orders', params={'ticker': 'CRZY_M', 'type': 'LIMIT', 'quantity': 5000, 'action': 'BUY', 'price': 8.00})
                s.post('http://localhost:9999/v1/orders', params={'ticker': 'CRZY_M', 'type': 'LIMIT', 'quantity': 5000, 'action': 'BUY', 'price': 6.00})
                s.post('http://localhost:9999/v1/orders', params={'ticker': 'CRZY_M', 'type': 'LIMIT', 'quantity': 5000, 'action': 'BUY', 'price': 4.00})
                s.post('http://localhost:9999/v1/orders', params={'ticker': 'CRZY_M', 'type': 'LIMIT', 'quantity': 5000, 'action': 'BUY', 'price': 2.00})
                s.post('http://localhost:9999/v1/orders', params={'ticker': 'CRZY_A', 'type': 'LIMIT', 'quantity': 5000, 'action': 'BUY', 'price': 8.00})
                s.post('http://localhost:9999/v1/orders', params={'ticker': 'CRZY_A', 'type': 'LIMIT', 'quantity': 5000, 'action': 'BUY', 'price': 6.00})
                s.post('http://localhost:9999/v1/orders', params={'ticker': 'CRZY_A', 'type': 'LIMIT', 'quantity': 5000, 'action': 'BUY', 'price': 4.00})
                s.post('http://localhost:9999/v1/orders', params={'ticker': 'CRZY_A', 'type': 'LIMIT', 'quantity': 5000, 'action': 'BUY', 'price': 2.00})
                
                s.post('http://localhost:9999/v1/orders', params={'ticker': 'TAME_A', 'type': 'LIMIT', 'quantity': 5000, 'action': 'SELL', 'price': 35.00})
                s.post('http://localhost:9999/v1/orders', params={'ticker': 'TAME_A', 'type': 'LIMIT', 'quantity': 5000, 'action': 'SELL', 'price': 38.00})
                s.post('http://localhost:9999/v1/orders', params={'ticker': 'TAME_A', 'type': 'LIMIT', 'quantity': 5000, 'action': 'SELL', 'price': 85.00})
                s.post('http://localhost:9999/v1/orders', params={'ticker': 'TAME_A', 'type': 'LIMIT', 'quantity': 5000, 'action': 'SELL', 'price': 100.00})
                s.post('http://localhost:9999/v1/orders', params={'ticker': 'TAME_M', 'type': 'LIMIT', 'quantity': 5000, 'action': 'SELL', 'price': 35.00})
                s.post('http://localhost:9999/v1/orders', params={'ticker': 'TAME_M', 'type': 'LIMIT', 'quantity': 5000, 'action': 'SELL', 'price': 38.00})
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