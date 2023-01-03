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
            bid_ask_A = s.get('http://localhost:9999/v1/securities/book', params={'ticker': 'CRZY_A', 'limit': 1})
            bid_ask_M = s.get('http://localhost:9999/v1/securities/book', params={'ticker': 'CRZY_M', 'limit': 1})

            # parse bid and ask prices
            CRZY_A_bid_price = bid_ask_A.json()['bids'][0]['price']
            CRZY_A_ask_price = bid_ask_A.json()['asks'][0]['price']
            CRZY_M_bid_price = bid_ask_M.json()['bids'][0]['price']
            CRZY_M_ask_price = bid_ask_M.json()['asks'][0]['price']
            
            # parse order quantity
            CRZY_A_bid_quantity_total = bid_ask_A.json()['bids'][0]['quantity']
            CRZY_A_ask_quantity_total = bid_ask_A.json()['asks'][0]['quantity']
            CRZY_M_bid_quantity_total = bid_ask_M.json()['bids'][0]['quantity']
            CRZY_M_ask_quantity_total = bid_ask_M.json()['asks'][0]['quantity']

            # parse order quantity filled
            CRZY_A_bid_quantity_filled = bid_ask_A.json()['bids'][0]['quantity_filled']
            CRZY_A_ask_quantity_filled = bid_ask_A.json()['asks'][0]['quantity_filled']
            CRZY_M_bid_quantity_filled = bid_ask_M.json()['bids'][0]['quantity_filled']
            CRZY_M_ask_quantity_filled = bid_ask_M.json()['asks'][0]['quantity_filled']

            # calcuate amount left to fill
            CRZY_A_bid_quantity = CRZY_A_bid_quantity_total - CRZY_A_bid_quantity_filled
            CRZY_A_ask_quantity = CRZY_A_ask_quantity_total - CRZY_A_ask_quantity_filled
            CRZY_M_bid_quantity = CRZY_M_bid_quantity_total - CRZY_M_bid_quantity_filled
            CRZY_M_ask_quantity = CRZY_M_ask_quantity_total - CRZY_M_ask_quantity_filled

            # quantity decision rule: sets market making order quantity to the minimum quantity between arbitrage trades
            if CRZY_A_bid_quantity > CRZY_M_ask_quantity:
                quantity1 = CRZY_M_ask_quantity
            else:
                quantity1 = CRZY_A_bid_quantity

            if CRZY_M_bid_quantity > CRZY_A_ask_quantity:
                quantity2 = CRZY_A_ask_quantity
            else:
                quantity2 = CRZY_M_bid_quantity

            threshold = .02
            quantity_percent = .5

            # algorithm decision rule: arbitrage between markets
            if CRZY_A_bid_price > CRZY_M_ask_price + threshold:
                # market orders
                s.post('http://localhost:9999/v1/orders', params={'ticker': 'CRZY_M', 'type': 'MARKET', 'quantity': quantity1 * quantity_percent, 'action': 'BUY'})
                s.post('http://localhost:9999/v1/orders', params={'ticker': 'CRZY_A', 'type': 'MARKET', 'quantity': quantity1 * quantity_percent, 'action': 'SELL'})

                sleep(.25)

            if CRZY_M_bid_price > CRZY_A_ask_price + threshold:
                # market orders
                s.post('http://localhost:9999/v1/orders', params={'ticker': 'CRZY_A', 'type': 'MARKET', 'quantity': quantity2 * quantity_percent, 'action': 'BUY'})
                s.post('http://localhost:9999/v1/orders', params={'ticker': 'CRZY_M', 'type': 'MARKET', 'quantity': quantity2 * quantity_percent, 'action': 'SELL'})

                sleep(.25)

            '''
            Ways to Improve:
            - Flatten unfilled limit orders
            - Add minimum spread for market orders
            - Try other HFT strategies
            - Create functions for processes within the algo and add to a HelperFunction() class
            - Send market making orders at a smaller size than limit order size to account for other HFT players
            '''

            # add bottom fishing orders
            # adjust trade position based on length of order book (liqudity trading)

if __name__ == '__main__':
    signal.signal(signal.SIGINT, signal_handler)
    main()