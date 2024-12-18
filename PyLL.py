import ast
from llvm import *

llvm = LLVM()

def not_supports(msg): 
    raise Exception(f'Compiler doesn\'t support {msg}.')

class Visitor(ast.NodeVisitor):
    def __init__(self, func_name, arg_names=(), typ=None):
        if func_name in llvm.functions:
            self.func = llvm.functions[func_name]
        else:
            self.func = Function.get(llvm.module, func_name, typ, True)
            llvm.functions[func_name] = self.func
        self.args = {arg_names[i]: v for i, v in enumerate(self.func.func.args)}
        self.list_lengths = {}  # 用于跟踪列表变量的长度
    
    def bool(self, value):
        if value.type == Bool: 
            return value
        return self.func.builder.icmp_signed('!=', Int(0), value)
    
    def visit_Module(self, node):
        for st in node.body: 
            self.visit(st)
        self.func.builder.ret(Int(0))
    
    def visit_Constant(self, node):
        if isinstance(node.value, int):
            return ir.Constant(Int, node.value)
        elif isinstance(node.value, bool):
            return ir.Constant(Bool, int(node.value))
        else:
            not_supports(f'Constant type {type(node.value)}')
    
    def visit_Name(self, node):
        if node.id in self.args: 
            return self.args[node.id]
        return self.func.var[node.id].load()
    
    def visit_Assign(self, node):
        if len(node.targets) > 1: 
            not_supports('Multiple variable assignment')
        target = node.targets[0]
        if isinstance(target, ast.Subscript):
            base = self.visit(target.value)
            index = self.visit(target.slice)
            elt_ptr = self.func.builder.gep(base, [ir.Constant(Int, 0), index], inbounds=True, name="elt_ptr")
            value = self.visit(node.value)
            self.func.builder.store(value, elt_ptr)
        elif isinstance(target, ast.Name):
            if isinstance(node.value, ast.List):
                list_alloc = self.visit(node.value)
                array_type = ir.ArrayType(Int, len(node.value.elts))
                pArray = ir.PointerType(array_type)
                self.func.alloc(target.id, list_alloc, pArray)
                self.list_lengths[target.id] = len(node.value.elts)
            elif isinstance(node.value, ast.Name) and node.value.id in self.list_lengths:
                rhs = self.visit(node.value)  # 获取 x 的指针
                list_length = self.list_lengths[node.value.id]
                array_type = ir.ArrayType(Int, list_length)
                pArray = ir.PointerType(array_type)
                self.func.alloc(target.id, rhs, pArray)
            else:
                rhs = self.visit(node.value)
                self.func.alloc(target.id, rhs)
        else:
            not_supports(f'Unsupported assignment target type: {type(target).__name__}')
    
    def visit_UnaryOp(self, node):
        op, oprnd = node.op, self.visit(node.operand)
        s = None
        b = self.func.builder
        if isinstance(node.op, ast.USub):
            s = b.neg
        if s is None: 
            not_supports(f'"{node.op.__class__.__name__}" Operator')
        return s(oprnd)
    
    def visit_BinOp(self, node):
        op1 = self.visit(node.left)
        op2 = self.visit(node.right)
        s = None
        b = self.func.builder
        if isinstance(node.op, ast.Add):
            s = b.add
        elif isinstance(node.op, ast.Sub):
            s = b.sub
        elif isinstance(node.op, ast.Mult):
            s = b.mul
        elif isinstance(node.op, ast.Mod):
            s = b.urem
        elif isinstance(node.op, ast.FloorDiv):
            s = b.sdiv
        if s is None: 
            not_supports(f'"{node.op.__class__.__name__}" Operator')
        return s(op1, op2)
    
    def visit_BoolOp(self, node):
        oprnds = [self.bool(self.visit(i)) for i in node.values]
        res = oprnds[0]
        b = self.func.builder
        
        if isinstance(node.op, ast.And):
            s = b.and_
        elif isinstance(node.op, ast.Or):
            s = b.or_
        else:
            s = None
        if s is None: 
            not_supports(f'"{node.op.__class__.__name__}" Operator')
    
        for i in range(1, len(oprnds)):
            res = s(res, oprnds[i])
        return res
    
    def visit_Compare(self, node):
        if len(node.comparators) > 1: 
            not_supports('Multiple comparison expression')
        op1 = self.visit(node.left)
        op2 = self.visit(node.comparators[0])
        s = None
        if isinstance(node.ops[0], ast.Gt):
            s = '>'
        elif isinstance(node.ops[0], ast.GtE):
            s = '>='
        elif isinstance(node.ops[0], ast.Lt):
            s = '<'
        elif isinstance(node.ops[0], ast.LtE):
            s = '<='
        elif isinstance(node.ops[0], ast.Eq):
            s = '=='
        elif isinstance(node.ops[0], ast.NotEq):
            s = '!='
    
        if s is None: 
            not_supports(f'"{node.ops[0].__class__.__name__}" Operator')
        return self.func.builder.icmp_signed(s, op1, op2)
    
    def visit_Call(self, node):
        if node.keywords: 
            not_supports('Keyword arguments')
        if node.func.id == 'len':
            arg = node.args[0]
            if isinstance(arg, ast.Name):
                var_name = arg.id
                if var_name in self.list_lengths:
                    return ir.Constant(Int, self.list_lengths[var_name])
                else:
                    not_supports(f'Length of variable "{var_name}" is not known.')
            else:
                not_supports('len() argument is not a variable.')
        return self.func.builder.call(llvm.getFunction(node.func.id), [self.visit(node.args[0])])
    
    def visit_If(self, node):
        b = self.func.builder
        pae = b.position_at_end
        br = b.branch
    
        test = self.visit(node.test)
        test = self.bool(test)
        
        with b.if_else(test) as (ifn, elsen):
            with ifn:
                for i in node.body: 
                    self.visit(i)
            with elsen:
                if node.orelse: 
                    for stmt in node.orelse: 
                        self.visit(stmt)
    
    def visit_Expr(self, node):
        self.visit(node.value)
    
    def visit_While(self, node):
        if node.orelse: 
            not_supports('While - else statement')
        
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
        for st in node.body: 
            self.visit(st)
        br(while_test)
    
        pae(while_test)
        while_end = self.func.getBlock('while.end')
        b.cbranch(test, while_body, while_end)
        
        pae(while_end)
    
    def visit_For(self, node):
        b = self.func.builder
        pae = b.position_at_end
        br = b.branch
    
        loop_test = self.func.getBlock('for.test')
        loop_body = self.func.getBlock('for.body')
        loop_end = self.func.getBlock('for.end')
    
        target = node.target
        iter_node = node.iter
    
        if isinstance(iter_node, ast.Call) and iter_node.func.id == 'range':
            # 处理 range 调用
            args = iter_node.args
            if len(args) == 1:
                start = ir.Constant(Int, 0)
                stop = self.visit(args[0])
                step = ir.Constant(Int, 1)
            elif len(args) == 2:
                start = self.visit(args[0])
                stop = self.visit(args[1])
                step = ir.Constant(Int, 1)
            elif len(args) == 3:
                start = self.visit(args[0])
                stop = self.visit(args[1])
                step = self.visit(args[2])
            else:
                not_supports('range with more than 3 arguments')
    
            # 分配并初始化循环变量
            self.func.alloc(target.id, start)
    
            # 分支到 loop_test
            b.branch(loop_test)
    
            # 设置 loop_test
            pae(loop_test)
            current = self.func.var[target.id].load()
            cmp = self.func.builder.icmp_signed('<', current, stop)
            self.func.builder.cbranch(cmp, loop_body, loop_end)
    
            # 设置 loop_body
            pae(loop_body)
            for stmt in node.body:
                self.visit(stmt)
    
            # 增加循环变量
            current = self.func.var[target.id].load()
            increment = self.func.builder.add(current, step)
            self.func.builder.store(increment, self.func.var[target.id].addr)
    
            # 分支回 loop_test
            self.func.builder.branch(loop_test)
    
            # 设置 loop_end
            pae(loop_end)
            if node.orelse:
                for stmt in node.orelse:
                    self.visit(stmt)
        else:
            # 处理非 range 的 for 循环（未实现）
            not_supports('for loops over non-range iterables')
    
    def visit_List(self, node):
        elements = [self.visit(elt) for elt in node.elts]
        size = len(elements)
        array_type = ir.ArrayType(Int, size)
        array_alloc = self.func.builder.alloca(array_type, name="list_alloc")
        for i, elt in enumerate(elements):
            elt_ptr = self.func.builder.gep(array_alloc, [ir.Constant(Int, 0), ir.Constant(Int, i)], inbounds=True, name=f"list_{i}")
            self.func.builder.store(elt, elt_ptr)
        return array_alloc  # 返回指向整个数组的指针 [N x i32]*
    
    def visit_Subscript(self, node):
        list_ptr = self.visit(node.value)  # 应该是 [N x i32]*
        index = self.visit(node.slice)    # i32
        elt_ptr = self.func.builder.gep(list_ptr, [ir.Constant(Int, 0), index], inbounds=True, name="elt_ptr")
        return self.func.builder.load(elt_ptr)
    
    def visit_Return(self, node):
        self.func.builder.ret(self.visit(node.value))
    
    def visit_FunctionDef(self, node):
        args = [v.arg for v in node.args.args]
        visitor = Visitor(node.name, args, [Int, [Int]*len(node.args.args)])
        for i in node.body: 
            visitor.visit(i)

if __name__ == '__main__':
    import sys
    filename = sys.argv[1]
    code = open(filename).read()
    a = Visitor('main')
    from lexer import Lexer
    from parser import Parser
    lexer = Lexer(code)
    tokens = lexer.tokenize()
    parser = Parser(tokens)
    a.visit(parser.parse())

    with open('generated.ll', 'w') as f: 
        print(llvm.module, file=f)
    for i in str(llvm.module).split("\n"): 
        print(i)
