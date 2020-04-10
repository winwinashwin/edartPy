# edartPy


![GitHub Logo](https://i.morioh.com/2019/10/30/49137bce15d7.jpg)


Description
-----------

A fully **automated Trading bot** built in python with an **appealing Command Line Interface**. The bot uses the Ichimoku Indicator and employs **Kumo Breakout strategy** for generating buy and sell calls.


### Workflow

Upon initiation, the bot goes through *four phases*:

- Idle phase
> Stay Idle for the market to settle, then find the relevant stocks to focus on. Each of there stocks is passed to each trader by the master

- Observation phase
> Each trader observes the stock price for 80 (default) periods to set the Ichimoku parameters

- Trading phase
> 
- Shutdown phase
