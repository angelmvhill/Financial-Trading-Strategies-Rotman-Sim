import os
import functools
import operator
import itertools
from time import sleep
import signal
import requests
import pandas as pd
import pandas_ta as ta

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
        
        while tick <= 480:
            tick = get_tick(s)
            
            # vwap, daily_vwap, and portfolio_shares are not defined

            # if today's vwap is more than 10% greater than yesterday's vwap
            # prevents trading when volatility causes large price spikes
            if vwap[-1] > daily_vwap[-2] * 1.1:
                
                # gets current ask from Rotman API - unsure how to parse json output to get the  ask - I believe limiting the request to 1 will send the most recent ask
                current_ask = s.get('http://localhost:9999/v1/securities/book', params={'ticker': 'PTON', 'limit': 1})  
                
                # if the current asking price is less than vwap, place a market order
                # this will allow us to place quick trades when the price is "cheap" and save on transaction cost by placing market instead of limit orders
                # needs a liquidity and volatility parameter to prevent slippage
                if current_ask <= vwap:

                    # send order
                    s.post('http://localhost:9999/v1/orders', params={'ticker': 'PTON', 'type': 'MARKET', 'quantity': 1000, 'action': 'BUY'})

                # if vwap is greater than the asking price, we will place a limit order to ensure that we get filled below the VWAP
                else:
                    
                    # retrieve open order information
                    orders = s.get('http://localhost:9999/v1/orders')
                        
                    # if there are no open orders
                    if len(orders) == 0:

                        # place another limit order at 2 cents below the VWAP
                        s.post('http://localhost:9999/v1/orders', params={'ticker': 'PTON', 'type': 'LIMIT', 'quantity': 2000, 'price': vwap - 0.02, 'action': 'BUY'})

                # end loop after purchasing 100000 shares
                if portfolio_shares == 100000:
                    return
                
                # halt trading is portfolio vwap is  5 cents more than market vwap
                if portfolio_vwap >= market_vwap + .05:
                    return