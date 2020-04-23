from colorama import Fore, Style
from time import sleep


PAUSE = 0.03


class Notify:
    @staticmethod
    def heading(heading: str) -> None:
        print(Fore.YELLOW + heading)
        print(Style.RESET_ALL)

    @staticmethod
    def info(message: str) -> None:
        print(Fore.GREEN + "[ MESSAGE ]  " + Style.RESET_ALL, end="")
        for char in message:
            print(char, end="")
            sleep(PAUSE)
        print("")

    @staticmethod
    def warn(message: str) -> None:
        print(Fore.CYAN + "[ WARNING ]  " + Style.RESET_ALL, end="")
        for char in message:
            print(char, end="")
            sleep(PAUSE)
        print("")

    @staticmethod
    def fatal(message: str) -> None:
        print(Fore.RED + "[  FATAL  ]  " + Style.RESET_ALL, end="")
        for char in message:
            print(char, end="")
            sleep(PAUSE)
        print("")
