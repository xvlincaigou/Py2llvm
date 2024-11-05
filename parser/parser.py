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
        if self.current_token.type == 'IDENTIFIER' or self.current_token.type == 'ARRAY_MEMBER':
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
            self.error()

    def assignment_statement(self):
        if self.current_token.type == 'ARRAY_MEMBER':
            var_name = self.array_member()
        else:
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
        current_indent_level = self.indent_level
        self.consume('IF')
        condition = self.condition()
        self.consume('COLON')
        self.consume('NEWLINE')
        true_branch = self.statement_block()
        false_branch = []
        
        # 处理 elif 语句。每次要到这里的时候，都是得到一个indent elif
        while self.lookahead(1).type == 'ELIF':
            assert self.indent_level == current_indent_level
            self.consume('INDENT')
            self.consume('ELIF')
            elif_condition = self.condition()
            self.consume('COLON')
            self.consume('NEWLINE')
            elif_branch = self.statement_block()
            false_branch.append(ast.If(
                test=elif_condition,
                body=elif_branch,
                orelse=[]
            ))

        # 处理 else 语句
        if self.lookahead(1).type == 'ELSE':
            assert self.indent_level == current_indent_level
            self.consume('INDENT')
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
        condition = self.condition()
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
    
    def array_member(self):
        array_name = self.current_token.value
        self.consume('ARRAY_MEMBER')
        self.consume('LBRACKET')
        index = self.expression()
        self.consume('RBRACKET')
        return ast.Subscript(
            value=ast.Name(id=array_name, ctx=ast.Load()),
            slice=ast.Index(value=index),
            ctx=ast.Load()
        )
    
    # 这个时候开头的必然是INDENT，并且我保证我结束之后，尾巴的这里的indent也被处理掉了
    def statement_block(self):
        assert self.current_token.type == 'INDENT'
        assert self.tab2indent_level(self.current_token) == self.indent_level + 1
        self.indent_level = self.tab2indent_level(self.current_token)
        statements = []
        while self.current_token.type == 'INDENT':
            if self.tab2indent_level(self.current_token) > self.indent_level:
                self.error()
            elif self.tab2indent_level(self.current_token) < self.indent_level:
                self.indent_level -= 1
                return statements
            self.consume('INDENT')
            statements.append(self.statement())
            if self.current_token.type == 'NEWLINE':
                self.consume('NEWLINE')
        self.indent_level -= 1
        return statements

    def condition(self):
        """
        解析条件表达式 (LOGIC_EXPR)，即可能包含逻辑操作符的比较表达式。
        """
        left = self.comparison()  # 初始的比较表达式
        while self.current_token.type in ['AND', 'OR']:  # 处理逻辑操作符
            op = self.current_token.value  # 记录逻辑操作符
            self.consume(self.current_token.type)  # 消耗逻辑操作符
            right = self.comparison()  # 继续解析后面的比较表达式
            left = ast.BoolOp(op=ast.And() if op == 'and' else ast.Or(), values=[left, right])  # 构建逻辑操作的AST节点
        return left

    def comparison(self):
        """
        解析比较表达式 (COMPARISON)，可能包含条件操作符（如 `==`, `!=`）。
        """
        left = self.expression()  # 首先解析一个常规表达式
        if self.current_token.type in ['LT', 'GT', 'LTE', 'GTE', 'EQUALS', 'NOT_EQUALS']:  # 如果是比较操作符
            op = self.current_token.value  # 获取操作符
            self.consume(self.current_token.type)  # 消耗操作符
            right = self.expression()  # 解析右侧表达式
            # 根据操作符构建比较操作AST节点
            if op == '==':
                return ast.Compare(left=left, ops=[ast.Eq()], comparators=[right])
            elif op == '!=':
                return ast.Compare(left=left, ops=[ast.NotEq()], comparators=[right])
            elif op == '>':
                return ast.Compare(left=left, ops=[ast.Gt()], comparators=[right])
            elif op == '<':
                return ast.Compare(left=left, ops=[ast.Lt()], comparators=[right])
            elif op == '>=':
                return ast.Compare(left=left, ops=[ast.GtE()], comparators=[right])
            elif op == '<=':
                return ast.Compare(left=left, ops=[ast.LtE()], comparators=[right])
        return left  # 如果没有比较操作符，返回当前的表达式

    def expression(self):
        """
        解析一个常规表达式 (EXPRESSION)，可能是加法、减法、乘法、除法等。
        """
        if self.current_token.type == 'STRING_LITERAL':
            node = ast.Constant(value=self.current_token.value)
            self.consume('STRING_LITERAL')
            return node
        
        if self.current_token.type == 'LBRACKET':
            return self.list_expr()
        
        if (self.current_token.type == 'IDENTIFIER' or self.current_token.type == 'NUMBER' or 
            self.current_token.type == 'LPAREN' or self.current_token.type == 'FUNC_CALL' or self.current_token.type == 'ARRAY_MEMBER'):
            left = self.term()  # 解析一个基本的TERM
            while self.current_token.type in ['PLUS', 'MINUS']:  # 处理加法和减法
                op = self.current_token.value
                self.consume(self.current_token.type)  # 消耗加号或减号
                right = self.term()  # 解析下一个TERM
                # 构建加法或减法的AST节点
                if op == '+':
                    left = ast.BinOp(left=left, op=ast.Add(), right=right)
                elif op == '-':
                    left = ast.BinOp(left=left, op=ast.Sub(), right=right)
            return left
    
        self.error()
    
    def list_expr(self):
        """
        解析列表字面量（LIST），即`[expr1, expr2, ...]`。
        """
        self.consume('LBRACKET')
        elements = []
        while self.current_token.type != 'RBRACKET':
            elements.append(self.expression())
            if self.current_token.type == 'COMMA':
                self.consume('COMMA')
        self.consume('RBRACKET')
        return ast.List(elts=elements, ctx=ast.Load())
    
    def term(self):
        """
        解析一个基础的术语（TERM），可能是乘法、除法等。
        """
        left = self.factor()  # 解析基本的因子
        while self.current_token.type in ['MULTIPLY', 'DIVIDE']:  # 处理乘法和除法
            op = self.current_token.value
            self.consume(self.current_token.type)  # 消耗乘号或除号
            right = self.factor()  # 解析下一个因子
            # 构建乘法或除法的AST节点
            if op == '*':
                left = ast.BinOp(left=left, op=ast.Mult(), right=right)
            elif op == '//':
                left = ast.BinOp(left=left, op=ast.FloorDiv(), right=right)
        return left

    def factor(self):
        """
        解析因子（FACTOR），即变量、常量、括号内的表达式或函数调用。
        """
        if self.current_token.type == 'NUMBER':  # 如果是数字
            value = int(self.current_token.value)  # 转换为整数
            self.consume('NUMBER')
            return ast.Constant(value=value)
        elif self.current_token.type == 'IDENTIFIER':  # 如果是标识符
            value = self.current_token.value  # 获取标识符值
            self.consume('IDENTIFIER')
            return ast.Name(id=value, ctx=ast.Load())
        elif self.current_token.type == 'LPAREN':  # 如果是括号，递归解析表达式
            self.consume('LPAREN')
            expr = self.expression()
            self.consume('RPAREN')
            return expr
        elif self.current_token.type == 'FUNC_CALL':
            return self.function_call()
        elif self.current_token.type == 'ARRAY_MEMBER':
            return self.array_member()
        else:
            self.error()
    
    def lookahead(self, n):
        """
        预读下一个令牌。
        """
        if self.current_token_index + n >= len(self.tokens):
            return Token(-1, 'EOF', None)
        return self.tokens[self.current_token_index + n]

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
