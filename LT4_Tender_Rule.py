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
    
    # creates a session to manage connections and requests to the RIT Client
    with requests.Session() as s:
        # add the API key to the session to authenticate during requests
        s.headers.update(API_KEY)
        # get the current time of the case
        tick = get_tick(s)
        
        while tick <= 300:
            tick = get_tick(s)

            # RETRIVE AND PARSE DATA

            # retrieve tender information
            tender_dict = s.get('http://localhost:9999/v1/tenders')

            # convert tender information into json object to be parsed
            tender_json = tender_dict.json()

            # create slicing objects to parse tender json output
            slice_obj1 = slice(6, 7)
            order_quantity = tender_json[slice_obj1]

            slice_obj2 = slice(7, 8)
            action = tender_json[slice_obj2]
            
            slice_obj3 = slice(9, 10)
            price = tender_json[slice_obj3]
            
            # request caption to obtain ticker since it cannot be directly referenced
            slice_obj4 = slice(4, 5)
            caption = tender_json[slice_obj4]
            # convert list to string
            ticker = ''.join(caption)

            # parse string caption to obtain ticker
            ticker = ticker.partition("of ")[2].partition("to ")[0]
            
            slice_obj5 = slice(1, 2)
            order_id = tender_json[slice_obj5]

            # request bid/ask data for CRZY
            if ticker == 'CRZY_A' or 'CRZY_M':
                ticker_A = 'CRZY_A'
                ticker_M = 'CRZY_M'

                bid_ask_A = s.get('http://localhost:9999/v1/securities/book', params={'ticker': ticker_A, 'limit': 1})
                bid_ask_M = s.get('http://localhost:9999/v1/securities/book', params={'ticker': ticker_M, 'limit': 1})

                bid_ask_A = bid_ask_A.json()
                bid_ask_M = bid_ask_M.json()

                # bid_ask_A = json.load(bid_ask_A)
                # bid_ask_M = json.load(bid_ask_M)

                # bid_A = bid_ask_A['bid']['price']
                # bid_M = bid_ask_M['ask']['price']
                # ask_A = bid_ask_A['bid']['price']
                # ask_M = bid_ask_M['ask']['price']

                # bid_A = bid_ask_A[slice_bid][slice_bid_price]
                # bid_M = bid_ask_M[slice_bid][slice_bid_price]
                # ask_A = bid_ask_A[slice_ask][slice_ask_price]
                # ask_M = bid_ask_M[slice_ask][slice_ask_price]

                # slice_bid = slice(1, 2)
                # slice_bid_price = slice(9, 10)
                # slice_ask = slice(2, 2)
                # slice_ask_price = slice(9, 10)

                # parse alternate market bid / ask data to get bid price
                for i, item in enumerate(bid_ask_A.items()):
                    if i == 0:
                        bid_A = i
                
                # parse alternate market bid / ask data to get ask price
                for i, item in enumerate(bid_ask_A.items()):
                    if i == 1:
                        ask_A = i

                # parse primary market bid / ask data to get bid price
                for i, item in enumerate(bid_ask_M.items()):
                    if i == 0:
                        bid_M = i
                
                # parse primary market bid / ask data to get ask price
                for i, item in enumerate(bid_ask_M.items()):
                    if i == 1:
                        ask_M = i

            # request bid/ask data for TAME
            if ticker == 'TAME_A' or 'TAME_M':
                ticker_A = 'TAME_A'
                ticker_M = 'TAME_M'

                bid_ask_A = s.get('http://localhost:9999/v1/securities/book', params={'ticker': ticker_A, 'limit': 1})
                bid_ask_M = s.get('http://localhost:9999/v1/securities/book', params={'ticker': ticker_M, 'limit': 1})

                # bid_A = bid_ask_A['bid']['price']
                # bid_M = bid_ask_M['ask']['price']
                # ask_A = bid_ask_A['bid']['price']
                # ask_M = bid_ask_M['ask']['price']

                bid_ask_A = bid_ask_A.json()
                bid_ask_M = bid_ask_M.json()

                # parse alternate market bid / ask data to get bid price
                for i, item in enumerate(bid_ask_A.items()):
                    if i == 0:
                        bid_A = i
                                
                # parse alternate market bid / ask data to get ask price
                for i, item in enumerate(bid_ask_A.items()):
                    if i == 1:
                        ask_A = i

                # parse primary market bid / ask data to get bid price
                for i, item in enumerate(bid_ask_M.items()):
                    if i == 0:
                        bid_M = i

                # parse primary market bid / ask data to get ask price
                for i, item in enumerate(bid_ask_M.items()):
                    if i == 1:
                        ask_M = i

            # TRADING RULE

            # trading strategy for buying
            if action == 'BUY':

                # fees
                primary_mkt_fee = -0.02
                alt_mkt_fee = 0.005

                # trading rule: minimum profit 1% margin on purchase / sale including fees to accept tender
                if ticker * 0.01 <= (bid_A - price + alt_mkt_fee) or ticker * 0.01 <= (bid_M - price + primary_mkt_fee):
                    
                    # accept tender order if 1% margin is exceeded or met
                    # s.post('http://localhost:9999/v1/tenders/{order_id}', params={'id': 'order_id'})
                    s.post('http://localhost:9999/v1/tenders', params={'id': tender_dict['tender_id']})

                    # request share quantity in portfolio for ticker
                    portfolio = s.get('http://localhost:9999/v1/assets/history', params={'ticker': ticker})
                    shares = portfolio.get('quantity')

                    # selling strategy
                    while shares != 0:
                        
                        # sell orders for CRZY
                        if ticker == 'CRZY_A' or 'CRZY_M':

                            # if alt market offers a better price (including fees), sell at bid price for liquidity
                            if bid_A + alt_mkt_fee >= bid_M + primary_mkt_fee:
                                s.post('http://localhost:9999/v1/orders', params={'ticker': 'CRZY_A', 'type': 'LIMIT', 'quantity': 2000, 'price': bid_A, 'action': 'SELL'})
                            else:
                                # if primary market has a better (including fees), sell at the bid price for liquidity
                                s.post('http://localhost:9999/v1/orders', params={'ticker': 'CRZY_M', 'type': 'LIMIT', 'quantity': 2000, 'price': bid_M, 'action': 'SELL'})

                            # get number of shares in portfolio to determine if position is flattened (or reversed)
                            portfolo = s.get('http://localhost:9999/v1/assets/history', params={'ticker': ticker})
                            shares = portfolio.get('quantity')

                            # if position is reversed (excess shares are sold), flatten position
                            if shares < 0:
                                s.post('http://localhost:9999/v1/orders', params={'ticker': 'CRZY_M', 'type': 'MARKET', 'quantity': shares, 'action': 'BUY'})
                                return
                                
                            # stop selling if all shares are sold
                            if shares == 0:
                                return

                            else:
                                pass
                        
                        # sell orders for TAME
                        if ticker == 'TAME_A' or 'TAME_M':

                            # if alt market offers a better price (including fees), sell at bid price for liquidity
                            if bid_A + alt_mkt_fee >= bid_M + primary_mkt_fee:
                                s.post('http://localhost:9999/v1/orders', params={'ticker': 'TAME_A', 'type': 'LIMIT', 'quantity': 2000, 'price': bid_A, 'action': 'SELL'})
                            else:
                                # if primary market has a better (including fees), sell at the bid price for liquidity
                                s.post('http://localhost:9999/v1/orders', params={'ticker': 'TAME_M', 'type': 'LIMIT', 'quantity': 2000, 'price': bid_M, 'action': 'SELL'})

                            # get number of shares in portfolio to determine if position is flattened (or reversed)
                            portfolio = s.get('http://localhost:9999/v1/assets/history', params={'ticker': ticker})
                            shares = portfolio.get('quantity')

                            # if position is reversed (excess shares are sold), flatten position
                            if shares < 0:
                                s.post('http://localhost:9999/v1/orders', params={'ticker': 'TAME_M', 'type': 'MARKET', 'quantity': shares, 'action': 'BUY'})
                                return
                                
                            # stop selling if all shares are sold
                            if shares == 0:
                                return

                            else:
                                pass

            # trading strategy for shorting
            if action == 'SELL':

                # fees
                primary_mkt_fee = -0.02
                alt_mkt_fee = 0.005

                # trading rule: minimum 1% profit margin on purchase / sale including fees to accept tender
                if ticker * 0.01 <= (price - ask_A + alt_mkt_fee) or ticker * 0.01 <= (price - ask_M + primary_mkt_fee):
                    
                    # accept tender order if 1% margin is exceeded or met
                    s.post('http://localhost:9999/v1/tenders/{order_id}', params={'id': 'order_id'})
                    
                    # request share quantity in portfolio for ticker
                    portfolio = s.get('http://localhost:9999/v1/assets/history', params={'ticker': ticker})
                    shares = portfolio.get('quantity')

                    # buyback strategy
                    while shares != 0:
                        
                        # sell orders for CRZY
                        if ticker == 'CRZY_A' or 'CRZY_M':

                            # if alt market offers a better price (including fees), buy at ask price for liquidity
                            if ask_A + alt_mkt_fee <= ask_M + primary_mkt_fee:
                                s.post('http://localhost:9999/v1/orders', params={'ticker': 'CRZY_A', 'type': 'LIMIT', 'quantity': 2000, 'price': bid_A, 'action': 'BUY'})
                            else:
                                # if primary market has a better (including fees), buy at the ask price for liquidity
                                s.post('http://localhost:9999/v1/orders', params={'ticker': 'CRZY_M', 'type': 'LIMIT', 'quantity': 2000, 'price': bid_M, 'action': 'BUY'})

                            # get number of shares in portfolio to determine if position is flattened (or reversed)
                            portfolio = s.get('http://localhost:9999/v1/assets/history', params={'ticker': ticker})
                            shares = portfolio.get('quantity')

                            # if position is reversed (excess shares are bought), flatten position
                            if shares < 0:
                                s.post('http://localhost:9999/v1/orders', params={'ticker': 'CRZY_M', 'type': 'MARKET', 'quantity': shares, 'action': 'SELL'})
                                return
                                
                            # stop buying if all shares are bought back
                            if shares == 0:
                                return

                            else:
                                pass
                        
                        # sell orders for TAME
                        if ticker == 'TAME_A' or 'TAME_M':

                            # if alt market offers a better price (including fees), buy at ask price for liquidity
                            if bid_A + alt_mkt_fee <= bid_M + primary_mkt_fee:
                                s.post('http://localhost:9999/v1/orders', params={'ticker': 'TAME_A', 'type': 'LIMIT', 'quantity': 2000, 'price': bid_A, 'action': 'BUY'})
                            else:
                                # if primary market has a better (including fees), buy at the ask price for liquidity
                                s.post('http://localhost:9999/v1/orders', params={'ticker': 'TAME_M', 'type': 'LIMIT', 'quantity': 2000, 'price': bid_M, 'action': 'BUY'})

                            # get number of shares in portfolio to determine if position is flattened (or reversed)
                            portfolio = s.get('http://localhost:9999/v1/assets/history', params={'ticker': ticker})
                            shares = portfolio.get('quantity')

                            # if position is reversed (excess shares are bought), flatten position
                            if shares < 0:
                                s.post('http://localhost:9999/v1/orders', params={'ticker': 'TAME_M', 'type': 'MARKET', 'quantity': shares, 'action': 'SELL'})
                                return
                                
                            # stop buying if all shares are bought back
                            if shares == 0:
                                return

                            else:
                                pass
                    
                    tick = get_tick(s)

            tick = get_tick(s)

if __name__ == '__main__':
    # register the custom signal handler for graceful shutdowns
    signal.signal(signal.SIGINT, signal_handler)
    main()