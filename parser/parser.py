from Token import Token
from lexer import Lexer
import sys
import ast

class Parser:
    def __init__(self, tokens):
        self.tokens = tokens
        self.current_token_index = 0
        self.current_token = self.tokens[self.current_token_index]
        self.indent_level = 0

    def error(self):
        print(self.current_token)
        raise Exception("Parsing error")

    def consume(self, token_type):
        if self.current_token.type == token_type:
            self.current_token_index += 1
            if self.current_token_index < len(self.tokens):
                self.current_token = self.tokens[self.current_token_index]
        else:
            self.error()

    def tab2indent_level(self, token):
        indent_size = token.value.count('\t') * 4 + token.value.count(' ')
        assert not (indent_size % 4)
        return indent_size // 4

    def parse(self):
        return self.program()

    def program(self):
        statements = []
        while self.current_token.type != 'EOF':
            statements.append(self.statement())
        statements = list(filter(lambda x: x is not None, statements))
        return ast.Module(body=statements, type_ignores=[])

    def statement(self):
        if self.current_token.type == 'IDENTIFIER':
            return self.assignment_statement()
        elif self.current_token.type == 'DEF':
            return self.function_definition()
        elif self.current_token.type == 'IF':
            return self.if_statement()
        elif self.current_token.type == 'FOR':
            return self.for_statement()
        elif self.current_token.type == 'WHILE':
            return self.while_statement()
        elif self.current_token.type == 'RETURN':
            return self.return_statement()
        elif self.current_token.type == 'FUNC_CALL':
            return self.function_call()
        elif self.current_token.type == 'NEWLINE':
            self.consume('NEWLINE')
            return None
        else:
            print('Last seen token: ', self.current_token)
            sys.exit(1)

    def assignment_statement(self):
        var_name = self.current_token.value
        self.consume('IDENTIFIER')
        self.consume('ASSIGN')
        value = self.expression()
        return ast.Assign(
            targets=[ast.Name(id=var_name, ctx=ast.Store())],
            value=value
        )

    def function_definition(self):
        self.consume('DEF')
        func_name = self.current_token.value
        self.consume('IDENTIFIER')
        self.consume('LPAREN')
        param = self.current_token.value
        self.consume('IDENTIFIER')
        self.consume('RPAREN')
        self.consume('COLON')
        self.consume('NEWLINE')
        body = self.statement_block()
        return ast.FunctionDef(
            name=func_name,
            args=ast.arguments(
                args=[ast.arg(arg=param, annotation=None)],
                vararg=None,
                kwonlyargs=[],
                kw_defaults=[],
                kwarg=None,
                defaults=[]
            ),
            body=body,
            decorator_list=[],
            returns=None
        )

    def if_statement(self):
        self.consume('IF')
        condition = self.expression()
        self.consume('COLON')
        self.consume('NEWLINE')
        true_branch = self.statement_block()
        false_branch = []
        
        # 处理 elif 语句
        while self.current_token.type == 'ELIF':
            self.consume('ELIF')
            elif_condition = self.expression()
            self.consume('COLON')
            self.consume('NEWLINE')
            elif_branch = self.statement_block()
            false_branch.append(ast.If(
                test=elif_condition,
                body=elif_branch,
                orelse=[]
            ))

        # 处理 else 语句
        if self.current_token.type == 'ELSE':
            self.consume('ELSE')
            self.consume('COLON')
            self.consume('NEWLINE')
            false_branch.append(self.statement_block())

        return ast.If(
            test=condition,
            body=true_branch,
            orelse=false_branch
        )


    def for_statement(self):
        self.consume('FOR')
        loop_var = self.current_token.value
        self.consume('IDENTIFIER')
        self.consume('IN')
        iterable = self.expression()
        self.consume('COLON')
        self.consume('NEWLINE')
        body = self.statement_block()
        return ast.For(
            target=ast.Name(id=loop_var, ctx=ast.Store()),
            iter=iterable,
            body=body,
            orelse=[]
        )

    def while_statement(self):
        self.consume('WHILE')
        condition = self.expression()
        self.consume('COLON')
        self.consume('NEWLINE')
        body = self.statement_block()
        return ast.While(
            test=condition,
            body=body,
            orelse=[]
        )

    def return_statement(self):
        self.consume('RETURN')
        value = self.expression()
        return ast.Return(value=value)

    def function_call(self):
        func_name = self.current_token.value
        self.consume('FUNC_CALL')
        self.consume('LPAREN')
        args = []
        while self.current_token.type != 'RPAREN':
            args.append(self.expression())
            if self.current_token.type == 'COMMA':
                self.consume('COMMA')
        self.consume('RPAREN')
        return ast.Call(
            func=ast.Name(id=func_name, ctx=ast.Load()),
            args=args,
            keywords=[]
        )
    # 这个时候开头的必然是INDENT，并且我保证我结束之后，尾巴的这里的indent也被处理掉了
    def statement_block(self):
        assert self.current_token.type == 'INDENT'
        self.indent_level = self.tab2indent_level(self.current_token)
        statements = []
        while self.current_token.type == 'INDENT':
            #这里的条件其实还有待商榷，因为有可能是回去了一个INDENT，也有可能是新的INDENT，我们这里其实就是当回去的INDENT的时候就break TODO
            if self.tab2indent_level(self.current_token) != self.indent_level:
                self.indent_level = self.tab2indent_level(self.current_token)
                self.consume('INDENT')
                break
            self.consume('INDENT')
            statements.append(self.statement())
            if self.current_token.type == 'NEWLINE':
                self.consume('NEWLINE')
        return statements

    def expression(self):
        value = self.current_token.value
        self.consume(self.current_token.type)
        # 这里简单假设表达式是一个标识符或常量
        return ast.Constant(value=value) if isinstance(value, (int, str)) else ast.Name(id=value, ctx=ast.Load())

if __name__ == "__main__":
    filename = sys.argv[1]
    with open(filename, 'r') as file:
        source_code = file.read()
        lexer = Lexer(source_code)
        tokens = lexer.tokenize()
        for token in tokens:
            print(token)
        parser = Parser(tokens)
        parsed_program = parser.parse()
        print(ast.dump(parsed_program, indent=4))
