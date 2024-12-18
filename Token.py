class Token:
    def __init__(self, idx, type, value, line, column):
        self.idx = idx
        self.type = type
        self.value = value
        self.line = line
        self.column = column

    def __str__(self):
        return f"Token({self.idx}, {self.type}, {self.value}, line={self.line}, column={self.column})"
