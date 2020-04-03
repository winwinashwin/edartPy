# import necessary libraries
# from yahoo_fin.stock_info import get_live_price
from my_fin.stock_info import get_live_price
from bs4 import BeautifulSoup
from collections import deque
from CONSTANTS import *
import datetime
import requests
import json


# function to check if market is open or closed
def is_open():
	now = datetime.datetime.now(TZ)
	# if a holiday
	if now.strftime('%Y-%m-%d') in INDIA_HOLIDAYS:
		return False
	# if before opening or after closing
	if (now.time() < OPEN_TIME) or (now.time() > CLOSE_TIME):
		return False
	# if it is a weekend
	if now.date().weekday() > 4:
		return False
	return True


# returns a list of stocks to focus on
def fetch_stocks():
    # url to grab data from
    url = f'https://in.finance.yahoo.com/gainers?count={NUM_OF_STOCKS_TO_SEARCH}'
    # request header
    headers = {
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/79.0.3945.130 Safari/537.36'
        }
    src = requests.get(url=url, headers= headers).content
    # soup of parsed html
    soup = BeautifulSoup(src, "html.parser")
    rows = soup.find('table').tbody.find_all('tr')
    # initialisations
    stocks_temp, count = dict(), 0
    stocks = deque()
    # iterate over rows in web page
    for tr in rows:
    	# exit if 
        if count == NUM_OF_STOCKS_TO_FOCUS:
            break
        else:
            row_data = tr.find_all('td')
            price = float(row_data[2].text.strip().replace(',', ""))
            # split ticker for checking if same stock of diff stock exchage if selected or not
            stock_name, stock_ex = row_data[0].text.strip().split(".")
            if price >= PENNY_STOCK_THRESHOLD and stock_name not in stocks_temp:
                stocks_temp[stock_name] = stock_ex
                count += 1
    # get back ticker
    for stock in stocks_temp:
    	stocks.append(f"{stock}.{stocks_temp[stock]}")
    # return deque of stocks to focus on
    return stocks


# helper function for trader
def get_value(ref, x_src, x):
	return ref[x_src.index(x)]


class Trader:
	def __init__(self, ticker):
		self.ticker = ticker
		self.time = deque(i for i in range(-25, DATA_LIMIT + 27))
		self.price = deque()
		self.tenkan_data = deque()
		self.kijun_data = deque()
		self.chikou_data = deque()
		self.senkou_A_data = deque()
		self.senkou_B_data = deque()

		self.IN_SHORT_TRADE = False
		self.IN_LONG_TRADE = False
		self.price_for_buffer = 0
		self.ACCOUNT = 0
		self.STOCKS_TO_SELL = 0
		self.STOCKS_TO_BUY_BACK = 0

	def get_initial_data(self):
		for i in range(DATA_LIMIT):
			self.price.append(get_live_price(self.ticker))
			progress = round(i*100/DATA_LIMIT, 1)
			print()

	def buy(self, price):
		self.bought_price = price
		self.ACCOUNT -= price

	def sell(self, price):
		self.sold_price = price
		self.ACCOUNT += price

	def update_data(self):
		new_price = get_live_price(self.ticker)
		self.time.append(self.time[-1] + 1)
		self.price.append(new_price)
		self.time.__delitem__(0)
		self.price.__delitem__(0)

	def make_decision(self):
		self.tenkan_data = []
		for i in range(DATA_LIMIT - 9):
			tenkan_src = self.price[i:i + 9]
			self.tenkan_data.append((max(tenkan_src) + min(tenkan_src)) / 2)
		self.kijun_data = []
		for i in range(DATA_LIMIT - 26):
			kijun_src = self.price[i:i + 26]
			self.kijun_data.append((max(kijun_src) + min(kijun_src)) / 2)
		self.x5 = self.time[78:78 + DATA_LIMIT - 26]
		self.x6 = self.time[104:104 + DATA_LIMIT - 52]
		self.senkou_A_data = [(self.tenkan_data[i + 17] + self.kijun_data[i]) / 2 for i in range(DATA_LIMIT - 26)]
		self.senkou_B_data = []
		for i in range(DATA_LIMIT - 52):
			senkou_B_src = self.price[i:i + 52]
			self.senkou_B_data.append((max(senkou_B_src) + min(senkou_B_src)) / 2)

		x = self.time[26:26 + DATA_LIMIT][-1]
		curr_price = self.price[-1]
		tenkan = self.tenkan_data[-1]
		kijun = self.kijun_data[-1]
		sen_A = get_value(self.senkou_A_data, self.x5, x)
		sen_B = get_value(self.senkou_B_data, self.x6, x)

		# conditions for long trade entry
		cond1 = sen_A > sen_B and curr_price >= sen_A
		# conditions for short trade entry
		cond2 = sen_A < sen_B and curr_price <= sen_A

		# for trade entry
		if cond1 and not self.IN_LONG_TRADE:
			self.buy(curr_price)
			self.price_for_buffer = curr_price
			self.IN_LONG_TRADE = True
			self.STOCKS_TO_SELL += 1
		if cond2 and not self.IN_SHORT_TRADE:
			self.sell(curr_price)
			self.price_for_buffer = curr_price
			self.IN_SHORT_TRADE = True
			self.STOCKS_TO_BUY_BACK += 1

		# setup buffer for stop loss and trade exit
		buffer = self.price_for_buffer*BUFFER_PERCENT
		cond3 = abs(curr_price - kijun) >= buffer

		# for trade exit
		if self.IN_LONG_TRADE:
			if cond3:
				self.sell(curr_price)
				self.IN_LONG_TRADE = False
				self.STOCKS_TO_SELL -= 1
		if self.IN_SHORT_TRADE:
			if cond3:
				self.buy(curr_price)
				self.IN_SHORT_TRADE = False
				self.STOCKS_TO_BUY_BACK -= 1

	def run(self):
		self.update_data()
		self.make_decision()


if __name__ == "__main__":
	print(fetch_stocks())
