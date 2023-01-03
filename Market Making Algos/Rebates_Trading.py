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

# this helper method submits a pair of limit orders to buy and sell VOLUME of each security, at the last price +/- SPREAD
# def buy_sell(session, to_buy, to_sell, last):
#     buy_payload = {'ticker': to_buy, 'type': 'LIMIT', 'quantity': BUY_VOLUME, 'action': 'BUY', 'price': last - SPREAD}
#     sell_payload = {'ticker': to_sell, 'type': 'LIMIT', 'quantity': SELL_VOLUME, 'action': 'SELL', 'price': last + SPREAD}
#     session.post('http://localhost:9999/v1/orders', params=buy_payload)
#     session.post('http://localhost:9999/v1/orders', params=sell_payload)

# this function calculates the spread between the algo's bid and ask based on order book depth
def calc_spread_cushion(order_books_stats):
    bid_vol = order_books_stats['Cumulative Vol Bid']
    ask_vol = order_books_stats['Cumulative Vol Ask']

    reduction_factor = 20
    price_cushion_factor = (bid_vol - ask_vol) / ask_vol / reduction_factor

    return price_cushion_factor

# this function submits a buy order
def buy_order(session, ticker, quantity, price, price_cushion):
    buy_param = {'ticker': ticker, 'type': 'LIMIT', 'quantity': quantity, 'action': 'BUY', 'price': price + (price * price_cushion)}
    session.post('http://localhost:9999/v1/orders', params = buy_param)

# this function submits a sell order
def sell_order(session, ticker, quantity, price, price_cushion):
    buy_param = {'ticker': ticker, 'type': 'LIMIT', 'quantity': quantity, 'action': 'SELL', 'price': price + (price * price_cushion)}
    session.post('http://localhost:9999/v1/orders', params = buy_param)

# def get_bid():
#     8

# def get_ask():

# this function fetches the bid and ask prices of a given ticker
def ticker_bid_ask(session, ticker):
    payload = {'ticker': ticker}
    resp = session.get('http://localhost:9999/v1/securities/book', params=payload)
    if resp.ok:
        book = resp.json()
        return [book['bids'][0]['price'], book['asks'][0]['price']]
    raise ApiException('Error getting bid / ask: The API key provided in this Python code must match that in the RIT client') 

# this helper method gets all the orders of a given type (OPEN/TRANSACTED/CANCELLED)
def get_orders(session, status):
    payload = {'status': status}
    resp = session.get('http://localhost:9999/v1/orders', params=payload)
    if resp.status_code == 401:
        raise ApiException('The API key provided in this Python code must match that in the RIT client (please refer to the API hyperlink in the client toolbar and/or the RIT – User Guide – REST API Documentation.pdf)')
    orders = resp.json()
    return orders

# this function calculates a smooth moving average for n periods
def mov_avg(session, price):
    array = []
    array.append(price)

    sum = 0
    sma_period = 12

    for idx, i in reversed(list(enumerate(array))):
        if idx > len(array) - 13:
            sum += i

    mov_avg_num = sum/sma_period

    # ema12 = (array.apply(lambda x: x.ewm(span=12, adjust=False).mean()))

    if len(array) > 12:
        del array[:-11]

    if len(array) > 12:
        del array[:-11]

    return mov_avg_num

# this function liquidates the entire portfolio
def liquidate_portfolio():
    pass

# this function fetches the position size for a given ticker
def get_position(session, ticker):
    positions = session.get('http://localhost:9999/v1/securities', params={'ticker': ticker})
    position = positions.json()[0]['position']
    return position

# this function calculates summary statistic on the order book
def get_order_book_stats(session, ticker, limit):

    orders = session.get('http://localhost:9999/v1/securities/book', params={'ticker': ticker, 'limit': limit})

    bids = orders.json()['bids']
    asks = orders.json()['asks']

    bid_cumulative_volume = 0
    bid_number_of_orders = 0

    ask_cumulative_volume = 0
    ask_number_of_orders = 0

    for i in bids:
        if i['trader_id'] == 'ANON':

            bid_cumulative_volume += 1
            bid_number_of_orders += i['quantity']

        # else:
        #     del bids[i]

    for i in asks:
        if i['trader_id'] == 'ANON':

            ask_cumulative_volume += 1
            ask_number_of_orders += i['quantity']

        # else:
        #     del asks[i]

    dict = {'Cumulative Vol Bid': bid_cumulative_volume,
            'Bid Num of Orders': bid_number_of_orders,
            'Cumulative Vol Ask': ask_cumulative_volume,
            'Ask Num of Orders': ask_number_of_orders,}

    return dict

# this is the main method containing the actual order routing logic
def main():

    with requests.Session() as s:
        # add the API key to the session to authenticate during requests
        s.headers.update(API_KEY)
        # get the current time of the case
        tick = get_tick(s)
        
        while 3 <= tick <= 300:
            tick = get_tick(s)

            # fetch data via API to feed to algorithm
            close = ticker_close(s, 'CNR')
            sma = mov_avg(s, close)
            order_book_stats = get_order_book_stats(s, 'CNR', 100)
            orders = get_orders(s, 'OPEN')
            algo_close = ticker_close(s, 'CNR')
            bid_ask = ticker_bid_ask(s, 'CNR')
            bid = bid_ask[0]
            ask = bid_ask[1]

            position = get_position(s, 'CNR')

            s.post('http://localhost:9999/v1/orders', params={'ticker': 'CNR', 'type': 'LIMIT', 'price': algo_close, 'quantity': 500, 'action': 'SELL'})
            s.post('http://localhost:9999/v1/orders', params={'ticker': 'CNR', 'type': 'LIMIT', 'price': algo_close, 'quantity': 500, 'action': 'BUY'})
            sleep(1)

if __name__ == '__main__':
    signal.signal(signal.SIGINT, signal_handler)
    main()