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

API_KEY = {'X-API-Key': 'KZJ94OPT'}

def main_function():
    session = requests.session()
    session.headers.update(API_KEY)

    tender_dict = session.get('http://localhost:9999/v1/tenders')
    print(tender_dict.json())
    # tender_dict.json()
    # tender_dict.loads()
    # print(tender_dict['tender_id'])
    # print(tender_dict['ticker'])
    

main_function()

# s.post('http://localhost:9999/v1/tenders', params={'id': order_id})