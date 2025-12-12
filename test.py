# 필요한 모듈 불러오기
import requests
import pandas as pd
import time
from datetime import datetime
import numpy as np

# 디스코드 웹훅 주소
webhook = "https://discord.com/api/webhooks/1446378689695846490/5twJMMsdskIP4VccLz489aIe_WrXJK61qGkKm13SGWBNvuyQh6NdqPIOJMYmbQiQwF2O"

# 설정 값들
coin = "KRW-BTC"
k = 0.5
rsi_기간 = 14
과매도 = 45
거래량_배수 = 1.5
잠깐_잘_시간 = 60

# 디스코드 알림 보내는 함수

def 디스코드보내기(msg):
    try:
        data = {}
        data["content"] = msg
        requests.post(webhook, json=data)
        print("디스코드 보냄")
    except:
        print("디스코드 실패")

# RSI 계산 함수

def RSI계산(가격들):
    차이 = 가격들.diff()
    올라감 = []
    내려감 = []
    for i in range(len(차이)):
        if i == 0:
            올라감.append(0)
            내려감.append(0)
        else:
            if 차이.iloc[i] > 0:
                올라감.append(차이.iloc[i])
                내려감.append(0)
            else:
                올라감.append(0)
                내려감.append(-차이.iloc[i])
    올라감평균 = pd.Series(올라감).rolling(rsi_기간).mean()
    내려감평균 = pd.Series(내려감).rolling(rsi_기간).mean()
    RS = 올라감평균 / 내려감평균
    RSI = 100 - (100 / (1 + RS))
    return RSI.iloc[-1]

# 백테스팅 함수

def 백테스팅():
    print("백테스팅 시작함")
    모든 = []
    for i in range(12):
        if i == 0:
            주소 = "https://api.upbit.com/v1/candles/minutes/60?market=" + coin + "&count=200"
        else:
            마지막 = 모든[-1]["candle_date_time_kst"]
            주소 = "https://api.upbit.com/v1/candles/minutes/60?market=" + coin + "&count=200&to=" + 마지막
        결과 = requests.get(주소).json()
        if 결과 == None or len(결과) == 0:
            break
        for d in 결과:
            모든.append(d)
        time.sleep(0.2)

    if len(모든) < 100:
        print("데이터 부족")
        return

    df = pd.DataFrame(모든)
    df = df.sort_values("candle_date_time_kst").reset_index(drop=True)
    df["종가"] = df["trade_price"].astype(float)

    rsi값들 = []
    for i in range(len(df)):
        if i < rsi_기간:
            rsi값들.append(50)
        else:
            최근 = df["종가"].iloc[i-rsi_기간+1:i+1]
            값 = RSI계산(최근)
            if np.isnan(값):
                값 = 50
            rsi값들.append(값)
    df["RSI"] = rsi값들

    범위 = []
    for i in range(len(df)):
        범위.append(df["high_price"].iloc[i] - df["low_price"].iloc[i])
    df["범위"] = 범위

    목표 = [None]*len(df)
    전일거래량 = [None]*len(df)
    for i in range(24, len(df)):
        목표[i] = df["opening_price"].iloc[i-24] + df["범위"].iloc[i-24]*k
        전일거래량[i] = df["candle_acc_trade_volume"].iloc[i-24]
    df["목표가"] = 목표
    df["전일거래량"] = 전일거래량

    매매 = 0
    수익 = []

    for i in range(len(df)):
        if i < 50:
            continue
        고가 = df["high_price"].iloc[i]
        목표가 = df["목표가"].iloc[i]
        rsi = df["RSI"].iloc[i]
        오늘 = df["candle_acc_trade_volume"].iloc[i]
        어제 = df["전일거래량"].iloc[i]

        if 목표가 is None or 어제 is None:
            continue

        if 고가 >= 목표가 and rsi <= 과매도 and 오늘 >= 어제 * 거래량_배수:
            매매 += 1
            if i+1 < len(df):
                다음 = df["opening_price"].iloc[i+1]
            else:
                다음 = df["trade_price"].iloc[i]
            수익률 = (다음/목표가 - 1) * 100
            수익.append(수익률)

    if 매매 > 0:
        승 = 0
        for x in 수익:
            if x > 0:
                승 += 1
        승률 = 승 / 매매 * 100
        총 = sum(수익)
    else:
        승률 = 0
        총 = 0

    print("==============================")
    print("백테스트 결과")
    print("매매:", 매매)
    print("승률:", round(승률,1), "%")
    print("총 수익:", round(총,2), "%")
    if 매매 > 0:
        print("평균 수익률:", round(총/매매,2), "%")
    print("==============================")

# 현재 상태 함수

def 지금상태():
    캔 = requests.get("https://api.upbit.com/v1/candles/minutes/60?market=" + coin + "&count=50").json()
    캔.reverse()
    df = pd.DataFrame(캔)
    현재rsi = RSI계산(df["trade_price"])
    어제 = 캔[-2]
    목표가 = 어제["opening_price"] + (어제["high_price"] - 어제["low_price"]) * k
    가격 = requests.get("https://api.upbit.com/v1/ticker?markets=" + coin).json()[0]["trade_price"]
    거래량비 = 캔[-1]["candle_acc_trade_volume"] / 어제["candle_acc_trade_volume"]

    print("=========================")
    print("현재 상태")
    print("가격:", 가격)
    print("목표가:", 목표가)
    print("RSI:", round(현재rsi,2))
    print("거래량배수:", round(거래량비,2))
    print("=========================")

# 실시간 감시

def 실시간감시():
    print("실시간 감시 시작")
    마지막 = None

    while True:
        try:
            캔 = requests.get("https://api.upbit.com/v1/candles/minutes/60?market=" + coin + "&count=50").json()
            캔.reverse()
            df = pd.DataFrame(캔)
            rsi = RSI계산(df["trade_price"])
            어제 = 캔[-2]
            목표가 = 어제["opening_price"] + (어제["high_price"] - 어제["low_price"]) * k
            가격 = requests.get("https://api.upbit.com/v1/ticker?markets=" + coin).json()[0]["trade_price"]
            거래량비 = 캔[-1]["candle_acc_trade_volume"] / 어제["candle_acc_trade_volume"]

            지금 = datetime.now().strftime("%m/%d %H:%M")
            print("["+지금+"]", 가격, "목표", 목표가, "RSI", round(rsi,1), "거래량", round(거래량비,1))

            조건1 = 가격 > 목표가
            조건2 = rsi <= 과매도
            조건3 = 거래량비 >= 거래량_배수

            if 조건1 and 조건2 and 조건3:
                보냄 = False
                if 마지막 == None:
                    보냄 = True
                else:
                    차이 = (datetime.now() - 마지막).seconds
                    if 차이 > 600:
                        보냄 = True
                if 보냄:
                    메시지 = "매수 신호!! 시간: " + 지금 + " 가격:" + str(가격)
                    디스코드보내기(메시지)
                    마지막 = datetime.now()
            time.sleep(잠깐_잘_시간)
        except Exception as e:
            print("에러", e)
            time.sleep(10)

# 시작
if __name__ == "__main__":
    print("1. 백테스트")
    print("2. 현재 상태")
    print("3. 실시간 감시")
    선택 = input("번호 선택: ")

    if 선택 == "1":
        백테스팅()
    elif 선택 == "2":
        지금상태()
    elif 선택 == "3":
        실시간감시()
    else:
        print("잘못 입력함")
