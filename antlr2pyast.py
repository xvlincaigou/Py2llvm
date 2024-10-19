import ast
from antlr4 import ParseTreeVisitor
from antlr_output.Python3SimplifiedParser import Python3SimplifiedParser

class ANTLRToPythonAST(ParseTreeVisitor):
    def __init__(self):
        self.ast_module = ast.Module(body=[], type_ignores=[])

    def visitProgram(self, ctx:Python3SimplifiedParser.ProgramContext):
        for child in ctx.children:
            if isinstance(child, Python3SimplifiedParser.StatementContext):
                stmt = self.visit(child)
                if stmt:
                    self.ast_module.body.append(stmt)
        return self.ast_module

    def visitStatement(self, ctx:Python3SimplifiedParser.StatementContext):
        return self.visitChildren(ctx)

    def visitSimple_stmt(self, ctx:Python3SimplifiedParser.Simple_stmtContext):
        return self.visit(ctx.small_stmt())

    def visitAssignment(self, ctx:Python3SimplifiedParser.AssignmentContext):
        target = ast.Name(id=ctx.NAME().getText(), ctx=ast.Store())
        value = self.visit(ctx.expr())
        return ast.Assign(targets=[target], value=value)

    def visitExpr_stmt(self, ctx:Python3SimplifiedParser.Expr_stmtContext):
        return ast.Expr(value=self.visit(ctx.expr()))

    def visitReturn_stmt(self, ctx:Python3SimplifiedParser.Return_stmtContext):
        return ast.Return(value=self.visit(ctx.expr()))

    def visitIf_stmt(self, ctx:Python3SimplifiedParser.If_stmtContext):
        test = self.visit(ctx.test(0))
        body = [self.visit(ctx.suite(0))]
        orelse = []
        for i in range(1, len(ctx.test())):
            orelse.append(ast.If(
                test=self.visit(ctx.test(i)),
                body=[self.visit(ctx.suite(i))],
                orelse=[]
            ))
        if ctx.ELSE():
            orelse.append(self.visit(ctx.suite()[-1]))
        return ast.If(test=test, body=body, orelse=orelse)

    def visitWhile_stmt(self, ctx:Python3SimplifiedParser.While_stmtContext):
        test = self.visit(ctx.test())
        body = [self.visit(ctx.suite())]
        return ast.While(test=test, body=body, orelse=[])

    def visitFor_stmt(self, ctx:Python3SimplifiedParser.For_stmtContext):
        target = ast.Name(id=ctx.NAME().getText(), ctx=ast.Store())
        iter = self.visit(ctx.expr())
        body = [self.visit(ctx.suite())]
        return ast.For(target=target, iter=iter, body=body, orelse=[])

    def visitFuncdef(self, ctx:Python3SimplifiedParser.FuncdefContext):
        name = ctx.NAME().getText()
        args = ast.arguments(
            posonlyargs=[],
            args=[ast.arg(arg=param.getText()) for param in ctx.parameters().NAME()],
            kwonlyargs=[],
            kw_defaults=[],
            defaults=[]
        )
        body = [self.visit(ctx.suite())]
        return ast.FunctionDef(name=name, args=args, body=body, decorator_list=[])

    def visitExpr(self, ctx:Python3SimplifiedParser.ExprContext):
        if len(ctx.children) == 1:
            return self.visit(ctx.atom())
        left = self.visit(ctx.expr(0))
        right = self.visit(ctx.expr(1))
        op = ctx.children[1].getText()
        op_map = {'+': ast.Add, '-': ast.Sub, '*': ast.Mult, '/': ast.Div, '//': ast.FloorDiv, '%': ast.Mod}
        return ast.BinOp(left=left, op=op_map[op](), right=right)

    def visitAtom(self, ctx:Python3SimplifiedParser.AtomContext):
        if ctx.NAME():
            return ast.Name(id=ctx.NAME().getText(), ctx=ast.Load())
        elif ctx.NUMBER():
            return ast.Constant(value=int(ctx.NUMBER().getText()))
        elif ctx.STRING():
            return ast.Constant(value=ctx.STRING().getText()[1:-1])  # Remove quotes
        elif ctx.getText() in ['True', 'False']:
            return ast.Constant(value=ctx.getText() == 'True')
        elif ctx.expr():
            return self.visit(ctx.expr())
        elif ctx.list():
            return self.visit(ctx.list())
        elif ctx.func_call():
            return self.visit(ctx.func_call())

    def visitList(self, ctx:Python3SimplifiedParser.ListContext):
        elts = [self.visit(expr) for expr in ctx.expr()]
        return ast.List(elts=elts, ctx=ast.Load())

    def visitFunc_call(self, ctx:Python3SimplifiedParser.Func_callContext):
        func = ast.Name(id=ctx.NAME().getText(), ctx=ast.Load())
        args = [self.visit(expr) for expr in ctx.expr()]
        return ast.Call(func=func, args=args, keywords=[])

# 其他方法根据需要添加...