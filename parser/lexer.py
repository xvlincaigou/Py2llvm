from Token import Token

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
                self.tokens.append(Token(self.pos, 'NEWLINE', '\n'))
                self.pos += 1
                self.current_line += 1
                self.current_column = 1
                indent = self.get_indent()
                if indent:
                    self.tokens.append(Token(self.pos, 'INDENT', indent))
            elif self.text[self.pos].isspace():
                self.pos += 1
                self.current_column += 1
            elif self.text[self.pos].isalpha() or self.text[self.pos] == '_':
                self.identifier()
            elif self.text[self.pos].isdigit() or (self.text[self.pos] == '-' and self.pos + 1 < len(self.text) and self.text[self.pos + 1].isdigit()):
                self.tokens.append(self.number())
            elif self.text[self.pos] == '"' or self.text[self.pos] == '\'':
                self.tokens.append(self.string(self.text[self.pos]))
            else:
                self.tokens.append(self.operator())
            if self.tokens and self.tokens[-1].type == 'UNKNOWN':
                RED = '\033[31m'
                RESET = '\033[0m'
                print(f"{RED}Error:{RESET} Unknown token at line {self.current_line}, column {self.current_column}, character '{self.tokens[-1].value}'")
                print(f"{RED}Exiting 1{RESET}")
                exit(1)

        self.tokens.append(Token(self.pos, 'EOF', None))
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
            'and': 'AND', 'or': 'OR', 'not': 'NOT', 'True': 'TRUE', 'False': 'FALSE',
        }
        token_type = keywords.get(value, 'IDENTIFIER')
        
        # Check if it's a function call
        if token_type == 'IDENTIFIER' and self.pos < len(self.text) and self.text[self.pos] == '(':
            # Check if the previous token is 'DEF'
            if self.tokens and self.tokens[-1].type != 'DEF':
                token_type = 'FUNC_CALL'
        elif token_type == 'IDENTIFIER' and self.pos < len(self.text) and self.text[self.pos] == '[':
            if self.tokens and self.tokens[-1].type != 'DEF':
                token_type = 'ARRAY_MEMBER'
        
        self.tokens.append(Token(self.pos, token_type, value))

    def number(self):
        start = self.pos
        if self.text[self.pos] == '-':
            self.pos += 1
            self.current_column += 1
        while self.pos < len(self.text) and (self.text[self.pos].isdigit() or self.text[self.pos] == '.'):
            self.pos += 1
            self.current_column += 1
        return Token(self.pos, 'NUMBER', self.text[start:self.pos])

    def string(self, quote):
        start = self.pos
        self.pos += 1
        self.current_column += 1
        while self.pos < len(self.text) and self.text[self.pos] != quote:
            if self.text[self.pos] == '\\' and self.pos + 1 < len(self.text):
                self.pos += 1
                self.current_column += 1
            self.pos += 1
            self.current_column += 1
        if self.pos < len(self.text):
            self.pos += 1
            self.current_column += 1
        return Token(self.pos, 'STRING_LITERAL', self.text[start:self.pos])

    def operator(self):
        operators = {
            '=': 'ASSIGN',
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
        
        return Token(self.pos, operators.get(op, 'UNKNOWN'), op)

def main():
    import sys
    filename = sys.argv[1]
    with open(filename, 'r') as file:
        source_code = file.read()
        lexer = Lexer(source_code)
        tokens = lexer.tokenize()
        with open(filename + '.tokens', 'w') as token_file:
            for token in tokens:
                token_file.write(f"{token}\n")

if __name__ == "__main__":
    main()