from clint.textui import puts, colored


class Notify:
    @staticmethod
    def heading(heading: str) -> None:
        puts(colored.yellow(heading))

    @staticmethod
    def info(message: str) -> None:
        puts(colored.green("[ MESSAGE ]  ") + message)

    @staticmethod
    def warn(message: str) -> None:
        puts(colored.cyan("[ WARNING ]  ") + message)

    @staticmethod
    def fatal(message: str) -> None:
        puts(colored.red("[  FATAL  ]  ") + message)
