# edartPy



![GitHub Logo](https://i.morioh.com/2019/10/30/49137bce15d7.jpg)



Description
-----------

A fully **automated Trading bot** built in python with an **appealing Command Line Interface**. The bot uses the Ichimoku Indicator and employs **Kumo Breakout strategy** for generating buy and sell calls.



### Workflow

Whole activity of the bot can be divided into *four phases*:

- Idle phase
> Stay Idle for the market to settle, then find the relevant stocks to focus on. Each of these stocks is then passed to each trader by the master


- Observation phase
> Each trader observes the stock price for 80 (default) periods to set the Ichimoku parameters


- Trading phase
> Traders make buy and sell calls according to the Ichimoku components and updates the same


- Shutdown phase
> By this point intraday trading has been complete and traders save the activity in json format



### References

* Balkrishna M. Sadekar - How to Make Money Trading the Ichimoku System
