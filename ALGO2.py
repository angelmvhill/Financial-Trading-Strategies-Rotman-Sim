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
            close = ticker_close(s, 'ALGO')
            sma = mov_avg(s, close)
            order_book_stats = get_order_book_stats(s, 'ALGO', 100)
            orders = get_orders(s, 'OPEN')
            algo_close = ticker_close(s, 'ALGO')

            # check if you have 0 open orders
            if len(orders) == 0:
                bid_ask = ticker_bid_ask(s, 'ALGO')
                print(bid_ask)

                price_factor = calc_spread_cushion(get_order_book_stats(s, 'ALGO', 100))

                # submit a pair of orders biased towards the long side if liquidity is stronger on the buy side
                if price_factor >= 0:
                    sell_order(s, 'ALGO', 2000, bid_ask[1] + .02, 0)
                    buy_order(s, 'ALGO', 2000, bid_ask[0] - .02, price_factor)
                    orders = get_orders(s, 'OPEN')
                    print(orders)
                    sleep(.25)

                # submit a pair of orders biased towards the sell side if liquidity is stronger on the sell side
                if price_factor < 0:
                    sell_order(s, 'ALGO', 2000, bid_ask[1] + .02, price_factor)
                    buy_order(s, 'ALGO', 2000, bid_ask[0] - .02, 0)
                    orders = get_orders(s, 'OPEN')
                    print(orders)
                    sleep(1)

            # check if you don't have a pair of open orders
            # if len(orders) != 2 and len(orders) > 0:
            #     # submit a POST request to the order cancellation endpoint to cancel all open orders
            #     sleep(7.5)
            #     s.post('http://localhost:9999/v1/commands/cancel?all=1')
            #     s.post


            # if len(orders) == 2:
                
                
            #     if orders

            # newest strategy

            # use order book to determine buy or sell price
            # always update bid/ask price on our end, but if liquidity dries up on one end
            # if price trends up, try both decreasing bid price and raising ask price in both scenarios


            # print(f'sma {sma} close {close} order book {order_book_stats}')
            # sleep(.25)

            # new strategy
            '''
            Tools needed: SMA or EMA, volatility, entire order book
            
            # calculate EMA
            send get request to get price
            log price in an array or list
            calculate rolling calculation of the list
            to save memory, remove old price data
            OR
            simply use EMA/SMA function on an object of the current price
            make sure to log these anyways to make sure the calculation is correct

            # calculate order book
            get request for entire order book
            filter out non ANON orders


            if volatility < threshold: # trade # we may want to add the volatility parameter to just the market making part
                if EMA > threshold1 # buy
                    filter order book and calculate total orders to determine trade size
                    also calculate volatility to determine risk and trade size
                if EMA < threshold2: # sell
                    filter order book and calculate total orders to determine trade size
                    also calculate volatility to determine risk and trade size
                if threshold3 > EMA > threshold4: # market make
                    constantly resend orders and cancel to be at the top of the bid/ask spread
                    once a buy or sell fills, halt the buy or sell until the opposing trade is filled
                if price > bollingerband threshold: # sell
                    shift position to be more on the short side depending on the st dev
                    can we calculate this not using OHLC
                    do we need to store a df? or can we just use api request objects
                if price < bollingerband threshold: # buy
                    shift position to be more on the long side depending on the st dev
                    
            obtain orders placed so we can cancel them
                send a request to get orders
                cancel oldest order(s)

            '''


            # add bottom fishing orders
            # adjust trade position based on length of order book (liqudity trading)

if __name__ == '__main__':
    signal.signal(signal.SIGINT, signal_handler)
    main()