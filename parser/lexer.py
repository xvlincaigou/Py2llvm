import re

class Token:
    def __init__(self, type, value):
        self.type = type
        self.value = value

    def __str__(self):
        return f"Token({self.type}, {self.value})"

class Lexer:
    def __init__(self, text):
        self.text = text
        self.pos = 0
        self.current_line = 1
        self.current_column = 1
        self.tokens = []

    def tokenize(self):
        while self.pos < len(self.text):
            if self.text[self.pos] == '\n':
                self.tokens.append(Token('NEWLINE', '\n'))
                self.pos += 1
                self.current_line += 1
                self.current_column = 1
                indent = self.get_indent()
                if indent:
                    self.tokens.append(Token('INDENT', indent))
            elif self.text[self.pos].isspace():
                self.pos += 1
                self.current_column += 1
            elif self.text[self.pos].isalpha() or self.text[self.pos] == '_':
                self.identifier()
            elif self.text[self.pos].isdigit() or (self.text[self.pos] == '-' and self.pos + 1 < len(self.text) and self.text[self.pos + 1].isdigit()):
                self.tokens.append(self.number())
            elif self.text[self.pos] == '"':
                self.tokens.append(self.string())
            else:
                self.tokens.append(self.operator())

        self.tokens.append(Token('EOF', None))
        return self.tokens

    def get_indent(self):
        start = self.pos
        while self.pos < len(self.text) and self.text[self.pos] == '\t':
            self.pos += 1
            self.current_column += 1
        if self.pos > start:
            return self.text[start:self.pos]
        return None

    def identifier(self):
        start = self.pos
        while self.pos < len(self.text) and (self.text[self.pos].isalnum() or self.text[self.pos] == '_'):
            self.pos += 1
            self.current_column += 1
        value = self.text[start:self.pos]
        keywords = {
            'if': 'IF', 'elif': 'ELIF', 'else': 'ELSE', 'while': 'WHILE', 
            'for': 'FOR', 'in': 'IN', 'def': 'DEF', 'return': 'RETURN', 
            'and': 'AND', 'or': 'OR', 'not': 'NOT'
        }
        token_type = keywords.get(value, 'IDENTIFIER')
        
        # Check if it's a function call
        if token_type == 'IDENTIFIER' and self.pos < len(self.text) and self.text[self.pos] == '(':
            # Check if the previous token is 'DEF'
            if self.tokens and self.tokens[-1].type != 'DEF':
                token_type = 'FUNC_CALL'
        
        self.tokens.append(Token(token_type, value))

    def number(self):
        start = self.pos
        if self.text[self.pos] == '-':
            self.pos += 1
            self.current_column += 1
        while self.pos < len(self.text) and (self.text[self.pos].isdigit() or self.text[self.pos] == '.'):
            self.pos += 1
            self.current_column += 1
        return Token('NUMBER', self.text[start:self.pos])

    def string(self):
        start = self.pos
        self.pos += 1
        self.current_column += 1
        while self.pos < len(self.text) and self.text[self.pos] != '"':
            if self.text[self.pos] == '\\' and self.pos + 1 < len(self.text):
                self.pos += 1
                self.current_column += 1
            self.pos += 1
            self.current_column += 1
        if self.pos < len(self.text):
            self.pos += 1
            self.current_column += 1
        return Token('STRING_LITERAL', self.text[start:self.pos])

    def operator(self):
        operators = {
            '=': 'EQUAL',
            ':': 'COLON',
            ',': 'COMMA',
            '+': 'PLUS',
            '-': 'MINUS',
            '*': 'MULTIPLY',
            '//': 'DIVIDE',
            '(': 'LPAREN',
            ')': 'RPAREN',
            '[': 'LBRACKET',
            ']': 'RBRACKET',
            '<': 'LT',
            '>': 'GT',
            '<=': 'LTE',
            '>=': 'GTE',
            '==': 'EQUALS',
            '!=': 'NOT_EQUALS'
        }
        
        if self.pos + 1 < len(self.text) and self.text[self.pos:self.pos+2] in operators:
            op = self.text[self.pos:self.pos+2]
            self.pos += 2
            self.current_column += 2
        else:
            op = self.text[self.pos]
            self.pos += 1
            self.current_column += 1
        
        return Token(operators.get(op, 'UNKNOWN'), op)

def main():
    with open("test_code.py", 'r') as file:
        source_code = file.read()
        lexer = Lexer(source_code)
        tokens = lexer.tokenize()
        for token in tokens:
            print(token)

if __name__ == "__main__":
    main()