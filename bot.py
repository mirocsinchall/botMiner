import websocket, json, pprint, talib, numpy
import config
from binance.client import Client
from binance.enums import *
import numpy as np
import math
import redis
import json
import logging
import sys
import time

r = redis.Redis(host='localhost', port=6379, db=0)
# RSI_OVERBOUGHT = 70
# RSI_OVERSOLD = 30

logger = logging.getLogger()
logger.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s | %(levelname)s | %(message)s')

stdout_handler = logging.StreamHandler(sys.stdout)
stdout_handler.setLevel(logging.DEBUG)
stdout_handler.setFormatter(formatter)

file_handler = logging.FileHandler('logs.log')
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(formatter)


logger.addHandler(file_handler)
logger.addHandler(stdout_handler)


# BTC
TRADE_QUANTITY = 0.005
TRADE_SYMBOL = 'BTCUSDT'
SOCKET = "wss://stream.binance.com:9443/ws/btcusdt@kline_1m"

# ADA
# TRADE_QUANTITY = 20
# TRADE_SYMBOL = 'ADAUSDT'
# SOCKET = "wss://stream.binance.com:9443/ws/adausdt@kline_1m"


# TRADE_QUANTITY = 0.05
# TRADE_SYMBOL = 'ETHUSDT'
# SOCKET = "wss://stream.binance.com:9443/ws/ethusdt@kline_1m"

liveOrder = r.get("liveOrder") 
aroon_time_period = 14
closes = []
highs = []
lows = []
profit = r.get("profit")
lastBuy = r.get("lastBuy")
expProfit = 0.20

logger.info(f'Trading Symbol: {TRADE_SYMBOL}  Trading Qty: {TRADE_QUANTITY}')

if liveOrder==None:
    liveOrder = False
else:
    if "true" in (str(liveOrder).lower()):
        liveOrder = True
    else:
        liveOrder = False

if liveOrder:
    logger.info(f'Trading Type: Live')
else:
    logger.info(f'Trading Type: Test')


if lastBuy==None:
    lastBuy = []
else:
    lastBuy = json.loads(lastBuy)

if profit==None:
    profit = 0
else:
    profit = float(profit)


client = Client(config.API_KEY, config.API_SECRET)

def order(side, price,quantity, symbol,live_order=False,order_type=ORDER_TYPE_MARKET):
    try:
        # print("sending order")
        logger.info('Sending Order...')
        # ORDER_TYPE_LIMIT
        # ORDER_TYPE_MARKET
        if live_order:
            order = client.create_order(symbol=symbol, side=side, type=order_type, quantity=quantity)
        else:
            order = client.create_test_order(symbol=symbol, side=side, type=order_type, quantity=quantity)

        # order = client.create_order(symbol=symbol, side=side, type=order_type, quantity=quantity,price="{:.2f}".format(float(price)))
        # order = client.create_test_order(symbol=symbol, side=side, type=order_type, quantity=quantity,price="{:.2f}".format(float(price)),timeInForce='GTC')
        # print(order)
        logger.info(order)
    except Exception as e:
        print("an exception occured - {}".format(e))
        return False

    return True

def on_open(ws):
    # print('opened connection')
    logger.info('Binance Socket opened')

def on_close(ws):
    # print('closed connection')
    logger.info('Binance Socket closed')

def on_message(ws, message):
    global aroon_time_period,closes, highs, lows,lastBuy, profit,r,liveOrder,TRADE_QUANTITY,TRADE_SYMBOL,expProfit
    
    json_message = json.loads(message)
    cs = json_message['k']
    candle_closed,close,high,low = cs['x'], cs['c'], cs['h'], cs['l']
    
    # closes.append(float(close))
    # highs.append(float(high))
    # lows.append(float(low))

    stopBuyWhenAllSold = r.get("stopBuyWhenAllSold")
    if stopBuyWhenAllSold==None:
        stopBuyWhenAllSold = 0
    else:
        stopBuyWhenAllSold = int(stopBuyWhenAllSold)
    
    buyCount = r.get("buyCount")
    if buyCount==None:
        buyCount = 2 # default
    else:
        buyCount = int(buyCount)
    
    # profitExpectation = r.get("profitExpectation")
    # if profitExpectation==None:
    #     profitExpectation = 100 # default for BTC
    # else:
    #     profitExpectation = float(profitExpectation)
    
    aroonValueLimit = r.get("aroonValueLimit")
    if aroonValueLimit==None:
        aroonValueLimit = 50 # default
    else:
        aroonValueLimit = int(aroonValueLimit)

    aroonValueLimitLow = r.get("aroonValueLimitLow")
    if aroonValueLimitLow==None:
        aroonValueLimitLow = -50 #20 # default
    else:
        aroonValueLimitLow = float(aroonValueLimitLow)

    if candle_closed:
        closes.append(float(close))
        highs.append(float(high))
        lows.append(float(low))
        closingPrice = float(closes[-1])

        ncleanup = 100
        
        if (len(closes)>ncleanup):
            closes.pop(0)
        if (len(highs)>ncleanup):
            highs.pop(0)
        if (len(lows)>ncleanup):
            lows.pop(0)

        # The oscillator moves between -100 and 100. A high oscillator value is an indication of an uptrend 
        # while a low oscillator value is an indication of a downtrend.
        # above 50 is Bullish and below 50 or negative is Bearish
        # aroon = talib.ATR(numpy.array(highs, dtype='double'),numpy.array(lows, dtype='double'),numpy.array(closes, dtype='double'),aroon_time_period)
        aroon = talib.AROONOSC(numpy.array(highs, dtype='float'),numpy.array(lows, dtype='float'),aroon_time_period)
        aroonValue = aroon[-1]
        
        if (not math.isnan(aroonValue)):
            if aroonValue>aroonValueLimit:
            # -- SELL!
                for index, lbuy in enumerate(lastBuy):
                   expectedPrice = lbuy + (lbuy * (expProfit/100)) # sell if price 0.15% or higher
                   if closingPrice >= expectedPrice: 
                    # if (closingPrice - lbuy >= profitExpectation):
                    # print(f'Uptrend, Selling @ AroonOSC: {round(aroonValue,2)}%' )
                    logger.info(f'Uptrend, Selling @ AroonOSC: {round(aroonValue,2)}%')

                    order_succeeded = order(SIDE_SELL,closingPrice, TRADE_QUANTITY, TRADE_SYMBOL,liveOrder)
                    if order_succeeded:
                        transFee = (TRADE_QUANTITY * closingPrice) * (0.1/100)
                        profit = profit + ((closingPrice-lbuy) * TRADE_QUANTITY) - transFee
                        # print(f'Estimated Profit {round(profit,2)}')
                        logger.info(f'Estimated Profit {round(profit,2)}')
                        lastBuy.pop(index)
                        r.set('lastBuy', json.dumps(lastBuy))
                        r.set('profit', profit)

            # -- BUY!
            #else:
            elif aroonValue < aroonValueLimitLow:
                if (len(lastBuy)<buyCount and stopBuyWhenAllSold==0):
                    # print(f'Downtrend, Buying @ AroonOSC: {round(aroonValue,2)}%' )
                    logger.info(f'Downtrend, Buying @ AroonOSC: {round(aroonValue,2)}%')
                    order_succeeded = order(SIDE_BUY,closingPrice, TRADE_QUANTITY, TRADE_SYMBOL,liveOrder)
                    if order_succeeded:
                        transFee = 0.10 # BNB Transfer Fee
                        profit = profit - transFee
                        lastBuy.append(closingPrice)
                        r.set('lastBuy', json.dumps(lastBuy))
                        r.set('profit', profit)
                        
        # print(f'Closes @ {closingPrice}  AroonOSC @ {aroonValue}%   LastBuy @ {lastBuy}')
        expectedToSellAt = []
        for index, lbuy in enumerate(lastBuy):
            sellAt = round(lbuy + (lbuy * (expProfit/100)),2)
            expectedToSellAt.append(sellAt)
        logger.info(f'AroonOSC @ {round(aroonValue,2)}% (BuyTrend@{aroonValueLimitLow}%  SellTrend@{aroonValueLimit}%)  Closed @ {closingPrice}   LastBuy @ {lastBuy}   Sell @ {expProfit}% {expectedToSellAt}')

        if (stopBuyWhenAllSold==1 and len(lastBuy)==0):
            # print(f'All tokens have been sold out with an estimated profit of {profit}')
            logger.info(f'All tokens have been sold out with an estimated profit of {profit}')
            # r.set("stopBuyWhenAllSold","0")


ws = websocket.WebSocketApp(SOCKET, on_open=on_open, on_close=on_close, on_message=on_message)
ws.run_forever()
