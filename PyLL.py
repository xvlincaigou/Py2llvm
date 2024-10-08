import ast
from llvm import *

llvm = LLVM()

def not_supports(msg): raise Exception(f'Compiler doesn\'t supports {msg}.')

class Visitor:
    def __init__(self, func_name, arg_names = (), typ=None):
        if func_name in llvm.functions: self.func = llvm.functions[func_name]
        else:
            self.func = Function.get(llvm.module, func_name, typ, True)
            llvm.functions[func_name] = self.func
        self.args = {arg_names[i]: v for i, v in enumerate(self.func.func.args)}

    def bool(self, value):
        if value.type == Bool: return value
        return self.func.builder.icmp_signed('!=', Int(0), value)

    def visit(self, node):
        nty = node.__class__.__name__
        try: return getattr(self, f'visit_{nty}')(node)
        except AttributeError: return ast.NodeVisitor.visit(self, node)
        raise Exception(f'Visitor of Node Type "{nty}" not found.')

    def visit_Module(self, node):
        for st in node.body: self.visit(st)
        self.func.builder.ret(Int(0))

    def visit_Constant(self, node):
        return Int(node.value)

    def visit_Name(self, node):
        if node.id in self.args: return self.args[node.id]
        return self.func.var[node.id].load()

    def visit_Assign(self, node):
        if len(node.targets) > 1: not_supports('Multiple variable assignment')
        rhs = self.visit(node.value)
        self.func.alloc(node.targets[0].id, rhs)

    def visit_UnaryOp(self, node):
        op, oprnd = node.op, self.visit(node.operand)
        s = None
        b = self.func.builder
        match type(node.op):
            case ast.USub: s = b.neg

        if s is None: not_supports(f'"{node.op.__class__.__name__}" Operator')
        return s(oprnd)

    def visit_BinOp(self, node):
        op1 = self.visit(node.left)
        op2 = self.visit(node.right)
        s = None
        b = self.func.builder
        match type(node.op):
            case ast.Add: s = b.add
            case ast.Sub: s = b.sub
            case ast.Mult: s = b.mul
            case ast.Mod: s = b.urem

        if s is None: not_supports(f'"{node.op.__class__.__name__}" Operator')
        return s(op1, op2)

    def visit_BoolOp(self, node):
        oprnds = [self.bool(self.visit(i))for i in node.values]
        res = oprnds[0]
        b = self.func.builder
        
        match type(node.op):
                case ast.And: s = b.and_
                case ast.Or: s = b.or_
        if s is None: not_supports(f'"{node.op.__class__.__name__}" Operator')

        for i in range(1, len(oprnds)):
            res = s(res, oprnds[i])
        return res

    def visit_Compare(self, node):
        if len(node.comparators) > 1: not_supports('Multiple comparison expression')
        op1 = self.visit(node.left)
        op2 = self.visit(node.comparators[0])
        s = None
        match type(node.ops[0]):
            case ast.Gt: s = '>'
            case ast.GtE: s = '>='
            case ast.Lt: s = '<'
            case ast.LtE: s = '<='
            case ast.Eq: s = '=='
            case ast.NotEq: s = '!='

        if s is None: not_supports(f'"{node.op.__class__.__name__}" Operator')
        return self.func.builder.icmp_signed(s, op1, op2)
    
    def visit_Call(self, node):
        if node.keywords: not_supports('Keyword arguments')
        return self.func.builder.call(llvm.getFunction(node.func.id), [self.visit(node.args[0])])

    def visit_If(self, node):
        b = self.func.builder
        pae = b.position_at_end
        br = b.branch

        test = self.visit(node.test)
        test = self.bool(test)
        
        with b.if_else(test) as (ifn, elsen):
            with ifn:
                for i in node.body: self.visit(i)
            with elsen:
                if node.orelse: self.visit(node.orelse[0])

    def visit_Expr(self, node):
        self.visit(node.value)

    def visit_While(self, node):
        if node.orelse: not_supports('While - else statement')
        
        while_test = self.func.getBlock('while.test')
        while_body = self.func.getBlock('while.body')

        b = self.func.builder
        pae = b.position_at_end
        br = b.branch
        
        br(while_test)
        pae(while_test)

        test = self.visit(node.test)
        test = self.bool(test)
        
        pae(while_body)
        for st in node.body: self.visit(st)
        br(while_test)

        pae(while_test)
        while_end = self.func.getBlock('while.end')
        b.cbranch(test, while_body, while_end)
        
        pae(while_end)

    def visit_Return(self, node):
        self.func.builder.ret(self.visit(node.value))

    def visit_FunctionDef(self, node):
        args = [v.arg for v in node.args.args]
        visitor = Visitor(node.name, args, [Int, [Int]*len(node.args.args)])
        for i in node.body: visitor.visit(i)


code = open('code.pyll').read()
a = Visitor('main')
a.visit(ast.parse(code))

with open('generated.ll', 'w') as f: print(llvm.module, file=f)
for i in str(llvm.module).split("\n"): print(i)
