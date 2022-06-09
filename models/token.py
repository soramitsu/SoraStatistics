class Token:
    def __init__(self, name: str, ticker: str, precision: int):
        self.ticker = ticker
        self.name = name
        self.precision = precision
