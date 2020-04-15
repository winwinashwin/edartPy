import requests
import pandas as pd

try:
    from requests_html import HTMLSession
except Exception:
    print("""Warning - Certain functionality 
             requires requests_html, which is not installed.

             Install using: 
             pip install requests_html

             After installation, you may have to restart your Python session.""")


base_url = "https://query1.finance.yahoo.com/v8/finance/chart/"


def build_url(ticker, start_date=None, end_date=None, interval="1d"):

    if end_date is None:
        end_seconds = int(pd.Timestamp("now").timestamp())
    else:
        end_seconds = int(pd.Timestamp(end_date).timestamp())

    if start_date is None:
        start_seconds = 7223400
    else:
        start_seconds = int(pd.Timestamp(start_date).timestamp())

    site = base_url + ticker
    params = {"period1": start_seconds, "period2": end_seconds,
              "interval": interval.lower(), "events": "div,splits"}

    return site, params


def get_data(ticker, start_date = None, end_date = None, index_as_date = True, interval = "1d"):
    if interval not in ("1d", "1wk", "1mo"):
        raise AssertionError("interval must be of of '1d', '1wk', or '1mo'")

    # build and connect to URL
    site, params = build_url(ticker, start_date, end_date, interval)
    resp = requests.get(site, params = params, headers = {
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/80.0.3987.163 Safari/537.36"
    })

    if not resp.ok:
        raise AssertionError(resp.json())

    data = resp.json()

    frame = pd.DataFrame(data["chart"]["result"][0]["indicators"]["quote"][0])
    frame["adjclose"] = data["chart"]["result"][0]["indicators"]["adjclose"][0]["adjclose"]
    temp_time = data["chart"]["result"][0]["timestamp"]
    frame.index = pd.to_datetime(temp_time, unit = "s")
    frame.index = frame.index.map(lambda dt: dt.floor("d"))
    frame = frame[["open", "high", "low", "close", "adjclose", "volume"]]
    frame['ticker'] = ticker.upper()

    if not index_as_date:
        frame = frame.reset_index()
        frame.rename(columns = {"index": "date"}, inplace = True)

    return frame


def get_live_price(ticker):
    df = get_data(ticker, end_date=pd.Timestamp.today() + pd.DateOffset(10))
    return df.close[-1]
