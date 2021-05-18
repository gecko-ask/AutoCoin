import time
import pyupbit
from datetime import datetime
from datetime import timedelta
import requests
import os
from logging import handlers
import logging

myToken = "0"

access = "0"
secret = "0"

log_dir = './logs'

if not os.path.exists(log_dir):
    os.mkdir(log_dir)

#log settings
geckoLogFormatter = logging.Formatter('%(asctime)s [%(levelname)8s] |%(funcName)s|%(lineno)d| [ %(message)s ]')

#handler settings
geckoLogHandler = handlers.TimedRotatingFileHandler(filename=log_dir + '/AutoCoin.log', when='midnight', interval=1, encoding='utf-8')
geckoLogHandler.setFormatter(geckoLogFormatter)
geckoLogHandler.suffix = "%Y%m%d"

#logger set
geckoLogger = logging.getLogger()
geckoLogger.setLevel(logging.INFO)
geckoLogger.addHandler(geckoLogHandler)

slackchannel = "#coin"

def post_message(token, channel, text):
    """슬랙 메시지 전송"""
    geckoLogger.info(" 슬랙 전송 ")
    response = requests.post("https://slack.com/api/chat.postMessage",
        headers={"Authorization": "Bearer "+token},
        data={"channel": channel,"text": text}
    )

def get_start_time(ticker):
    """시작 시간 조회"""
    df = pyupbit.get_ohlcv(ticker, interval="day", count=1)
    start_time = df.index[0]
    return start_time

def get_balance(ticker):
    """잔고 조회"""
    geckoLogger.info(" 잔고조회  >> " + str(ticker))
    balances = upbit.get_balances()
    for b in balances:
        if b['currency'] == ticker[4:]:
            if b['balance'] is not None:
                return float(b['balance'])
            else:
                return 0

def get_current_price(ticker):
    """현재가 조회"""
    geckoLogger.info(" 현재가 >> " + str(ticker))
    return pyupbit.get_orderbook(tickers=ticker)[0]["orderbook_units"][0]["ask_price"]

def get_buy_price(ticker):
    """매수 가격"""
    geckoLogger.info(" 평단가 >> " + str(ticker))
    balances = upbit.get_balances()
    for bal in balances:
        if bal['currency'] == ticker[4:]:
            return float(bal['avg_buy_price'])

# def get_ma(ticker, cnt, t):
#     """이동 평균선 조회 (cnt = 10 : 10분 이동평균 time = -1 : 현재 이동평균가 -2 : 1분전 이동평균가)"""    
#     geckoLogger.info(" 이동 평균 >> " + str(ticker))
#     df = pyupbit.get_ohlcv(ticker, interval="minute1", count=cnt+(-1*t))
#     ma = df['close'].rolling(cnt).mean().iloc[t]
#     time.sleep(0.1)
#     return ma

def get_ma(ticker, cnt):
    """이동 평균선 조회 (cnt = 10 : 10분 이동평균)"""    
    geckoLogger.info(" 이동 평균 >> " + str(ticker))
    df = pyupbit.get_ohlcv(ticker, interval="minute1", count=cnt+(10))
    ma = df['close'].rolling(cnt).mean()
    time.sleep(0.1)
    return ma

def get_pre_price(ticker):
    """1분전 종가 조회"""
    geckoLogger.info(" 이전 종가 >> " + str(ticker))
    df = pyupbit.get_ohlcv(ticker, interval="minute1", count=2)
    time.sleep(0.1)
    pre_price = df['close'].iloc[-2]
    return pre_price


def buy_coin(ticker):
    try:
        geckoLogger.info('매수 함수 호출')
        global wish_list    # 함수 내에서 값 변경을 하기 위해 global로 지정    
        global bought_list      
        # if ticker in bought_list: # 매수 완료 종목이면 더 이상 안 사도록 함수 종료
        #     #printlog('code:', code, 'in', bought_list)
        #     return False

        current_price = get_current_price(ticker) 
        
        # 매수 전략 수정
        # 5분 10분 20분 이동평균선 상승 중
        # 이전에 이동평균선이 하향이었던 종목 구매  

        # 이전 이동평균선의 기울기 계산 
        ma5_series = get_ma(sym,5)
        ma10_series = get_ma(sym,10)
        ma20_series = get_ma(sym,20)

        ma5_diff = ma5_series.iloc[-2] - ma5_series.iloc[-3]
        ma10_diff = ma10_series.iloc[-2] - ma10_series.iloc[-3]
        ma20_diff = ma20_series.iloc[-2] - ma20_series.iloc[-3]

        # geckoLogger.debug(" 매수 진입 >> " + str(ticker) + "|" + str(ma5_diff) + "|" + str(ma10_diff) + "|" + str(ma20_diff))
        
        # print(ma5_diff, ma10_diff, ma20_diff)
        
        if ma5_diff > 0 and ma10_diff > 0 and ma20_diff > 0 and ticker in wish_list and bought_cnt[ticker] < maximum_buy_qty : 
            # 추가 매수 경우, 평단가가 현재가보다 낮으면 구매하지 않고, 위시리스트에서도 삭제.
            if bought_cnt[ticker] > 0 :
                buy_price = get_buy_price(ticker)    # 매수 가격
                if current_price >= buy_price :
                    if ticker in wish_list:
                        wish_list.remove(ticker) 
                    return False

                else :
                    # if bought_cnt[ticker] == 2:
                    #     buy_amount = unit_buy_amount * 2.5
                    if bought_cnt[ticker] == 1:
                        buy_amount = unit_buy_amount * 2
                    else:
                        buy_amount = unit_buy_amount
            else :
                buy_amount = unit_buy_amount

            # 현재 잔액(KRW)이 부족할 경우 매수는 진행하지 않고 위시 리스트에서 제거.
            if upbit.get_balance("KRW") < buy_amount:
                wish_list.remove(sym)
                post_message(myToken,slackchannel, datetime.now().strftime('[%m/%d %H:%M:%S] ') + "잔액 부족 ! : " + ticker)            
                time.sleep(0.2)
                geckoLogger.info("잔액 부족 ! : " + ticker)
                return False

            # 매수 주문 요청
            order = upbit.buy_market_order(ticker, buy_amount*0.9995) 

            post_message(myToken,slackchannel, datetime.now().strftime('[%m/%d %H:%M:%S] ') + "매수 조건 일치! : " + ticker + " = " + str(current_price))            
            time.sleep(0.2)
            geckoLogger.info('매수 주문 체결 완료 >> ' + ticker)
            
            # 매수 주문 채결 완료 대기
            while True:
                order_result = upbit.get_order(order['uuid'])
                time.sleep(1)
                if order_result['state'] == 'done' or order_result['state'] == 'cancel' : break
            
            # geckoLogger.debug(" 매수 주문 완료 >> " + str(ticker) + "|" + str(current_price))   

            bought_cnt[ticker] += 1
            
            if ticker not in bought_list:
                bought_list.append(ticker)
            if ticker in wish_list:
                wish_list.remove(ticker)  
            
            post_message(myToken,slackchannel, datetime.now().strftime('[%m/%d %H:%M:%S] ') + "Bought list : " + str(bought_list))
            time.sleep(0.2)
            post_message(myToken,slackchannel, datetime.now().strftime('[%m/%d %H:%M:%S] ') + "Wish list : " + str(wish_list))
            time.sleep(0.2)
            post_message(myToken,slackchannel, datetime.now().strftime('[%m/%d %H:%M:%S] ') + "매수 횟수 : " + str(bought_cnt[sym]))
            time.sleep(0.2)
            
            # # if문 밖으로 이동 - 수동 매수의 경우 확인하기 위해서   
            # bought_qty = upbit.get_balance(ticker)
            # time.sleep(0.3)
            # # 구매수량이 5000원(최소거래금액)이상일 경우엔 구매리스트에 추가하여 더 이상 구매하지 않음
            # if bought_qty > 5000/current_price:
                              
            #     # print(bought_list)
            
                
    except Exception as ex:
        print(datetime.now().strftime('[%m/%d %H:%M:%S] ') + str(ticker) + " 매수 >> " + str(ex))
        post_message(myToken,slackchannel, datetime.now().strftime('[%m/%d %H:%M:%S] ') + str(ticker) + " 매수 >> " + str(ex))
        geckoLogger.info(" 매수 >> " + str(ex))

def sell_coin(ticker):
    try:
        geckoLogger.info('매도 함수 호출')
        current_price = get_current_price(ticker) 
        buy_price = get_buy_price(ticker)    # 평단가

        balance = get_balance(ticker)

        
        # 5분 이동평균선 방향
        ma5_series = get_ma(sym,5)
        ma5_diff = (ma5_series.iloc[-2] - ma5_series.iloc[-3])      
        # 20분 이동평균가
        ma20 = get_ma(sym,20).iloc[-1]    
        # print(ma5_diff)
        # post_message(myToken,slackchannel, datetime.now().strftime('[%m/%d %H:%M:%S] ') + sym +" = "+ str(ma5_diff))
        # time.sleep(0.5)
        # post_message(myToken,slackchannel, datetime.now().strftime('[%m/%d %H:%M:%S] ') + "Wish list : " + str(wish_list))  

        # geckoLogger.debug(" 매도 진입 >> " + str(ticker) + "|" + str(ma5_diff))

        # 매도 조건 - 구매한 항목일 경우 / 이동평균선 보다 현재가가 낮은 경우 / 평단가의 0.25퍼센트 이상의 가격일 경우
        #                                                                   1.002 매도 잘하지만 가끔 손해(수수료)
        # 무조건 1.5%이상 손해나면 손절.
        if buy_price is not None:
            if (ma5_diff <= 0 and current_price > (buy_price * 1.0025) and current_price <= ma20) or current_price < (buy_price * 0.985):    
                if balance > 5000/current_price:
                    # 매도 주문 요청
                    upbit.sell_market_order(ticker, balance * 1)                    
                    time.sleep(3)

                    post_message(myToken,slackchannel, datetime.now().strftime('[%m/%d %H:%M:%S] ') + "매도 조건 일치! : " + ticker + " = " + str(current_price-buy_price))
                    time.sleep(0.2)
                    geckoLogger.info('매도 주문 체결 완료 >> ' + ticker)

                # geckoLogger.debug(" 매도 주문 완료 >> " + str(ticker) + "|" + str(current_price))
                
                # 보유 수량 조회 후 매수리스트에서 삭제
                bought_balance = upbit.get_balance(ticker)
                time.sleep(0.3)
                if bought_balance == 0 or bought_balance < 5000/current_price:
                    if ticker in bought_list:
                        bought_list.remove(ticker)
                    if ticker in wish_list:
                        wish_list.remove(ticker)  
                    # print(bought_list)

                post_message(myToken,slackchannel, datetime.now().strftime('[%m/%d %H:%M:%S] ') + "Bought list : " + str(bought_list))
                time.sleep(0.2)
                post_message(myToken,slackchannel, datetime.now().strftime('[%m/%d %H:%M:%S] ') + "Wish list : " + str(wish_list))    
                time.sleep(0.2)

    except Exception as ex:
        print(datetime.now().strftime('[%m/%d %H:%M:%S] ') + str(ticker) + " 매도 >> " + str(ex))
        post_message(myToken,slackchannel, datetime.now().strftime('[%m/%d %H:%M:%S] ') + str(ticker) + " 매도 >> " + str(ex))
        geckoLogger.info(" 매도 >> " + str(ex))


# def sell_all(ticker):
#     try:
#         geckoLogger.info('매도 All 함수 호출')
#         current_price = get_current_price(ticker) 
#         buy_price = get_buy_price(ticker)    # 매수 가격

#         balance = get_balance(ticker)

#         # geckoLogger.debug(" 매도 all 진입 >> " + str(ticker))
        
#         if buy_price is not None and current_price > (buy_price * 1.0025):
#             if balance > 5000/current_price:                
#                 # 매도 주문 요청
#                 upbit.sell_market_order(ticker, balance * 1)
#                 post_message(myToken,slackchannel, datetime.now().strftime('[%m/%d %H:%M:%S] ') + "Sell all !!!  "  + str(ticker))
#                 time.sleep(0.2)
#                 geckoLogger.info('매도 All 주문 체결 완료 >> ' + ticker)
#                 time.sleep(3)
            
#             # 보유 수량 조회 후 매수리스트에서 삭제
#             bought_balance = upbit.get_balance(ticker)
#             time.sleep(0.3)
#             if bought_balance == 0 or bought_balance < 5000/current_price:
#                 if ticker in bought_list:
#                     bought_list.remove(ticker)
#                 if ticker in wish_list:
#                     wish_list.remove(ticker)  
                
#     except Exception as ex:
#         print(datetime.now().strftime('[%m/%d %H:%M:%S] ') + str(ticker) + " 매도 all >> " + str(ex))
#         post_message(myToken,slackchannel, datetime.now().strftime('[%m/%d %H:%M:%S] ') + str(ticker) + " 매도 all >> " + str(ex))
#         geckoLogger.info(" 매도 all >> " + str(ex))


# 로그인
geckoLogger.info('업비트 로그인 시도')
upbit = pyupbit.Upbit(access, secret)
# print("autotrade start")
geckoLogger.info('프로그램 시작')
post_message(myToken,slackchannel, datetime.now().strftime('[%m/%d %H:%M:%S] ') + "시작!")

ticker_list = ['KRW-BTC', 'KRW-ETH', 'KRW-DOGE', 'KRW-ETC', 'KRW-QTUM']
# ticker_list = ['KRW-BTC', 'KRW-ETH', 'KRW-DOGE', 'KRW-ETC', 'KRW-QTUM', 'KRW-BTT', 'KRW-SC']
# ticker_list = ['KRW-BTC', 'KRW-ETH', 'KRW-ETC', 'KRW-BTT','KRW-WAVES', 'KRW-LINK']
# ticker_list = ['KRW-DOGE', 'KRW-ETC', 'KRW-XRP', 'KRW-ETH', 'KRW-BTC',
#                 'KRW-EOS', 'KRW-WAVES', 'KRW-BTT', 'KRW-LINK', 'KRW-BTG',
#                 'KRW-QTUM', 'KRW-NEO', 'KRW-ADA', 'KRW-VET', 'KRW-TRX'] 
# ticker_list = ['KRW-LINK']
# ticker_list = ['KRW-BTC', 'KRW-ETH', 'KRW-NEO', 'KRW-MTL', 'KRW-LTC',
#  'KRW-XRP', 'KRW-ETC', 'KRW-OMG', 'KRW-SNT', 'KRW-WAVES',
#   'KRW-XEM', 'KRW-QTUM', 'KRW-LSK', 'KRW-STEEM', 'KRW-XLM',
#    'KRW-ARDR', 'KRW-KMD', 'KRW-ARK', 'KRW-STORJ', 'KRW-GRS',
#     'KRW-REP', 'KRW-EMC2', 'KRW-ADA', 'KRW-SBD', 'KRW-POWR', 'KRW-BTG',
#      'KRW-ICX', 'KRW-EOS', 'KRW-TRX', 'KRW-SC', 'KRW-IGNIS', 'KRW-ONT',
#       'KRW-ZIL', 'KRW-POLY', 'KRW-ZRX', 'KRW-LOOM', 'KRW-BCH', 'KRW-ADX',
#        'KRW-BAT', 'KRW-IOST', 'KRW-DMT', 'KRW-RFR', 'KRW-CVC', 'KRW-IQ',
#         'KRW-IOTA', 'KRW-MFT', 'KRW-ONG', 'KRW-GAS', 'KRW-UPP', 'KRW-ELF',
#          'KRW-KNC', 'KRW-BSV', 'KRW-THETA', 'KRW-EDR', 'KRW-QKC', 'KRW-BTT',
#           'KRW-MOC', 'KRW-ENJ', 'KRW-TFUEL', 'KRW-MANA', 'KRW-ANKR', 'KRW-AERGO',
#            'KRW-ATOM', 'KRW-TT', 'KRW-CRE', 'KRW-SOLVE', 'KRW-MBL', 'KRW-TSHP',
#             'KRW-WAXP', 'KRW-HBAR', 'KRW-MED', 'KRW-MLK', 'KRW-STPT', 'KRW-ORBS',
#              'KRW-VET', 'KRW-CHZ', 'KRW-PXL', 'KRW-STMX', 'KRW-DKA', 'KRW-HIVE',
#               'KRW-KAVA', 'KRW-AHT', 'KRW-LINK', 'KRW-XTZ', 'KRW-BORA', 'KRW-JST',
#                'KRW-CRO', 'KRW-TON', 'KRW-SXP', 'KRW-LAMB', 'KRW-HUNT', 'KRW-MARO',
#                 'KRW-PLA', 'KRW-DOT', 'KRW-SRM', 'KRW-MVL', 'KRW-PCI', 'KRW-STRAX',
#                  'KRW-AQT', 'KRW-BCHA', 'KRW-GLM', 'KRW-QTCON', 'KRW-SSX', 'KRW-META',
#                   'KRW-OBSR', 'KRW-FCT2', 'KRW-LBC', 'KRW-CBK', 'KRW-SAND', 'KRW-HUM',
#                    'KRW-DOGE', 'KRW-STRK', 'KRW-PUNDIX', 'KRW-FLOW', 'KRW-DAWN', 'KRW-AXS',
#                     'KRW-STX']

bought_list = []     # 매수 완료된 종목 리스트
bought_cnt = {}     # 매수 횟수 딕셔너리
wish_list = []      # 이동평균선이 하향했던 종목 리스트
maximum_buy_qty = 2 # 최대 추가 매수 횟수
target_count = len(ticker_list) # 매수할 종목 수
buy_rate = 1/(target_count*(maximum_buy_qty+1)) #종목당 구매 비율
heartbeat_flag = 0

# 종목당 구매할 금액 계산
unit_buy_amount = upbit.get_balance("KRW") * buy_rate
        
# 최소 주문금액 
if unit_buy_amount < 5100:
    unit_buy_amount = 5100 

post_message(myToken,slackchannel, datetime.now().strftime('[%m/%d %H:%M:%S] ') + "종목수 : " + str(target_count) 
                                                                                + " | 추가매수 횟수 : " + str(maximum_buy_qty) + " | 종목당 구매 금액 : " + str(unit_buy_amount))

# 자동매매 시작
while True:
    try:
        now = datetime.now()
        start_time = get_start_time("KRW-BTC")
        end_time = start_time + timedelta(days=1)
        
        if (29 <= now.minute <= 31 or now.minute <= 1 or now.minute >=59) and heartbeat_flag == 0:
            post_message(myToken,slackchannel, datetime.now().strftime('[%m/%d %H:%M:%S] ') + "Bought list : " + str(bought_list))
            time.sleep(0.2)
            post_message(myToken,slackchannel, datetime.now().strftime('[%m/%d %H:%M:%S] ') + "Wish list : " + str(wish_list))
            time.sleep(0.2)
            post_message(myToken,slackchannel, datetime.now().strftime('[%m/%d %H:%M:%S] ') + "매수 횟수 : " + str(bought_cnt))
            time.sleep(0.2)
            heartbeat_flag = 1
        elif (29 <= now.minute <= 31 or now.minute <= 1 or now.minute >=59) is False:
            heartbeat_flag = 0
        

        # if start_time < now < end_time - timedelta(seconds=59):
        for sym in ticker_list:
            # 이동평균선의 기울기 계산
            # (1분전 종가 - 4분전 종가) / 1분전 종가 * 100
            previous_price = get_pre_price(sym)
            # ma5_diff = (get_ma(sym, 5, -2) - get_ma(sym, 5, -5)) / previous_price * 100
            # ma10_diff = (get_ma(sym, 10, -2) - get_ma(sym, 10, -5)) / previous_price * 100
            # ma20_diff = (get_ma(sym, 20, -2) - get_ma(sym, 20, -5)) / previous_price * 100

            # 3개의 이동평균선이 하향하고, 매수 목록에 없을때 해당 종목 리스트업
            # if ma5_diff < -0.05 and ma10_diff < -0.05 and ma20_diff < -0.05 :

            ma5_series = get_ma(sym,5)
            ma10_series = get_ma(sym,10)
            ma20_series = get_ma(sym,20)

            # (1분전 종가 - 6분전 종가) / 1분전 종가 * 100
            previous_price = get_pre_price(sym)
            ma5_diff = (ma5_series.iloc[-2] - ma5_series.iloc[-7]) / previous_price * 100
            ma10_diff = (ma10_series.iloc[-2] - ma10_series.iloc[-7]) / previous_price * 100
            ma20_diff = (ma20_series.iloc[-2] - ma20_series.iloc[-7]) / previous_price * 100

            ma5_diff_1min = (ma5_series.iloc[-2] - ma5_series.iloc[-3])

            # 3개의 이동평균선이 하향하고, 매수 목록에 없을때 해당 종목 리스트업
            if ma5_diff < -0.085 and ma10_diff < -0.085 and ma20_diff < -0.085  and ma5_diff_1min < 0:
                if sym not in bought_list:
                    if sym not in wish_list:
                        wish_list.append(sym)
                    bought_cnt[sym] = 0
                    # post_message(myToken,slackchannel, "위시 리스트 추가 : " + sym)                    
                else:
                    current_price = get_current_price(sym) 
                    buy_price = get_buy_price(sym)    # 매수 평균 가격
                    if buy_price > current_price:
                        if sym not in wish_list:
                            wish_list.append(sym)
                            post_message(myToken,slackchannel, datetime.now().strftime('[%m/%d %H:%M:%S] ') +  "위시 리스트 추가(추가 매수) : " + sym)
                            time.sleep(0.2)

            # print(ma5_diff, ma10_diff, ma20_diff, wish_list)

            # 추가 매수 도입으로 필요 없어졌다고 판단 - 210511
            # if len(bought_list) < target_count:
                # pass
            

            else:
                # 매수
                buy_coin(sym)            

            # 매도
            sell_coin(sym)
 
        # else:
        #     for sym in ticker_list:                
        #         sell_all(sym)

        # 모두 판매한 경우 구매 금액 다시 계산    
        if not bought_list:
            # 종목당 구매할 금액 계산
            unit_buy_amount = upbit.get_balance("KRW") * buy_rate
        
            # 최소 주문금액 
            if unit_buy_amount < 5100:
                unit_buy_amount = 5100         

        time.sleep(0.5)
    except Exception as e:
        print(datetime.now().strftime('[%m/%d %H:%M:%S] ') + str(sym) + " 메인 >> " + str(e))
        post_message(myToken,slackchannel, datetime.now().strftime('[%m/%d %H:%M:%S] ') + str(sym) + " 메인 >> " + str(e))
        geckoLogger.info(" 메인 >> " + str(e))
        time.sleep(0.5)