import util
from time import sleep

def get_cl_price(session):
    res = session.get('http://localhost:9999/v1/securities?ticker=CL').json()[0]
    return res['last']

def get_future_price(session):
    ticker = 'CL-1F'
    res = session.get(f'http://localhost:9999/v1/securities?ticker={ticker}').json()[0]
    return res['last']

def calc_spot_future_spread(tick):
    spread = tick * (1/6) / 100
    return (1 - spread)

def spot_futures_arb(spot_price, future_price, theo_spread):
    actual_spread = future_price - spot_price
    required_margin = 0.1
    print('actual-spread: ' + str(actual_spread))
    print('theo-spread: ' + str(theo_spread))
    if actual_spread > (theo_spread + required_margin):
        print('SHORT FUTURES')
    elif (actual_spread + required_margin) < theo_spread:
        print('BUY OIL')
    else:
        print('NEUTRALIZE POSITION')

def main():
    session = util.open_session()
    tick = util.get_tick(session)
    while tick > 0 and tick < 600:
        cl_price = get_cl_price(session)
        future_price = get_future_price(session)
        print(cl_price)
        print(future_price)
        theo_spread = calc_spot_future_spread(tick)
        spot_futures_arb(cl_price, future_price, theo_spread)
        tick = util.get_tick(session)
        sleep(1)

main()