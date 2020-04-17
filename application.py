# import necessary libraries
from OpenSSL.SSL import SysCallError
from bs4 import BeautifulSoup
from collections import deque
from library import get_live_price
from library import Notify
from library import master_logger, trader_logger
from time import sleep
import requests
import argparse
import holidays
import datetime
import pytz
import json
import os


##############################################################

HEADING = '''
                        __           __  ____
              ___  ____/ /___ ______/ /_/ __ \\__  __
             / _ \\/ __  / __ `/ ___/ __/ /_/ / / / /
            /  __/ /_/ / /_/ / /  / /_/ ____/ /_/ /
            \\___/\\__,_/\\__,_/_/   \\__/_/    \\__, /
                                           /____/

'''
Notify.heading(HEADING)

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
BUFFER_PERCENT = 0.06
# number of observations of prices during initialisation phase, minimum value of 80
DATA_LIMIT = 80
# interval of each period, in seconds
PERIOD_INTERVAL = 60
# percentage of account_balance to be considered for trading
FEASIBLE_PERCENT = 0.2  # 20%

##############################################################

# time delay to check if market is open, in seconds
DELAY = 300
# delay in idle phase, in seconds
IDLE_DELAY = 1800
# time to stop trading
PACK_UP = datetime.time(hour=15, minute=15, second=0)

##############################################################

ml = master_logger(f'database/{datetime.date.today().strftime("%d-%m-%Y")}/master.log')
ml.info("----------------------------------------------------------------------------")
##############################################################

try:
    ACCOUNT = json.loads(open("database/user_info.json").read())["account_balance"] * FEASIBLE_PERCENT
except FileNotFoundError:
    Notify.fatal('User info not found, Aborting.')
    ml.critical("User info not found")
    quit(0)
ml.info("Successfully loaded user_info.json")
##############################################################

HEADERS = {
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/80.0.3987.163 Safari/537.36"
}

##############################################################

parser = argparse.ArgumentParser(prog="application.py",
                                 description="A fully automated Pythonic trading bot\n\nAuthor : Ashwin A Nayar",
                                 epilog="Time for some real money !",
                                 formatter_class=argparse.RawTextHelpFormatter
                                 )

parser.add_argument("--delay", type=int, default=IDLE_DELAY,
                    help="Duration of Idle Phase, in seconds")

parser.add_argument("-nd", action="store_true",
                    help="Skip Idle Phase, not recommended")

parser.add_argument("-np", action="store_true",
                    help="Set period interval to zero, not recommended")

parser.add_argument("-t", action="store_true",
                    help='Run script in trial mode, for debugging purposes')

args = parser.parse_args()

if args.nd:
    if args.delay != IDLE_DELAY:
        Notify.fatal("Invalid set of arguments given. Aborting")
        ml.critical("Received no delay and custom delay")
        quit(0)
    else:
        IDLE_DELAY = 0
        ml.warning("Running in no delay mode")
else:
    IDLE_DELAY = args.delay
    ml.info(f"Idle delay set to {IDLE_DELAY}")

if args.np:
    PERIOD_INTERVAL = 0
    ml.warning("Running with zero period interval !")

if args.t:
    IDLE_DELAY = 1
    PERIOD_INTERVAL = 0
    ml.warning("Running in test mode")

# developer mode
DEV_MODE = args.nd and args.np
if DEV_MODE:
    PENNY_STOCK_THRESHOLD = 0
    ml.warning("Running in developer mode")

##############################################################


def print_progress_bar(iteration, total, prefix='', suffix='', decimals=1, length=100, fill='█', printEnd="\r"):
    """
        Call in a loop to create terminal progress bar
        @params:
            iteration   - Required  : current iteration (Int)
            total       - Required  : total iterations (Int)
            prefix      - Optional  : prefix string (Str)
            suffix      - Optional  : suffix string (Str)
            decimals    - Optional  : positive number of decimals in percent complete (Int)
            length      - Optional  : character length of bar (Int)
            fill        - Optional  : bar fill character (Str)
            printEnd    - Optional  : end character (e.g. "\r", "\r\n") (Str)
    """
    percent = ("{0:." + str(decimals) + "f}").format(100 * (iteration / float(total)))
    filledLength = int(length * iteration // total)
    bar = fill * filledLength + ' ' * (length - filledLength)
    print('\r%s |%s| %s%% %s' % (prefix, bar, percent, suffix), end=printEnd)
    # print new line on complete
    if iteration == total:
        print()


def is_open():
    """
        Function to check if market is open at the moment

    Returns:
        True if market is open, False otherwise

    """
    global ml

    now = datetime.datetime.now(TZ)
    # if a holiday
    if now.strftime('%Y-%m-%d') in INDIA_HOLIDAYS:
        ml.error("Holiday ! ")
        return False
    # if before opening or after closing
    if (now.time() < OPEN_TIME) or (now.time() > CLOSE_TIME):
        ml.error("Market closed.")
        return False
    # if it is a weekend
    if now.date().weekday() > 4:
        ml.error("Weekday !")
        return False
    return True


def fetch_stocks():
    """
        Find relevant stocks to focus on for trading
    Returns:
        Deque of tickers of relevant stocks

    """
    # url to grab data from
    url = f'https://in.finance.yahoo.com/gainers?count={NUM_OF_STOCKS_TO_SEARCH}'
    # request header
    headers = {
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/79.0.3945.130 Safari/537.36'}
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
            ticker = row_data[0].text.strip()
            price = get_live_price(ticker)
            # split ticker for checking if same stock of different stock exchange is selected or not
            stock_name, stock_ex = ticker.split(".")
            if price >= PENNY_STOCK_THRESHOLD and stock_name not in stocks_temp:
                stocks_temp[stock_name] = stock_ex
                count += 1
    # get back ticker
    for stock in stocks_temp:
        stocks.append(f"{stock}.{stocks_temp[stock]}")
    # return deque of stocks to focus on
    return stocks


def get_value(ref: list, x_src: list, x: float) -> float:
    """
        Helper function for traders, used to find Ichimoku components corresponding to entry from other components or price
    Args:
        ref: iterable from which corresponding entry should be found
        x_src: iterable containing param x
        x: an item, maybe a component value, maybe price

    Returns:

    """
    return ref[x_src.index(x)]


class Trader:
    def __init__(self, number, ticker):
        self.number = number
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
        # check if allotted stock has been sold the previous day or not, short trade
        if self.ticker in prev_data["stocks_to_buy_back"]:
            price = prev_data["stocks_to_buy_back"][self.ticker]["buffer_price"]
            self.IN_SHORT_TRADE = True
            self.price_for_buffer = price
        self.logger = trader_logger(self.ticker)

    def get_initial_data(self):
        try:
            self.price.append(get_live_price(self.ticker))
            self.logger.debug("Successfully fetched live price")
        except SysCallError:
            Notify.warn(f"[Trader #{self.number} {self.ticker}]: Encountered SysCallError while initialising parameters, trying recursion")
            self.logger.warning("Encountered SysCallError, trying recursion")
            self.get_initial_data()
        except Exception as e:
            Notify.warn(f"[Trader #{self.number} {self.ticker}]: Exception in getting initial data, trying recursion")
            self.logger.error("Trying recursion due to uncommon Exception : ", e)
            self.get_initial_data()

    def buy(self, price, trade):
        global ACCOUNT
        now = datetime.datetime.now(TZ).strftime('%H:%M:%S')
        self.bought_price = price
        self.logger.info("Bought stock, in ", trade, " trade, for ", price, " INR")
        ACCOUNT -= price
        self.database['Activity'][now] = {
            "trade": trade,
            "bought at": price
        }

    def sell(self, price, trade):
        global ACCOUNT
        now = datetime.datetime.now(TZ).strftime('%H:%M:%S')
        self.sold_price = price
        self.logger.info("Sold stock, in ", trade, " trade, for ", price, " INR")
        ACCOUNT += price
        self.database['Activity'][now] = {
            "trade": trade,
            "sold at": price
        }

    def update_price(self):
        try:
            new_price = get_live_price(self.ticker)
            self.price.append(new_price)
            self.logger.info("Successfully fetched price, local database updated")
        except SysCallError:
            Notify.warn(f"[Trader #{self.number} {self.ticker}] : Encountered SysCallError in updating price, trying recursion")
            self.logger.warning("Encountered SysCallError while fetching live price, trying recursion")
            self.update_price()
        except Exception as e:
            Notify.warn(f"[Trader #{self.number} {self.ticker}] : Exception in updating price, trying recursion")
            self.logger.error("Trying recursion, encountered uncommon exception : ", e)
            self.update_price()

    def update_data(self):
        self.update_price()
        self.time.append(self.time[-1] + 1)
        del self.time[0], self.price[0]

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
        tenkan = self.tenkan_data[-1]
        kijun = self.kijun_data[-1]
        sen_A = get_value(self.senkou_A_data, self.x5, x)
        sen_B = get_value(self.senkou_B_data, self.x6, x)
        self.logger.info(f"Current status - Price : {curr_price}, Tenkan : {tenkan}, Kijun : {kijun}, Senkou A : {sen_A}, Senkou B : {sen_B}")

        # conditions for long trade entry
        # If Kumo cloud is green and current price is above kumo, strong bullish signal
        cond1 = (sen_A > sen_B) and (curr_price >= sen_A)
        if cond1:
            self.logger.debug("Sensing strong bullish signal")
        # conditions for short trade entry
        # If Kumo cloud is red and current price is below kumo, strong bearish signal
        cond2 = (sen_A < sen_B) and (curr_price <= sen_A)
        if cond2:
            self.logger.debug("Sensing strong bearish signal")
        # check allocated money
        cond3 = curr_price < ACCOUNT

        # IF all conditions are right, long trade entry
        if cond1 and not self.IN_LONG_TRADE and cond3:
            self.buy(curr_price, "LONG")
            self.price_for_buffer = curr_price
            self.IN_LONG_TRADE = True
            self.STOCKS_TO_SELL += 1
        if not cond3:
            Notify.fatal(f"[Trader #{self.number} {self.ticker}] : Oops! Out of cash!")
            self.logger.critical("Trader out of cash to buy stocks!")
        # If all conditions are right, short trade entry
        if cond2 and not self.IN_SHORT_TRADE:
            self.sell(curr_price, "SHORT")
            self.price_for_buffer = curr_price
            self.IN_SHORT_TRADE = True
            self.STOCKS_TO_BUY_BACK += 1

        # setup buffer for stop loss and trade exit
        buffer = self.price_for_buffer * BUFFER_PERCENT
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
                Notify.fatal(f"[Trader #{self.number} {self.ticker}] : Oops! Out of cash!")
                self.logger.critical("Trader out of cash to buy back stock !")

    # group update and decision call for convenience
    def run(self):
        self.update_data()
        self.make_decision()

    def __del__(self):
        with open(self.ticker + ".json", "w") as fp:
            fp.write(json.dumps(self.database, indent=4))
        self.logger.critical("Trader killed")


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
        global ml
        count = 1
        for ticker in tickers:
            self.traders.append(Trader(count, ticker))
            count += 1
        ml.info("Trader lineup complete")

    # initialise traders
    def init_traders(self, Tmode=False):
        global ml

        Notify.info("Traders are in Observation phase")
        ml.info("Traders entered Observation Phase")
        if not Tmode:
            print_progress_bar(0, 80, prefix='\tProgress:', suffix='Complete', length=40)
            for i in range(DATA_LIMIT):
                for trader in self.traders:
                    trader.get_initial_data()
                print_progress_bar(i + 1, 80, prefix='\tProgress:', suffix='Complete', length=40)
                sleep(PERIOD_INTERVAL)
        Notify.info("\tStatus : Complete")
        ml.info("Observation Phase complete")
        print("")

    # trading begins
    def start_trading(self, Tmode=False):
        global ml

        now = datetime.datetime.now(TZ)
        Notify.info("Trading has begun")
        ml.info("Trading has begun")
        count = 1
        if not Tmode:
            while now.time() < PACK_UP or DEV_MODE:
                try:
                    for trader in self.traders:
                        trader.run()
                    ml.info("Completed round #", count)
                    sleep(PERIOD_INTERVAL)
                except Exception as e:
                    Notify.fatal("Trading has been aborted")
                    ml.critical("Trade abort due to unexpected error : ", e)
                    quit(0)
                finally:
                    now = datetime.datetime.now(TZ)
                    count += 1
        else:
            Notify.info("Confirming access to live stock price...")
            ml.info("Confirming access to live stock price...")
            for trader in self.traders:
                try:
                    get_live_price(trader.ticker)
                except Exception as e:
                    Notify.fatal("Error in fetching live stock price. Aborting")
                    ml.critical("Error in fetching live stock price : ", e)

    # save master data
    def __del__(self):
        global ACCOUNT, ml
        # load previous day's data
        prev_data = json.loads(open("..\\user_info.json").read())
        username = prev_data['username']
        # debug
        account_balance_prev = prev_data["account_balance"]
        # get new data from trader's database
        account_balance_new = account_balance_prev * (1 - FEASIBLE_PERCENT) + ACCOUNT
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
                new_data["stocks_to_sell"][trader.ticker] = {"buffer_price": trader.price_for_buffer}
            # check owed stocks
            if trader.IN_SHORT_TRADE:
                new_data["stocks_to_buy_back"][trader.ticker] = {"buffer_price": trader.price_for_buffer}
            # save trader database in respective files
            del trader
        # save master database
        with open("..\\user_info.json", "w") as fp:
            fp.write(json.dumps(new_data, indent=4))
        # output profit
        Notify.info(f"\n\nNet Profit : {profit} INR\n")
        ml.info(f"\n\nNet Profit : {profit} INR\n")
        Notify.info(f'Stocks owned : {len(new_data["stocks_to_sell"])}')
        ml.info(f'Stocks owned : {len(new_data["stocks_to_sell"])}')
        Notify.info(f'Stocks owed : {len(new_data["stocks_to_buy_back"])}')
        ml.info(f'Stocks owed : {len(new_data["stocks_to_buy_back"])}')


def main():
    """
        Main Function
    """
    # make sure that market is open
    if not DEV_MODE:
        if is_open():
            pass
        else:
            Notify.fatal("Market is closed at the moment, aborting.")
            print("")
            quit(0)
    else:
        Notify.warn("You are in developer mode, if not intended, please quit.")
        input()

    # allow market to settle to launch Ichimoku strategy
    if IDLE_DELAY == 0:
        Notify.info("Skipped Idle phase")
    else:
        Notify.info(f"Entered Idle phase at {datetime.datetime.now(TZ).strftime('%H:%M:%S')}")
        ml.info(f"Entered Idle phase")
        Notify.info(f"\tExpected release : after {IDLE_DELAY // 60} minutes")
        print("")
        sleep(IDLE_DELAY)

    ml.info("Idle phase complete")
    # find relevant stocks to focus on
    Notify.info("Finding stocks to focus on .....")
    try:
        stocks_to_focus = fetch_stocks()
    except Exception as e:
        stocks_to_focus = []
        ml.critical("Could not fetch relevant stocks : ", e)
        quit(0)
    Notify.info("\tStatus : Complete")
    ml.info("Successfully found relevant stocks")
    print("")
    print(stocks_to_focus)
    print("")
    print("")

    # setup traders and begin trade
    master = Master()
    master.validate_repo()
    master.lineup_traders(stocks_to_focus)
    master.init_traders(args.t)
    master.start_trading(args.t)

    # trading in over by this point
    Notify.info("Trading complete")
    ml.info("Trading complete")

    # initiate packup
    del master
    quit(0)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        Notify.fatal("Operation cancelled by user.")
        ml.critical("Operation cancelled by user")
        quit(0)
