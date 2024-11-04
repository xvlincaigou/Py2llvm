class Token:
    def __init__(self, idx, type, value):
        self.idx = idx
        self.type = type
        self.value = value

    def __str__(self):
        return f"Token({self.idx}, {self.type}, {self.value})"