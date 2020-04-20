##############################################################

# Weight for a strong bullish signal
STRONG_BULL = 1
# Weight for a neutral bullish signal
NEUTRAL_BULL = 0
# Weight for a weak bullish signal
WEAK_BULL = 0.01

##############################################################

STRONG_BEAR = -1
NEUTRAL_BEAR = 0
WEAK_BEAR = -0.01

##############################################################


class Model:
	def __init__(self, price, tenkan, kijun, sen_A, sen_B, price_26, tkp):
		self.price = price
		self.tenkan = tenkan
		self.kijun = kijun
		self.sen_A = sen_A
		self.sen_B = sen_B
		self.price_26 = price_26
		self.tkp = tkp

	def new_tkp(self):
		if self.tenkan < self.kijun:
			return -1
		elif self.tenkan > self.kijun:
			return 1
		else:
			return 0

