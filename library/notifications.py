from colorama import Fore, Style
from time import sleep


PAUSE = 0.02


class Notify:
    @staticmethod
    def heading(heading: str) -> None:
        print(Fore.YELLOW + heading)
        print(Style.RESET_ALL)

    @staticmethod
    def for_input(message: str, delay: float = PAUSE) -> None:
        print(Fore.GREEN + "[ MESSAGE ]  " + Style.RESET_ALL, end="")
        for char in message:
            print(char, end="")
            sleep(delay)

    @staticmethod
    def info(message: str, delay: float = PAUSE) -> None:
        print(Fore.GREEN + "[ MESSAGE ]  " + Style.RESET_ALL, end="")
        for char in message:
            print(char, end="")
            sleep(delay)
        print("")

    @staticmethod
    def warn(message: str, delay: float = PAUSE) -> None:
        print(Fore.CYAN + "[ WARNING ]  " + Style.RESET_ALL, end="")
        for char in message:
            print(char, end="")
            sleep(delay)
        print("")

    @staticmethod
    def fatal(message: str, delay: float = PAUSE) -> None:
        print(Fore.RED + "[  FATAL  ]  " + Style.RESET_ALL, end="")
        for char in message:
            print(char, end="")
            sleep(delay)
        print("")
