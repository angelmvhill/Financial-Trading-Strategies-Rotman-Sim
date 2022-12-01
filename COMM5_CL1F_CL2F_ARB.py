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
        # get the current time of the case
        tick = get_tick(s)
       
        while 0 <= tick < 600:
            
            # GET CL1F AND CL2F PRICES
            get_cl_1f = s.get('http://localhost:9999/v1/securities', params = {'ticker': 'CL-1F'})
            cl_1f_price = get_cl_1f.json()[0]['ask']
            cl_2f_price = ticker_close(s, 'CL-2F')

            # CHECK IF CL1F IS AVAILABLE TO TRADE
            if cl_1f_price > 0:

                # SUBMIT ARBITRAGE TRADE IS CL1F AND CL2F HAVE A 30 CENT SPREAD
                if cl_2f_price - cl_1f_price < 0.7:
                    
                    s.post('http://localhost:9999/v1/orders', params = {'ticker': 'CL-1F', 'type': 'MARKET', 'quantity': 30, 'action': 'SELL'})
                    sleep(.1)
                    s.post('http://localhost:9999/v1/orders', params = {'ticker': 'CL-2F', 'type': 'MARKET', 'quantity': 30, 'action': 'BUY'})
                    sleep(.1)

                    print('Shorted CL1F and longed CL2F at 70 cent spread')
                    
                    # SET DEFAULT POSITION VALUE TO 1 -> 1 MEANING TRUE FOR POSITION
                    cl1f_position = 1
                    cl2f_position = 1

                    # RUN THROUGH WHILE LOOP DURING OPEN POSITION TO PREVENT ALGORITHM FROM MOVING TO NEXT STEPS

                    while cl1f_position == 1 or cl2f_position == 1:

                        cl_1f_price = ticker_close(s, 'CL-1F')
                        cl_2f_price = ticker_close(s, 'CL-2F')

                        # LIQUIDATE POSITION AT 85 CENT SPREAD

                        if cl_2f_price - cl_1f_price > 0.85:
                            
                            s.post('http://localhost:9999/v1/orders', params = {'ticker': 'CL-1F', 'type': 'MARKET', 'quantity': 30, 'action': 'BUY'})
                            sleep(.1)
                            s.post('http://localhost:9999/v1/orders', params = {'ticker': 'CL-2F', 'type': 'MARKET', 'quantity': 30, 'action': 'SELL'})
                            sleep(.1)

                            print('Liquidated position')

                            # cl1f = s.get('http://localhost:9999/v1/securities', params={'ticker': 'CL-1F'})
                            # if cl1f.json()[0]['position'] == 0.0:
                            #     cl1f_position = cl1f.json()[0]['position']
                            # cl2f = s.get('http://localhost:9999/v1/securities', params={'ticker': 'CL-2F'})
                            # if cl2f.json()[0]['position'] == 0.0:
                            #     cl2f_position = cl2f.json()[0]['position']
                            # print('getting CL1F and CL2F position')
                            # break

                            # BREAK WHILE LOOP WHEN POSITIONS == 0

                            cl1f = s.get('http://localhost:9999/v1/securities', params={'ticker': 'CL-1F'})
                            cl2f = s.get('http://localhost:9999/v1/securities', params={'ticker': 'CL-2F'})
                            if cl1f.json()[0]['position'] == 0.0:
                                if cl2f.json()[0]['position'] == 0.0:
                                    break

                        # SUBMIT ADDITIONAL ARBITRAGE TRADE IS CL1F AND CL2F HAVE A 50 CENT SPREAD

                        if cl_2f_price - cl_1f_price < 0.5:

                            s.post('http://localhost:9999/v1/orders', params = {'ticker': 'CL-1F', 'type': 'MARKET', 'quantity': 30, 'action': 'SELL'})
                            sleep(.1)
                            s.post('http://localhost:9999/v1/orders', params = {'ticker': 'CL-2F', 'type': 'MARKET', 'quantity': 30, 'action': 'BUY'})
                            sleep(.1)

                            print('Shorted CL1F and longed CL2F at 50 cent spread')

                            # RUN THROUGH WHILE LOOP DURING OPEN POSITION TO PREVENT ALGORITHM FROM MOVING TO NEXT STEPS

                            while cl1f_position == 1 or cl2f_position == 1:

                                cl_1f_price = ticker_close(s, 'CL-1F')
                                cl_2f_price = ticker_close(s, 'CL-2F')

                                # LIQUIDATE POSITION AT 85 CENT SPREAD

                                if cl_2f_price - cl_1f_price > 0.85:
                            
                                    s.post('http://localhost:9999/v1/orders', params = {'ticker': 'CL-1F', 'type': 'MARKET', 'quantity': 30, 'action': 'BUY'})
                                    sleep(.1)
                                    s.post('http://localhost:9999/v1/orders', params = {'ticker': 'CL-2F', 'type': 'MARKET', 'quantity': 30, 'action': 'SELL'})
                                    sleep(.1)
                                    s.post('http://localhost:9999/v1/orders', params = {'ticker': 'CL-1F', 'type': 'MARKET', 'quantity': 30, 'action': 'BUY'})
                                    sleep(.1)
                                    s.post('http://localhost:9999/v1/orders', params = {'ticker': 'CL-2F', 'type': 'MARKET', 'quantity': 30, 'action': 'SELL'})
                                    sleep(.1)

                                    print('Liquidated position')

                                    # cl1f = s.get('http://localhost:9999/v1/securities', params={'ticker': 'CL-1F'})
                                    # if cl1f.json()[0]['position'] == 0.0:
                                    #     cl1f_position = cl1f.json()[0]['position']
                                    # cl2f = s.get('http://localhost:9999/v1/securities', params={'ticker': 'CL-2F'})
                                    # if cl2f.json()[0]['position'] == 0.0:
                                    #     cl2f_position = cl2f.json()[0]['position']
                                    #     break
                                    # print('getting CL1F and CL2F position')

                                    # BREAK WHILE LOOP WHEN POSITIONS == 0

                                    cl1f = s.get('http://localhost:9999/v1/securities', params={'ticker': 'CL-1F'})
                                    cl2f = s.get('http://localhost:9999/v1/securities', params={'ticker': 'CL-2F'})
                                    if cl1f.json()[0]['position'] == 0.0:
                                        if cl2f.json()[0]['position'] == 0.0:
                                            break
                                    
                                # SUBMIT ADDITIONAL ARBITRAGE TRADE IS CL1F AND CL2F HAVE A 30 CENT SPREAD

                                if cl_2f_price - cl_1f_price < 0.3:

                                    s.post('http://localhost:9999/v1/orders', params = {'ticker': 'CL-1F', 'type': 'MARKET', 'quantity': 30, 'action': 'SELL'})
                                    s.post('http://localhost:9999/v1/orders', params = {'ticker': 'CL-2F', 'type': 'MARKET', 'quantity': 30, 'action': 'BUY'})

                                    print('Shorted CL1F and longed CL2F at 30 cent spread')

                                    # RUN THROUGH WHILE LOOP DURING OPEN POSITION TO PREVENT ALGORITHM FROM MOVING TO NEXT STEPS

                                    while cl1f_position == 1 or cl2f_position == 1:

                                        cl_1f_price = ticker_close(s, 'CL-1F')
                                        cl_2f_price = ticker_close(s, 'CL-2F')
                                    
                                        # LIQUIDATE POSITION AT 85 CENT SPREAD

                                        if cl_2f_price - cl_1f_price > 0.85:
                            
                                            s.post('http://localhost:9999/v1/orders', params = {'ticker': 'CL-1F', 'type': 'MARKET', 'quantity': 30, 'action': 'BUY'})
                                            sleep(.1)
                                            s.post('http://localhost:9999/v1/orders', params = {'ticker': 'CL-2F', 'type': 'MARKET', 'quantity': 30, 'action': 'SELL'})
                                            sleep(.1)
                                            s.post('http://localhost:9999/v1/orders', params = {'ticker': 'CL-1F', 'type': 'MARKET', 'quantity': 30, 'action': 'BUY'})
                                            sleep(.1)
                                            s.post('http://localhost:9999/v1/orders', params = {'ticker': 'CL-2F', 'type': 'MARKET', 'quantity': 30, 'action': 'SELL'})
                                            sleep(.1)
                                            s.post('http://localhost:9999/v1/orders', params = {'ticker': 'CL-1F', 'type': 'MARKET', 'quantity': 30, 'action': 'BUY'})
                                            sleep(.1)
                                            s.post('http://localhost:9999/v1/orders', params = {'ticker': 'CL-2F', 'type': 'MARKET', 'quantity': 30, 'action': 'SELL'})
                                            sleep(.1)

                                            print('Liquidated position')

                                            # cl1f = s.get('http://localhost:9999/v1/securities', params={'ticker': 'CL-1F'})
                                            # if cl1f.json()[0]['position'] == 0.0:
                                            #     cl1f_position = cl1f.json()[0]['position']
                                            # cl2f = s.get('http://localhost:9999/v1/securities', params={'ticker': 'CL-2F'})
                                            # if cl2f.json()[0]['position'] == 0.0:
                                            #     cl2f_position = cl2f.json()[0]['position']
                                            # print('getting CL1F and CL2F position')

                                            # BREAK WHILE LOOP WHEN POSITIONS == 0

                                            cl1f = s.get('http://localhost:9999/v1/securities', params={'ticker': 'CL-1F'})
                                            cl2f = s.get('http://localhost:9999/v1/securities', params={'ticker': 'CL-2F'})
                                            if cl1f.json()[0]['position'] == 0.0:
                                                if cl2f.json()[0]['position'] == 0.0:
                                                    break

                # print('Exited Loop 1')

                # SUBMIT ARBITRAGE TRADE IS CL1F AND CL2F HAVE A $1.30 SPREAD
                if cl_2f_price - cl_1f_price > 1.3:
                    
                    s.post('http://localhost:9999/v1/orders', params = {'ticker': 'CL-1F', 'type': 'MARKET', 'quantity': 30, 'action': 'BUY'})
                    sleep(.1)
                    s.post('http://localhost:9999/v1/orders', params = {'ticker': 'CL-2F', 'type': 'MARKET', 'quantity': 30, 'action': 'SELL'})
                    sleep(.1)

                    print('Shorted CL2F and longed CL1F at $1.30 spread')
                    
                    # SET DEFAULT POSITION VALUE TO 1 -> 1 MEANING TRUE FOR POSITION

                    cl1f_position = 1
                    cl2f_position = 1

                    # RUN THROUGH WHILE LOOP DURING OPEN POSITION TO PREVENT ALGORITHM FROM MOVING TO NEXT STEPS

                    while cl1f_position == 1 or cl2f_position == 1:

                        cl_1f_price = ticker_close(s, 'CL-1F')
                        cl_2f_price = ticker_close(s, 'CL-2F')

                        # LIQUIDATE POSITION AT $1.15 SPREAD

                        if cl_2f_price - cl_1f_price < 1.15:
                            
                            s.post('http://localhost:9999/v1/orders', params = {'ticker': 'CL-1F', 'type': 'MARKET', 'quantity': 30, 'action': 'SELL'})
                            sleep(.1)
                            s.post('http://localhost:9999/v1/orders', params = {'ticker': 'CL-2F', 'type': 'MARKET', 'quantity': 30, 'action': 'BUY'})
                            sleep(.1)

                            print('Liquidated position')

                            # cl1f = s.get('http://localhost:9999/v1/securities', params={'ticker': 'CL-1F'})
                            # if cl1f.json()[0]['position'] == 0.0:
                            #     cl1f_position = cl1f.json()[0]['position']
                            # cl2f = s.get('http://localhost:9999/v1/securities', params={'ticker': 'CL-2F'})
                            # if cl2f.json()[0]['position'] == 0.0:
                            #     cl2f_position = cl2f.json()[0]['position']
                            # print('getting CL1F and CL2F position')

                            # BREAK WHILE LOOP WHEN POSITIONS == 0

                            cl1f = s.get('http://localhost:9999/v1/securities', params={'ticker': 'CL-1F'})
                            cl2f = s.get('http://localhost:9999/v1/securities', params={'ticker': 'CL-2F'})
                            if cl1f.json()[0]['position'] == 0.0:
                                if cl2f.json()[0]['position'] == 0.0:
                                    break

                        # SUBMIT ARBITRAGE TRADE IS CL1F AND CL2F HAVE A $1.50 SPREAD

                        if cl_2f_price - cl_1f_price > 1.5:

                            s.post('http://localhost:9999/v1/orders', params = {'ticker': 'CL-1F', 'type': 'MARKET', 'quantity': 30, 'action': 'BUY'})
                            sleep(.1)
                            s.post('http://localhost:9999/v1/orders', params = {'ticker': 'CL-2F', 'type': 'MARKET', 'quantity': 30, 'action': 'SELL'})
                            sleep(.1)

                            print('Shorted CL2F and longed CL1F at $1.50 spread')

                            # RUN THROUGH WHILE LOOP DURING OPEN POSITION TO PREVENT ALGORITHM FROM MOVING TO NEXT STEPS

                            while cl1f_position == 1 or cl2f_position == 1:

                                cl_1f_price = ticker_close(s, 'CL-1F')
                                cl_2f_price = ticker_close(s, 'CL-2F')

                                # LIQUIDATE POSITION AT $1.15 SPREAD

                                if cl_2f_price - cl_1f_price < 1.15:
                            
                                    s.post('http://localhost:9999/v1/orders', params = {'ticker': 'CL-1F', 'type': 'MARKET', 'quantity': 30, 'action': 'SELL'})
                                    sleep(.1)
                                    s.post('http://localhost:9999/v1/orders', params = {'ticker': 'CL-2F', 'type': 'MARKET', 'quantity': 30, 'action': 'BUY'})
                                    sleep(.1)
                                    s.post('http://localhost:9999/v1/orders', params = {'ticker': 'CL-1F', 'type': 'MARKET', 'quantity': 30, 'action': 'SELL'})
                                    sleep(.1)
                                    s.post('http://localhost:9999/v1/orders', params = {'ticker': 'CL-2F', 'type': 'MARKET', 'quantity': 30, 'action': 'BUY'})
                                    sleep(.1)

                                    print('Liquidated position')

                                    # cl1f = s.get('http://localhost:9999/v1/securities', params={'ticker': 'CL-1F'})
                                    # if cl1f.json()[0]['position'] == 0.0:
                                    #     cl1f_position = cl1f.json()[0]['position']
                                    # cl2f = s.get('http://localhost:9999/v1/securities', params={'ticker': 'CL-2F'})
                                    # if cl2f.json()[0]['position'] == 0.0:
                                    #     cl2f_position = cl2f.json()[0]['position']
                                    # print('getting CL1F and CL2F position')

                                    # BREAK WHILE LOOP WHEN POSITIONS == 0

                                    cl1f = s.get('http://localhost:9999/v1/securities', params={'ticker': 'CL-1F'})
                                    cl2f = s.get('http://localhost:9999/v1/securities', params={'ticker': 'CL-2F'})
                                    if cl1f.json()[0]['position'] == 0.0:
                                        if cl2f.json()[0]['position'] == 0.0:
                                            break

                                # SUBMIT ARBITRAGE TRADE IS CL1F AND CL2F HAVE A $1.70 SPREAD

                                if cl_2f_price - cl_1f_price > 1.7:

                                    s.post('http://localhost:9999/v1/orders', params = {'ticker': 'CL-1F', 'type': 'MARKET', 'quantity': 30, 'action': 'BUY'})
                                    sleep(.1)
                                    s.post('http://localhost:9999/v1/orders', params = {'ticker': 'CL-2F', 'type': 'MARKET', 'quantity': 30, 'action': 'SELL'})
                                    sleep(.1)

                                    print('Shorted CL2F and longed CL1F at 30 cent spread')

                                    # RUN THROUGH WHILE LOOP DURING OPEN POSITION TO PREVENT ALGORITHM FROM MOVING TO NEXT STEPS

                                    while cl1f_position == 1 or cl2f_position == 1:

                                        cl_1f_price = ticker_close(s, 'CL-1F')
                                        cl_2f_price = ticker_close(s, 'CL-2F')

                                        # LIQUIDATE POSITION AT $1.15 SPREAD
                                    
                                        if cl_2f_price - cl_1f_price < 1.15:
                            
                                            s.post('http://localhost:9999/v1/orders', params = {'ticker': 'CL-1F', 'type': 'MARKET', 'quantity': 30, 'action': 'SELL'})
                                            sleep(.1)
                                            s.post('http://localhost:9999/v1/orders', params = {'ticker': 'CL-2F', 'type': 'MARKET', 'quantity': 30, 'action': 'BUY'})
                                            sleep(.1)
                                            s.post('http://localhost:9999/v1/orders', params = {'ticker': 'CL-1F', 'type': 'MARKET', 'quantity': 30, 'action': 'SELL'})
                                            sleep(.1)
                                            s.post('http://localhost:9999/v1/orders', params = {'ticker': 'CL-2F', 'type': 'MARKET', 'quantity': 30, 'action': 'BUY'})
                                            sleep(.1)
                                            s.post('http://localhost:9999/v1/orders', params = {'ticker': 'CL-1F', 'type': 'MARKET', 'quantity': 30, 'action': 'SELL'})
                                            sleep(.1)
                                            s.post('http://localhost:9999/v1/orders', params = {'ticker': 'CL-2F', 'type': 'MARKET', 'quantity': 30, 'action': 'BUY'})
                                            sleep(.1)

                                            print('Liquidated position')

                                            # cl1f = s.get('http://localhost:9999/v1/securities', params={'ticker': 'CL-1F'})
                                            # if cl1f.json()[0]['position'] == 0.0:
                                            #     cl1f_position = cl1f.json()[0]['position']
                                            # cl2f = s.get('http://localhost:9999/v1/securities', params={'ticker': 'CL-2F'})
                                            # if cl2f.json()[0]['position'] == 0.0:
                                            #     cl2f_position = cl2f.json()[0]['position']
                                            # print('getting CL1F and CL2F position')

                                            # BREAK WHILE LOOP WHEN POSITIONS == 0

                                            cl1f = s.get('http://localhost:9999/v1/securities', params={'ticker': 'CL-1F'})
                                            cl2f = s.get('http://localhost:9999/v1/securities', params={'ticker': 'CL-2F'})
                                            if cl1f.json()[0]['position'] == 0.0:
                                                if cl2f.json()[0]['position'] == 0.0:
                                                    break

                # print('Exited Loop 2')

if __name__ == '__main__':
    signal.signal(signal.SIGINT, signal_handler)
    main()