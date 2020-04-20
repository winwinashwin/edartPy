##############################################################

# Weight for a strong bullish signal
STRONG_BULL = 1
# Weight for a neutral bullish signal
NEUTRAL_BULL = 0
# Weight for a weak bullish signal
WEAK_BULL = 0.01

##############################################################

# Weight for a weak bearish signal
STRONG_BEAR = -1
# Weight for a weak bearish signal
NEUTRAL_BEAR = 0
# Weight for a weak bearish signal
WEAK_BEAR = -0.01

##############################################################

DEFAULT = 0

##############################################################


class Model:
	def __init__(self, price, tenkan, kijun, sen_A, sen_B, price_26, tk_old, pk_old, cp_old, ab_old, fut_senA, fut_senB):
		self.price = price
		self.tenkan = tenkan
		self.kijun = kijun
		self.sen_A = sen_A
		self.sen_B = sen_B
		self.price_26 = price_26

		self.tk_old = tk_old
		self.pk_old = pk_old
		self.cp_old = cp_old
		self.ab_old = ab_old

		self.fa = fut_senA
		self.fb = fut_senB

		if self.tenkan < self.kijun:
			self.tk_new = -1
		elif self.tenkan > self.kijun:
			self.tk_new = 1
		else:
			self.tk_new = 0

		if self.price < self.kijun:
			self.pk_new = -1
		elif self.price > self.kijun:
			self.pk_new = 1
		else:
			self.pk_new = 0

		if self.price < self.price_26:
			self.cp_new = -1
		elif self.price > self.price_26:
			self.cp_new = 1
		else:
			self.cp_new = 0

		if self.fa > self.fb:
			self.ab_new = 1
		elif self.fa < self.fb:
			self.ab_new = -1
		else:
			self.ab_new = 0

		self.k_upper = max(self.sen_A, self.sen_B)
		self.k_lower = min(self.sen_A, self.sen_B)

	def tk_cross(self):
		# if a bullish tk cross occurs
		if self.tk_new == 1 and self.tk_old == -1:
			if self.kijun > self.k_upper:
				return STRONG_BULL
			elif self.tenkan < self.k_lower:
				return WEAK_BULL
			else:
				return NEUTRAL_BULL

		if self.tk_new == -1 and self.tk_old == 1:
			if self.tenkan > self.k_upper:
				return WEAK_BEAR
			elif self.kijun < self.k_lower:
				return STRONG_BEAR
			else:
				return NEUTRAL_BEAR

		return DEFAULT

	def kijun_cross(self):
		if self.pk_new == 1 and self.pk_old == -1:
			if self.kijun > self.k_upper:
				return STRONG_BULL
			elif self.price < self.k_lower:
				return WEAK_BULL
			else:
				return NEUTRAL_BULL

		if self.pk_new == -1 and self.pk_old == 1:
			if self.price > self.k_upper:
				return WEAK_BEAR
			elif self.kijun < self.k_lower:
				return STRONG_BEAR
			else:
				return NEUTRAL_BEAR

		return DEFAULT

	def chikou_break(self):
		if self.cp_new == 1 and self.cp_old == -1:
			if self.price > self.k_upper:
				return STRONG_BULL
			elif self.price < self.k_lower:
				return WEAK_BULL
			else:
				return NEUTRAL_BULL

		if self.cp_new == -1 and self.cp_old == 1:
			if self.price < self.k_lower:
				return STRONG_BEAR
			elif self.price > self.k_upper:
				return WEAK_BEAR
			else:
				return NEUTRAL_BEAR

		return DEFAULT

	def kumo_twist(self):
		if self.ab_old == -1 and self.ab_new == 1:
			if self.price > self.k_upper:
				return STRONG_BULL
			elif self.price < self.k_lower:
				return WEAK_BULL
			else:
				return NEUTRAL_BULL

		if self.ab_old == 1 and self.ab_new == -1:
			if self.price < self.k_lower:
				return STRONG_BEAR
			elif self.price > self.k_upper:
				return WEAK_BEAR
			else:
				return NEUTRAL_BEAR

		return DEFAULT

	def get_conf(self):
		conf = (self.tk_cross() + self.kijun_cross() + self.chikou_break() + self.kumo_twist()) / 4
		return conf
