import matplotlib.pyplot as plt
from matplotlib import style
import numpy as np
import os
import json


class Ichimoku:
    def __init__(self):
        style.use("seaborn")
        self.ticker = ""
        self.data = list()
        self.len_data = 0
        self.tenkan_data = []
        self.kijun_data = []
        self.chikou_data = self.data
        self.senkou_B_data = []
        self.senkou_A_data = list()

    def from_file(self, filename):
        path = ".\\database\\" + filename
        with open(path, "r") as fp:
            src = json.loads(fp.read())
        self.ticker = src['ticker']
        src = src['data']
        self.data = [src[key] for key in src]
        self.len_data = len(self.data)

    def prepare_data(self):
        # tenkan
        for i in range(self.len_data - 9):
            tenkan_src = self.data[i:i + 9]
            self.tenkan_data.append((max(tenkan_src) + min(tenkan_src)) / 2)

        # kijun
        for i in range(self.len_data - 26):
            kijun_src = self.data[i:i + 26]
            self.kijun_data.append((max(kijun_src) + min(kijun_src)) / 2)

        self.chikou_data = self.data
        self.senkou_A_data = [((self.tenkan_data[i+17] + self.kijun_data[i])/2) for i in range(self.len_data - 26)]

        # senkou B
        for i in range(self.len_data - 52):
            senkou_B_src = self.data[i:i + 52]
            self.senkou_B_data.append((max(senkou_B_src) + min(senkou_B_src))/2)

    def plot_data(self):
        # real time data
        x1 = np.array([i for i in range(1, self.len_data + 1)])
        y1 = np.array(self.data)
        plt.plot(x1, y1, label="LIVE", color='#000000', linewidth=0.7)

        # tenkan plot
        x2 = [i for i in range(10, self.len_data + 1)]
        y2 = self.tenkan_data
        plt.plot(x2, y2, label='TENKAN', linestyle='dashed', color='#E00F0F', linewidth=0.5)

        # kijun plot
        x3 = [i for i in range(27, self.len_data + 1)]
        y3 = self.kijun_data
        plt.plot(x3, y3, label="KIJUN", linestyle='dashed', color='#151ACE', linewidth=0.5)

        # chikou plot
        x4 = [i for i in range(-25, self.len_data-25)]
        y4 = self.chikou_data
        plt.plot(x4, y4, label="CHIKOU", linestyle='dashed', color='orange', linewidth=0.3)

        # Senkou A plot
        x5 = [i for i in range(53, self.len_data + 27)]
        y5 = self.senkou_A_data
        plt.plot(x5, y5, label='Senkou A', color='#39AF20', linewidth=0.5)

        # Senkou B plot
        x6 = [i for i in range(79, self.len_data + 27)]
        y6 = self.senkou_B_data
        plt.plot(x6, y6, label='Senkou B', color='#AF208E', linewidth=0.5)

        # Fill Kumo Cloud
        fill_area = np.array(x6)
        z5 = np.array(self.senkou_A_data[26:])
        z6 = np.array(self.senkou_B_data)
        plt.fill_between(fill_area, z5, z6, where=z5 >= z6, color='green', alpha=0.6)
        plt.fill_between(fill_area, z5, z6, where=z5 <= z6, color='red', alpha=0.6)

        plt.xlim(-26, self.len_data + 30)
        plt.xlabel('x - axis')
        plt.ylabel('y - axis')
        plt.title('ICHIMOKU - ' + self.ticker)
        plt.legend()
        filePath = ".\\plots\\" + self.ticker + ".png"
        plt.savefig(filePath, bbox_inches='tight')
        # plt.show()


def plot(file_):
    ichPlot = Ichimoku()
    ichPlot.from_file(file_)
    ichPlot.prepare_data()
    ichPlot.plot_data()
    plt.clf()


if __name__ == "__main__":
    for _, _, files in os.walk("database"):
        for file in files:
            plot(file)
