# import necessary libraries
from yahoo_fin.stock_info import get_live_price
from CONSTANTS import *
import datetime
import requests
from bs4 import BeautifulSoup
from collections import deque


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


# find stocks to focus on
def fetch_stocks(num_of_stocks):
	# url to scrape data from
	url = "https://in.finance.yahoo.com/gainers"
	# request header 
	headers = {
		'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/79.0.3945.130 Safari/537.36'
	}
	# get source code of page and parse it
	src = request.get(url= url, headers= headers).content
	soup = BeautifulSoup(src, "html.parser")
	rows = soup.find('table').tbody.find_all("tr")

	stocks_temp = dict()
	stocks = deque()
	count = 0

	for tr in rows:
		if count == num_of_stocks:
			break
		else:
			stock_name, stock_ex = tr.find('td').text.strip().split(".")
			if stock_name in stocks_temp:
				continue
			else:
				stocks_temp[stock_name] = stock_ex
				count += 1

	for stock in stocks_temp:
		stocks.append(f"{stock}.{stocks_temp[stock]}")

	return stocks

class Trader:
	def __init__(self, ticker):
		self.ticker = ticker
		self.time = [i for i in range(-25, DATA_LIMIT + 27)]
		self.price = []
		self.tenkan_data = []
		self.kijun_data = []
		self.chikou_data = []
		self.senkou_A_data = []
		self.senkou_B_data = []

		self.IN_SHORT_TRADE = False
		self.IN_LONG_TRADE = False
		self.BUFFER_PERCENTAGE = 0.09
		self.price_for_buffer = 0
		self.ACCOUNT = 0
		self.STOCKS_TO_SELL = 0
		self.STOCKS_TO_BUY_BACK = 0

	def get_initial_data(self):
		for i in range(DATA_LIMIT):
			self.price.append(get_live_price(self.ticker))
			# time append
			progress = round(i*100/DATA_LIMIT, 1)

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
		buffer = self.price_for_buffer*self.BUFFER_PERCENTAGE
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

	def driver(self):
		self.update_data()
		self.make_decision()


if __name__ == "__main__":
	pass
