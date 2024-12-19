class Symbol:
    def __init__(self, name, symbol_type, attributes=None):
        self.name = name
        self.type = symbol_type  # 'variable', 'function', 'parameter'
        self.attributes = attributes or {}

    def __repr__(self):
        return f"Symbol(name={self.name}, type={self.type}, attributes={self.attributes})"

class SymbolTable:
    def __init__(self, parent=None):
        self.symbols = {}
        self.parent = parent

    def define(self, name, symbol_type, **attributes):
        if name in self.symbols:
            raise Exception(f"Symbol '{name}' already defined in the current scope.")
        self.symbols[name] = Symbol(name, symbol_type, attributes)

    def lookup(self, name):
        symbol = self.symbols.get(name)
        if symbol:
            return symbol
        elif self.parent:
            return self.parent.lookup(name)
        else:
            return None

    def __repr__(self):
        return f"SymbolTable(symbols={self.symbols}, parent={self.parent})"
