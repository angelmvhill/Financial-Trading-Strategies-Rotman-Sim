import requests

API_KEY = {'APIKEY': 'KZJ94OPT'}

'''
1. Import the 'requests' package.
2. Save your API key for easy access.
3. Create a Session object to manage connections and requests to the RIT client.
4. Add the API key to the Session to authenticate with every request.
5. Make a request to the appropriate URL endpoint, usually using the get() or post() methods.
        In general, the base URL is http://localhost:9999/v1/ followed by a method name
        and potentially some parameters.
        For example, the /case endpoint would look like http://localhost:9999/v1/case
        Or the /orders endpoint would look like http://localhost:9999/v1/orders&ticker=CRZY&type=MARKET&quantity=100
        &action=BUY, where &ticker=CRZY&type=MARKET&quantity=100&action=BUY are
        query parameters specifying a market buy order for 1000 shares of 'CRZY'.
6. Check that the response is as expected.
7. Parse the returned data (if applicable) by calling the json() method.
8. Do something with the parsed data.
'''

def main():
    with requests.Session() as s: # step 3
        s.headers.update(API_KEY) # step 4
        resp = s.get('http://localhost:9999/v1/case') # step 5
        if resp.ok: # step 6
            case = resp.json() # step 7
            tick = case['tick'] # accessing the 'tick' value that was returned
            print('The case is on tick', tick) # step 8

if __name__ == '__main__':
    main()

# sending orders

def main():
    with requests.Session() as s:
        s.headers.update(API_KEY)
        lmt_sell_params = {'ticker': 'CRZY', 'type': 'LIMIT', 'quantity': 2000, 'price': 10.00, 'action': 'SELL'}
        resp = s.post('http://localhost:9999/v1/orders', params=lmt_sell_params)
    if resp.ok:
        lmt_order = resp.json()
        id = lmt_order['order_id']
        print('The limit sell order was submitted and has ID', id)
    else:
        print('The order was not successfully submitted!')

if __name__ == '__main__':
    main()