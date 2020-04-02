import holidays
import pytz
import datetime


##############################################################

# set time zone
TZ = pytz.timezone('Asia/Calcutta')
# set holidays
INDIA_HOLIDAYS = holidays.India()
# set market open time
OPEN_TIME = datetime.time(hour= 9, minute= 30, second= 0)
# set market close time
CLOSE_TIME = datetime.time(hour= 16, minute= 0, second= 0)

##############################################################

# only those stocks will be considered whose price is above threshold
PENNY_STOCK_THRESHOLD = 50
# number of stocks to select relevant ones from
NUM_OF_STOCKS_TO_SEARCH = 100
# number of stocks to focus trading on
NUM_OF_STOCKS_TO_FOCUS = 5
# percentage buffer to be set for stop loss/trade exit
BUFFER_PERCENT = 0.09

##############################################################
