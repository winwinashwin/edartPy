# import necessary libraries
from yahoo_fin.stock_info import get_live_price
from bs4 import BeautifulSoup
from collections import deque
from time import sleep
import requests
import holidays
import datetime
import pytz
import json
import os


##############################################################

# set time zone
TZ = pytz.timezone('Asia/Calcutta')
# set holidays
INDIA_HOLIDAYS = holidays.India()
# set market open time
OPEN_TIME = datetime.time(hour=9, minute=15, second=0)
# set market close time
CLOSE_TIME = datetime.time(hour=15, minute=30, second=0)

##############################################################

# only those stocks will be considered whose price is above threshold
PENNY_STOCK_THRESHOLD = 50
# number of stocks to select relevant ones from
NUM_OF_STOCKS_TO_SEARCH = 100
# number of stocks to focus trading on
NUM_OF_STOCKS_TO_FOCUS = 5
# percentage buffer to be set for stop loss/trade exit
BUFFER_PERCENT = 0.09
# number of observations of prices during initialisation phase, minimum value of 80
DATA_LIMIT = 80
# interval of each period, in seconds
PERIOD_INTERVAL = 60  # 1 minute
# percentage of account_balance to be considered for trading
FEASIBLE_PERCENT = 0.2  # 20%

##############################################################

# time delay to check if market is open, in seconds
DELAY = 300
# delay in idle phase, in seconds
IDLE_DELAY = 1800
# time to stop trading
PACKUP = datetime.time(hour=15, minute=15, second=0)

##############################################################

ACCOUNT = json.loads(open("database/user_info.json").read())["account_balance"] * FEASIBLE_PERCENT

##############################################################


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
	headers = {'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/79.0.3945.130 Safari/537.36'}
	src = requests.get(url=url, headers=headers).content
	# soup object of source code
	soup = BeautifulSoup(src, "html.parser")
	rows = soup.find('table').tbody.find_all('tr')
	# initialisations
	stocks_temp = dict()
	# check previous day's closing status
	prev_data = json.loads(open("database/user_info.json").read())
	for ticker in prev_data["stocks_to_sell"]:
		stock_name, stock_ex = ticker.split(".")
		stocks_temp[stock_name] = stock_ex
	for ticker in prev_data["stocks_to_buy_back"]:
		stock_name, stock_ex = ticker.split(".")
		stocks_temp[stock_name] = stock_ex
	# set counter
	count = len(stocks_temp)
	stocks = deque()
	# iterate over rows in web page
	for tr in rows:
		# exit if
		if count == NUM_OF_STOCKS_TO_FOCUS:
			break
		else:
			row_data = tr.find_all('td')
			price = float(row_data[2].text.strip().replace(',', ""))
			# split ticker for checking if same stock of different stock exchange is selected or not
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
		# store x values, equivalent to time
		self.time = [i for i in range(-25, DATA_LIMIT + 27)]
		# list for storing live price
		self.price = []
		# lists for storing Ichimoku params
		self.tenkan_data = []
		self.kijun_data = []
		self.chikou_data = []
		self.senkou_A_data = []
		self.senkou_B_data = []
		# x values for senkou A and senkou B
		self.x5 = []
		self.x6 = []
		# database to save activity of trader
		self.database = dict()
		self.database["Ticker"] = self.ticker
		self.database["Activity"] = dict()
		# other params used within trader class
		self.IN_SHORT_TRADE = False
		self.IN_LONG_TRADE = False
		self.STOCKS_TO_SELL = 0
		self.STOCKS_TO_BUY_BACK = 0
		self.price_for_buffer = 0
		self.sold_price = 0
		self.bought_price = 0
		# set params in accordance with previous day's data
		prev_data = json.loads(open("../user_info.json").read())
		# check if allotted stock has been bought the previous day or not, long trade
		if self.ticker in prev_data["stocks_to_sell"]:
			price = prev_data["stocks_to_sell"][self.ticker]["buffer_price"]
			self.IN_LONG_TRADE = True
			self.price_for_buffer = price
		# check if alloted stock has been sold the previos day or not, short trade
		if self.ticker in prev_data["stocks_to_buy_back"]:
			price = prev_data["stocks_to_buy_back"][self.ticker]["buffer_price"]
			self.IN_SHORT_TRADE = True
			self.price_for_buffer = price

	# initialise Ichimoku indicator
	def get_initial_data(self):
		for i in range(DATA_LIMIT):
			self.price.append(get_live_price(self.ticker))

	def buy(self, price, trade):
		global ACCOUNT
		now = datetime.datetime.now(TZ).strftime('%H:%M:%S')
		self.bought_price = price
		ACCOUNT -= price
		self.database['Activity'][now] = {
			"trade": trade,
			"bought at": price
		}

	def sell(self, price, trade):
		global ACCOUNT
		now = datetime.datetime.now(TZ).strftime('%H:%M:%S')
		self.sold_price = price
		ACCOUNT += price
		self.database['Activity'][now] = {
			"trade": trade,
			"sold at": price
		}

	# function to update data with new price
	def update_data(self):
		new_price = get_live_price(self.ticker)
		self.time.append(self.time[-1] + 1)
		self.price.append(new_price)
		self.time.__delitem__(0)
		self.price.__delitem__(0)

	# observe indicator and decide buy and sell
	def make_decision(self):
		global ACCOUNT
		# update tenkan data
		self.tenkan_data = []
		for i in range(DATA_LIMIT - 9):
			tenkan_src = self.price[i:i + 9]
			self.tenkan_data.append((max(tenkan_src) + min(tenkan_src)) / 2)
		# update kijun data
		self.kijun_data = []
		for i in range(DATA_LIMIT - 26):
			kijun_src = self.price[i:i + 26]
			self.kijun_data.append((max(kijun_src) + min(kijun_src)) / 2)
		# update x values for senkou A and senkou B
		self.x5 = self.time[78:78 + DATA_LIMIT - 26]
		self.x6 = self.time[104:104 + DATA_LIMIT - 52]
		# update senkou A data
		self.senkou_A_data = [(self.tenkan_data[i + 17] + self.kijun_data[i]) / 2 for i in range(DATA_LIMIT - 26)]
		# update senkou B data
		self.senkou_B_data = []
		for i in range(DATA_LIMIT - 52):
			senkou_B_src = self.price[i:i + 52]
			self.senkou_B_data.append((max(senkou_B_src) + min(senkou_B_src)) / 2)

		# get Ichimoku params for comparison
		x = self.time[26:26 + DATA_LIMIT][-1]
		curr_price = self.price[-1]
		kijun = self.kijun_data[-1]
		sen_A = get_value(self.senkou_A_data, self.x5, x)
		sen_B = get_value(self.senkou_B_data, self.x6, x)

		# conditions for long trade entry
		# If Kumo cloud is green and current price is above kumo, strong bullish signal
		cond1 = (sen_A > sen_B) and (curr_price >= sen_A)
		# conditions for short trade entry
		# If Kumo cloud is red and current price is below kumo, strong bearish signal
		cond2 = (sen_A < sen_B) and (curr_price <= sen_A)
		# check allocated money
		cond3 = curr_price < ACCOUNT

		# IF all conditions are right, long trade entry
		if cond1 and not self.IN_LONG_TRADE and cond3:
			self.buy(curr_price, "LONG")
			self.price_for_buffer = curr_price
			self.IN_LONG_TRADE = True
			self.STOCKS_TO_SELL += 1
		if not cond3:
			print("Oops! Out of cash!")
		# If all conditions are right, short trade entry
		if cond2 and not self.IN_SHORT_TRADE:
			self.sell(curr_price, "SHORT")
			self.price_for_buffer = curr_price
			self.IN_SHORT_TRADE = True
			self.STOCKS_TO_BUY_BACK += 1

		# setup buffer for stop loss and trade exit
		buffer = self.price_for_buffer*BUFFER_PERCENT
		cond4 = abs(curr_price - kijun) >= buffer

		# Get stopped out as the price moves through the buffer area beyond the Kijun
		if self.IN_LONG_TRADE:
			if cond4:
				self.sell(curr_price, "LONG")
				self.IN_LONG_TRADE = False
				self.STOCKS_TO_SELL -= 1
		if self.IN_SHORT_TRADE:
			if cond4 and cond3:
				self.buy(curr_price, "SHORT")
				self.IN_SHORT_TRADE = False
				self.STOCKS_TO_BUY_BACK -= 1
			if not cond3:
				print("Oops! Out of cash!")

	# group updation and decision call for convenience
	def run(self):
		self.update_data()
		self.make_decision()

	def save_activity(self):
		with open(self.ticker+".json", "w") as fp:
			fp.write(json.dumps(self.database, indent=4))


# Manages all the traders
class Master:
	def __init__(self):
		self.traders = deque()

	# check if required directories exist, if not, make them
	@staticmethod
	def validate_repo():
		today = datetime.date.today().strftime("%d-%m-%Y")
		if not os.path.exists(".\\database"):
			os.mkdir("database")
		os.chdir("database")
		if not os.path.exists(today):
			os.mkdir(today)
		os.chdir(today)

	# allocate tickers to traders
	def lineup_traders(self, tickers):
		for ticker in tickers:
			self.traders.append(Trader(ticker))

	# initialise traders
	def init_traders(self):
		print(">>> Traders are in Observation phase")
		for _ in range(DATA_LIMIT):
			for trader in self.traders:
				trader.get_initial_data()
			sleep(PERIOD_INTERVAL)
		print("\tStatus : Complete")
		print("")

	# trading begins
	def start_trading(self):
		now = datetime.datetime.now(TZ)
		print(">>> Trading has begun")
		while now.time() < PACKUP:
			try:
				for trader in self.traders:
					trader.run()
				sleep(PERIOD_INTERVAL)
			except Exception as e:
				print("FATAL ERROR : Trading has been aborted")
				print(e)
				quit(0)
			finally:
				now = datetime.datetime.now(TZ)

	# save master data
	def packup(self):
		global ACCOUNT
		# load previous day's data
		prev_data = json.loads(open("..\\user_info.json").read())
		username = prev_data['username']
		account_balance_prev = prev_data["account_balance"]
		# get new data from trader's database
		account_balance_new = account_balance_prev*(1 - FEASIBLE_PERCENT) + ACCOUNT
		profit = account_balance_new - account_balance_prev
		# set up new data
		new_data = dict()
		new_data['username'] = username
		new_data["account_balance"] = account_balance_new
		new_data["stocks_to_sell"] = dict()
		new_data["stocks_to_buy_back"] = dict()
		# grab data from trader database
		for trader in self.traders:
			# check owned stocks
			if trader.IN_LONG_TRADE:
				new_data["stocks_to_sell"][trader.ticker]["buffer_price"] = trader.price_for_buffer
			# check owed stocks
			if trader.IN_SHORT_TRADE:
				new_data["stocks_to_buy_back"][trader.ticker]["buffer_price"] = trader.price_for_buffer
			# save trader database in respective files
			trader.save_activity()
		# save master database
		with open("..\\user_info.json", "w") as fp:
			fp.write(json.dumps(new_data, indent=4))
		# output profit
		print(f"\n\nNet Profit : {profit} INR\n")
		print(f'Stocks owned : {len(new_data["stocks_to_sell"])}')
		print(f'Stocks owed : {len(new_data["stocks_to_buy_back"])}')


if __name__ == "__main__":
	# make sure that market is open
	if is_open():
		pass
	else:
		print(">>> Market is closed at the moment, aborting.")
		print("")
		quit(0)

	# load maximum amount allowed to trade

	# allow market to settle to launch Ichimoku strategy
	print(f">>> Entered Idle phase at {datetime.datetime.now(TZ).strftime('%H:%M:%S')}")
	print(f"\tExpected release : after {IDLE_DELAY//60} minutes")
	print("")
	sleep(IDLE_DELAY)

	# find relevant stocks to focus on
	print(">>> Finding stocks to focus on .....")
	stocks_to_focus = fetch_stocks()
	print("")
	print(stocks_to_focus)
	print("")
	print("\tStatus : Complete")
	print("")

	# setup traders and begin trade
	master = Master()
	master.validate_repo()
	master.lineup_traders(stocks_to_focus)
	master.init_traders()
	master.start_trading()

	# trading in over by this point
	print(">>> Trading complete")

	# initiate packup
	master.packup()
	quit(0)
