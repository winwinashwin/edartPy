import logging


class LoggerFormatter(logging.Formatter):
	def __init__(self):
		super().__init__()
		self.datefmt = '%d-%b-%y %H:%M:%S'
		self.width = 8

	def format(self, record):
		level = record.levelname
		padding = self.width - len(level)
		time = self.formatTime(record, self.datefmt)
		return '[%s] [%s] %s :: %s' % (time, level, ''.ljust(padding), record.getMessage())


def master_logger():
	logger = logging.getLogger("main.log")
	logger.setLevel(logging.DEBUG)
	fh = logging.FileHandler("main.log")
	fh.setLevel(logging.DEBUG)
	fh.setFormatter(LoggerFormatter())
	logger.addHandler(fh)

	return logger


def trader_logger(ticker):
	logger = logging.getLogger(f"{ticker}.log")
	logger.setLevel(logging.DEBUG)
	fh = logging.FileHandler(f"{ticker}.log")
	fh.setLevel(logging.DEBUG)
	fh.setFormatter(LoggerFormatter())
	logger.addHandler(fh)

	return logger
