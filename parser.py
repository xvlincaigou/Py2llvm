from Token import Token
from lexer import Lexer
import sys
import ast
import json
from symbol_table import SymbolTable

class Parser:
    def __init__(self, tokens):
        self.tokens = tokens
        self.current_token_index = 0
        self.current_token = self.tokens[self.current_token_index]
        self.indent_level = 0
        self.symbol_table = SymbolTable()  # 全局符号表
        self.symbol_table.define('print', 'function')
        self.symbol_table.define('range', 'function')
        self.symbol_table.define('len', 'function')
        
    def error(self, message="Parsing error"):
        RED = '\033[31m'
        RESET = '\033[0m'
        print(f"{RED}Error at token {self.current_token}: {message} {RESET}")
        sys.exit(1)

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
        elif self.current_token.type == 'NEWLINE' or self.current_token.type == 'INDENT':
            self.consume(self.current_token.type)
            return None
        else:
            self.error()

    def assignment_statement(self):
        if self.current_token.type == 'ARRAY_MEMBER':
            var_name = self.array_member(ctx=ast.Store())
            targets = [ast.Subscript(value=var_name.value, slice=var_name.slice, ctx=ast.Store())]
        else:
            var_name = self.current_token.value
            symbol = self.symbol_table.lookup(var_name)
            if symbol:
                if symbol.type != 'variable' and symbol.type != 'parameter':
                    self.error(f"'{var_name}' is not a variable. Please use array_member to assign to array elements.")
            else:
                # 变量未定义，添加到符号表
                self.symbol_table.define(var_name, 'variable')
            targets = [ast.Name(id=var_name, ctx=ast.Store())]
            self.consume('IDENTIFIER')
        
        self.consume('ASSIGN')
        value = self.expression()
        return ast.Assign(
            targets=targets,
            value=value
        )

    def function_definition(self):
        self.consume('DEF')
        func_name = self.current_token.value
        self.consume('IDENTIFIER')
        self.consume('LPAREN')
        
        # 将函数名添加到当前符号表
        if self.symbol_table.lookup(func_name):
            self.error(f"Function '{func_name}' already defined. Please choose another name.")
        self.symbol_table.define(func_name, 'function')

        # Collect parameters
        params = []
        if self.current_token.type == 'IDENTIFIER':
            param_name = self.current_token.value
            params.append(param_name)
            self.consume('IDENTIFIER')
            while self.current_token.type == 'COMMA':
                self.consume('COMMA')
                if self.current_token.type != 'IDENTIFIER':
                    self.error("Expected parameter name after comma.")
                param_name = self.current_token.value
                params.append(param_name)
                self.consume('IDENTIFIER')

        self.consume('RPAREN')
        self.consume('COLON')
        self.consume('NEWLINE')

        # 创建新的符号表作用域
        previous_symbol_table = self.symbol_table
        self.symbol_table = SymbolTable(parent=previous_symbol_table)

        # 将参数添加到新的作用域
        for param in params:
            if self.symbol_table.lookup(param):
                self.error(f"Parameter '{param}' already defined. Please choose another name.")
            self.symbol_table.define(param, 'parameter')

        body = self.statement_block()

        # 恢复之前的符号表
        self.symbol_table = previous_symbol_table
        
        return ast.FunctionDef(
            name=func_name,
            args=ast.arguments(
                posonlyargs=[],
                args=[ast.arg(arg=param, annotation=None) for param in params],
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
        false_branches = []
        
        # 处理 elif 语句。每次要到这里的时候，都是得到一个indent elif
        while self.lookahead(1 if self.indent_level else 0).type == 'ELIF':
            if self.indent_level != current_indent_level:
                self.error("Wrong indent level.")
            if self.indent_level:
                self.consume('INDENT')
            self.consume('ELIF')
            elif_condition = self.condition()
            self.consume('COLON')
            self.consume('NEWLINE')
            elif_branch = self.statement_block()
            false_branches.append(ast.If(
                test=elif_condition,
                body=elif_branch,
                orelse=[]
            ))

        orelse = []
        # 处理 else 语句
        if self.lookahead(1 if self.indent_level else 0).type == 'ELSE':
            if self.indent_level != current_indent_level:
                self.error("Wrong indent level.")
            if self.indent_level:
                self.consume('INDENT')
            self.consume('ELSE')
            self.consume('COLON')
            self.consume('NEWLINE')
            false_branches.append(self.statement_block())
            orelse = false_branches.pop()

        while false_branches:
            false_branch = false_branches.pop()
            orelse = [ast.If(
                test=false_branch.test,
                body=false_branch.body,
                orelse=orelse
            )]

        return ast.If(
            test=condition,
            body=true_branch,
            orelse=orelse
        )


    def for_statement(self):
        self.consume('FOR')
        loop_var = self.current_token.value
        if self.symbol_table.lookup(loop_var):
            self.error(f"Loop variable '{loop_var}' already defined. Please choose another name.")
        self.symbol_table.define(loop_var, 'variable')
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
        if not self.symbol_table.lookup(func_name):
            self.error(f"Undefined function '{func_name}', please define it first.")
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
    
    def array_member(self, ctx=ast.Load()):
        array_name = self.current_token.value
        symbol = self.symbol_table.lookup(array_name)
        if not symbol:
            self.error(f"Undefined array '{array_name}', please define it first.")
        elif symbol.type != 'variable' and symbol.type != 'parameter':
            self.error(f"'{array_name}' is not an array.")
        self.consume('ARRAY_MEMBER')
        self.consume('LBRACKET')
        index = self.expression()
        self.consume('RBRACKET')
        return ast.Subscript(
            value=ast.Name(id=array_name, ctx=ast.Load()),
            slice=ast.Index(value=index),
            ctx=ctx
        )
    
    # 这个时候开头的必然是INDENT
    def statement_block(self):
        if self.current_token.type != 'INDENT':
            self.error("Expected an indent token.")
        if self.tab2indent_level(self.current_token) != self.indent_level + 1:
            self.error("Wrong indent level.")
        self.indent_level = self.tab2indent_level(self.current_token)
        statements = []
        while self.current_token.type == 'INDENT':
            if self.tab2indent_level(self.current_token) > self.indent_level:
                self.error()
            elif self.tab2indent_level(self.current_token) < self.indent_level:
                self.indent_level -= 1
                return statements
            self.consume('INDENT')
            ## 可能需要新增作用域
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
            node = ast.Constant(value=self.current_token.value.strip(self.current_token.value[0]))
            self.consume('STRING_LITERAL')
            return node
        
        if self.current_token.type == 'LBRACKET':
            return self.list_expr()
        
        if self.current_token.type == 'TRUE' or self.current_token.type == 'FALSE':
            node = ast.Constant(value=True if self.current_token.type == 'TRUE' else False)
            self.consume(self.current_token.type)
            return node
        
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
            symbol = self.symbol_table.lookup(value)
            if not symbol:
                self.error(f"Undefined variable '{value}', please define it first.")
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

def ast_to_dict(node):
    if isinstance(node, list):  # 处理节点列表
        return [ast_to_dict(elem) for elem in node]
    
    if isinstance(node, ast.AST):  # 处理AST节点
        node_dict = {}
        # 将 AST 节点的字段信息放入字典中
        for field in node._fields:
            value = getattr(node, field) if hasattr(node, field) else None
            # 如果字段是AST节点或列表，递归处理
            if isinstance(value, ast.AST):
                node_dict[field] = ast_to_dict(value)
            elif isinstance(value, list):
                node_dict[field] = ast_to_dict(value)
            elif value:
                node_dict[field] = value
        # 添加类型信息
        node_dict["type"] = node.__class__.__name__
        return node_dict
    return node  # 返回常规值（如数字、字符串等）

if __name__ == "__main__":
    filename = sys.argv[1]
    with open(filename, 'r') as file:
        source_code = file.read()
        lexer = Lexer(source_code)
        tokens = lexer.tokenize()
        print(tokens)

        # sys.stdout = open('output1.txt', 'w')

        # parser = Parser(tokens)
        # parsed_program = parser.parse()
        # print(ast.dump(parsed_program, indent=4))

        # sys.stdout.close()
        # sys.stdout = open('output2.txt', 'w')

        # # Generate official AST
        # official_ast = ast.parse(source_code)
        # print(ast.dump(official_ast, indent=4))

        # sys.stdout.close()

        parser = Parser(tokens)
        parsed_program = parser.parse()
        ast_dict = ast_to_dict(parsed_program)

        import os
        with open(f'ast-{os.path.basename(filename)}.json', 'w') as json_file:
            json.dump(ast_dict, json_file, indent=4)
