# import necessary libraries
from OpenSSL.SSL import SysCallError
from clint.textui import puts, colored
from library.stock_info import get_live_price
from bs4 import BeautifulSoup
from collections import deque
from time import sleep
import requests
import datetime
import pytz
import json
import os

##############################################################

# set time zone
TZ = pytz.timezone('Asia/Calcutta')
# set market open time
OPEN_TIME = datetime.time(hour=9, minute=15, second=0)
# set market close time
CLOSE_TIME = datetime.time(hour=15, minute=15, second=0)

##############################################################

# number of stocks to select relevant ones from
NUM_OF_STOCKS_TO_SEARCH = 100
# number of stocks to focus trading on
NUM_OF_STOCKS_TO_FOCUS = 5
# only those stocks will be considered whose price is above threshold
PENNY_STOCK_THRESHOLD = 50
# interval of each period, in seconds
PERIOD_INTERVAL = 60
# delay in idle phase, in seconds
IDLE_DELAY = 1800

##############################################################


class Notify:
    @staticmethod
    def info(message: 'str'):
        puts(colored.green("[ MESSAGE ]  ") + message)

    @staticmethod
    def warn(message: 'str'):
        puts(colored.cyan("[ WARNING ]  ") + message)

    @staticmethod
    def fatal(message: 'str'):
        puts(colored.red("[  FATAL  ]  ") + message)


class Miner:
    def __init__(self, number, ticker):
        self.number = number
        self.ticker = ticker
        self.database = {"ticker": self.ticker}
        self.subData = dict()
        Notify.info(f"Initialised Miner #{self.number} with {self.ticker}")

    def run(self):
        try:
            price = get_live_price(self.ticker)
        except SysCallError:
            Notify.warn(f"[Miner #{self.number} {self.ticker}]: Encountered SysCallError while fetching data, trying recursion")
            self.run()
        except Exception as e:
            Notify.warn(f"[Miner #{self.number} {self.ticker}]: Exception while fetching data, trying recursion")
            self.run()
        else:
            now = datetime.datetime.now(TZ)
            self.subData[now.strftime('%H:%M:%S')] = price
            # Notify.info(f"[Miner #{self.number} {self.ticker}]: Exception resolved")

    def __del__(self):
        self.database['data'] = self.subData
        fileName = self.ticker + ".json"
        with open(fileName, "w") as fp:
            fp.write(json.dumps(self.database, indent=4))

    def shutdown(self):
        self.__del__()


class Master:
    def __init__(self):
        self.miners = deque()

    def load_miners(self, stocks):
        for i, stock in enumerate(stocks):
            self.miners.append(Miner(i + 1, stock))

    def run(self, iteration):
        for miner in self.miners:
            miner.run()
        Notify.info(f"Iteration #{iteration} successful")

    def shutdown(self):
        for miner in self.miners:
            miner.shutdown()


def val_repo():
    if not os.path.exists("./database"):
        os.mkdir("database")
    os.chdir("database")


def is_open():
    now = datetime.datetime.now(TZ)
    # if before opening or after closing
    if (now.time() < OPEN_TIME) or (now.time() > CLOSE_TIME):
        return False
    # if it is a weekend
    if now.date().weekday() > 4:
        return False
    return True


def fetch_stocks():
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
    """
    # check previous day's closing status
    prev_data = json.loads(open("database/user_info.json").read())
    for ticker in prev_data["stocks_to_sell"]:
        stock_name, stock_ex = ticker.split(".")
        stocks_temp[stock_name] = stock_ex
    for ticker in prev_data["stocks_to_buy_back"]:
        stock_name, stock_ex = ticker.split(".")
        stocks_temp[stock_name] = stock_ex
    """
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


def main():
    val_repo()
    """
    while not is_open():
        Notify.warn("Market closed at the moment, next check after 2 minutes")
        sleep(120)
    """
    confo = input("Sleep ? (y/n) : ").lower()
    if confo == "y":
        Notify.info(f"Entered Idle phase at {datetime.datetime.now(TZ).strftime('%H:%M:%S')}")
        Notify.info(f"\tExpected release : after {IDLE_DELAY // 60} minutes")
        print("")
        sleep(IDLE_DELAY)

    try:
        Notify.info("Fetching stocks...")
        stocks = fetch_stocks()
    except Exception as e:
        stocks = None
        Notify.fatal("Error in fetching stocks. Aborting...")
        print(e)
        quit(0)

    master = Master()
    print(stocks)
    print("")
    master.load_miners(stocks)
    print("")
    Notify.info("Collecting stock data...")
    print("")
    now = datetime.datetime.now(TZ)
    iteration = 1
    # for _ in range(5):
    while now.time() < CLOSE_TIME:
        master.run(iteration)
        now = datetime.datetime.now(TZ)
        iteration += 1
        sleep(PERIOD_INTERVAL)

    master.shutdown()
    print("")
    Notify.info("Operation completed successfully")


if __name__ == "__main__":

    HEADING = '''
                            __           __  ____
                  ___  ____/ /___ ______/ /_/ __ \\__  __
                 / _ \\/ __  / __ `/ ___/ __/ /_/ / / / /
                /  __/ /_/ / /_/ / /  / /_/ ____/ /_/ /
                \\___/\\__,_/\\__,_/_/   \\__/_/    \\__, /
                                               /____/

    '''
    puts(colored.yellow(HEADING))

    try:
        main()
    except KeyboardInterrupt:
        Notify.fatal("Operation cancelled by user :(")
    except Exception as e:
        Notify.fatal("Fatal error in main function execution, Aborting")
        print(e)
