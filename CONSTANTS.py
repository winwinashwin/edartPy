import holidays
import pytz
import datetime


# set time zone
TZ = pytz.timezone('Asia/Calcutta')
# set holidays
INDIA_HOLIDAYS = holidays.India()
# set market open time
OPEN_TIME = datetime.time(hour= 9, minute= 30, second= 0)
# set market close time
CLOSE_TIME = datetime.time(hour= 16, minute= 0, second= 0)
