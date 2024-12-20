import ast
import sys
from llvm import *

# 定义自定义异常类以包含详细的错误信息
class CompilerError(Exception):
    def __init__(self, message, filename, lineno, col_offset):
        super().__init__(f"{filename}:{lineno}:{col_offset}: {message}")
        self.message = message
        self.filename = filename
        self.lineno = lineno
        self.col_offset = col_offset

# 假设 LLVM 类在 llvm 模块中定义
llvm = LLVM()

class Visitor(ast.NodeVisitor):
    def __init__(self, func_name, filename, arg_names=(), typ=None):
        self.filename = filename  # 存储文件名以在错误中引用
        if func_name in llvm.functions:
            # 函数已经定义，检查是否重定义
            existing_func = llvm.functions[func_name]
            if typ:
                existing_typ = (existing_func.return_type, [arg.type for arg in existing_func.func.args])
                if existing_typ != typ:
                    # 函数签名不同，抛出重定义错误
                    raise CompilerError(f"Function '{func_name}' is already defined with a different signature.", 
                                       filename, 0, 0)  # 如果可以获取 node 信息，请在调用处传递
            self.func = existing_func
        else:
            return_type, arg_types = typ if typ else (Void, [])
            func_type = ir.FunctionType(return_type, arg_types)
            llvm_func = ir.Function(llvm.module, func_type, name=func_name)
            self.func = Function(llvm_func, True)
            llvm.functions[func_name] = self.func
        self.args = {arg_names[i]: v for i, v in enumerate(self.func.func.args)}
        self.list_lengths = {}      # 用于跟踪列表变量的长度
        self.string_lengths = {}    # 用于跟踪字符串变量的长度
        self.var_types = {}         # 用于跟踪变量类型

    # 定义错误处理方法
    def error(self, msg, node):
        raise CompilerError(msg, self.filename, node.lineno, node.col_offset)

    # 将不支持的功能调用转换为详细错误
    def not_supports(self, msg, node):
        self.error(f"Compiler doesn't support {msg}.", node)

    def bool(self, value):
        if value.type == Bool: 
            return value
        return self.func.builder.icmp_signed('ne', value, ir.Constant(Int, 0))

    def visit_Module(self, node):
        for st in node.body: 
            self.visit(st)
        self.func.builder.ret(ir.Constant(Int, 0))

    def visit_FunctionDef(self, node):
        # 检查函数是否已经定义
        if node.name in llvm.functions:
            self.error(f"Function '{node.name}' is already defined.", node)
        
        args = [arg.arg for arg in node.args.args]
        # 假设所有函数返回 Int 并接受 Int 类型参数
        func_typ = (Int, [Int] * len(args))
        visitor = Visitor(node.name, self.filename, args, func_typ)
        for stmt in node.body: 
            visitor.visit(stmt)

    def visit_Constant(self, node):
        if isinstance(node.value, int):
            return ir.Constant(Int, node.value)
        elif isinstance(node.value, bool):
            return ir.Constant(Bool, int(node.value))
        elif isinstance(node.value, str):
            # 创建一个全局字符串常量
            str_val = node.value + '\0'  # 以空字符结尾
            str_bytes = bytearray(str_val.encode("utf8"))
            str_type = ir.ArrayType(Char, len(str_bytes))
            global_name = f"str_{len(llvm.module.global_values)}"
            global_str = ir.GlobalVariable(llvm.module, str_type, name=global_name)
            global_str.global_constant = True
            global_str.initializer = ir.Constant(str_type, str_bytes)
            return global_str  # 返回全局数组
        else:
            self.not_supports(f'Constant type {type(node.value)}', node)

    def visit_Name(self, node):
        if node.id in self.args: 
            return self.args[node.id]
        if node.id in self.func.var:
            return self.func.var[node.id].load()
        self.error(f"Undefined variable '{node.id}'.", node)

    def visit_Assign(self, node):
        if len(node.targets) > 1: 
            self.not_supports('Multiple variable assignment', node)
        target = node.targets[0]
        if isinstance(target, ast.Subscript):
            base = self.visit(target.value)
            index = self.visit(target.slice)
            # 确定 base 的类型
            base_type = base.type.pointee
            if isinstance(base_type, ir.ArrayType):
                # 如果 base 是数组指针，则使用两个索引
                elt_ptr = self.func.builder.gep(base, [ir.Constant(Int, 0), index], inbounds=True, name="elt_ptr")
            elif base.type == PChar:
                # 如果 base 是字符串指针（i8*），则使用一个索引
                elt_ptr = self.func.builder.gep(base, [index], inbounds=True, name="elt_ptr")
            else:
                self.not_supports(f'Unsupported subscript type: {base_type}', node)
            value = self.visit(node.value)
            self.func.builder.store(value, elt_ptr)
        elif isinstance(target, ast.Name):
            var_name = target.id
            if isinstance(node.value, ast.List):
                list_alloc = self.visit(node.value)
                array_type = ir.ArrayType(Int, len(node.value.elts))
                pArray = ir.PointerType(array_type)
                self.func.alloc(var_name, list_alloc, pArray)
                self.list_lengths[var_name] = len(node.value.elts)
                self.var_types[var_name] = pArray
            elif isinstance(node.value, ast.Name) and node.value.id in self.list_lengths:
                rhs = self.visit(node.value)  # 获取 x 的指针
                list_length = self.list_lengths[node.value.id]
                array_type = ir.ArrayType(Int, list_length)
                pArray = ir.PointerType(array_type)
                self.func.alloc(var_name, rhs, pArray)
                self.var_types[var_name] = pArray
            elif isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
                # 处理字符串赋值
                str_global = self.visit(node.value)
                ptr = self.func.builder.gep(str_global, [ir.Constant(Int, 0), ir.Constant(Int, 0)], inbounds=True, name="str_ptr")
                self.func.alloc(var_name, ptr, PChar)
                self.var_types[var_name] = PChar
                # 记录字符串长度
                self.string_lengths[var_name] = len(node.value.value)
            else:
                rhs = self.visit(node.value)
                self.func.alloc(var_name, rhs)
                self.var_types[var_name] = rhs.type
        else:
            self.not_supports(f'Unsupported assignment target type: {type(target).__name__}', node)

    def visit_UnaryOp(self, node):
        oprnd = self.visit(node.operand)
        b = self.func.builder
        if isinstance(node.op, ast.USub):
            return b.neg(oprnd)
        else:
            self.not_supports(f'"{node.op.__class__.__name__}" Operator', node)

    def visit_BinOp(self, node):
        op1 = self.visit(node.left)
        op2 = self.visit(node.right)
        b = self.func.builder
        if isinstance(node.op, ast.Add):
            return b.add(op1, op2)
        elif isinstance(node.op, ast.Sub):
            return b.sub(op1, op2)
        elif isinstance(node.op, ast.Mult):
            return b.mul(op1, op2)
        elif isinstance(node.op, ast.Mod):
            return b.urem(op1, op2)
        elif isinstance(node.op, ast.FloorDiv):
            return b.sdiv(op1, op2)
        else:
            self.not_supports(f'"{node.op.__class__.__name__}" Operator', node)

    def visit_BoolOp(self, node):
        oprnds = [self.bool(self.visit(i)) for i in node.values]
        res = oprnds[0]
        b = self.func.builder

        if isinstance(node.op, ast.And):
            s = b.and_
        elif isinstance(node.op, ast.Or):
            s = b.or_
        else:
            self.not_supports(f'"{node.op.__class__.__name__}" Operator', node)

        for i in range(1, len(oprnds)):
            res = s(res, oprnds[i])
        return res

    def visit_Compare(self, node):
        if len(node.comparators) > 1: 
            self.not_supports('Multiple comparison expression', node)
        op1 = self.visit(node.left)
        op2 = self.visit(node.comparators[0])
        
        # 获取变量类型
        if isinstance(node.left, ast.Subscript):
            base = node.left.value.id
            if base in self.var_types:
                base_type = self.var_types[base].pointee
            else:
                self.not_supports(f'Variable "{base}" type not tracked.', node)
        elif isinstance(node.left, ast.Name):
            base = node.left.id
            if base in self.var_types:
                base_type = self.var_types[base]
                if isinstance(base_type, ir.PointerType):
                    base_type = base_type.pointee
            else:
                self.not_supports(f'Variable "{base}" type not tracked.', node)
        else:
            base_type = op1.type
        
        # 根据类型选择比较谓词
        if base_type == Char:
            # 对于 i8 类型，使用无符号比较
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
            else:
                self.not_supports(f'Unsupported comparison operator: {type(node.ops[0]).__name__}', node)
            # 使用 icmp_unsigned
            return self.func.builder.icmp_unsigned(s, op1, op2)
        elif base_type == Int:
            # 对于 i32 类型，使用有符号比较
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
            else:
                self.not_supports(f'Unsupported comparison operator: {type(node.ops[0]).__name__}', node)
            # 使用 icmp_signed
            return self.func.builder.icmp_signed(s, op1, op2)
        else:
            self.not_supports(f'Unsupported type for comparison: {base_type}', node)

    def visit_Call(self, node):
        if node.keywords: 
            self.not_supports('Keyword arguments', node)
        if not isinstance(node.func, ast.Name):
            self.not_supports('Unsupported function call type', node)
        func_id = node.func.id
        if func_id == 'len':
            if len(node.args) != 1:
                self.not_supports('len() takes exactly one argument', node)
            arg = node.args[0]
            if isinstance(arg, ast.Name):
                var_name = arg.id
                if var_name in self.list_lengths:
                    return ir.Constant(Int, self.list_lengths[var_name])
                elif var_name in self.string_lengths:
                    return ir.Constant(Int, self.string_lengths[var_name])
                else:
                    self.not_supports(f'Length of variable "{var_name}" is not known.', node)
            else:
                self.not_supports('len() argument is not a variable.', node)
        elif func_id == 'print':
            if len(node.args) != 1:
                self.not_supports('print() with multiple arguments.', node)
            arg = node.args[0]
            if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                # 打印字符串
                str_global = self.visit(arg)
                # 获取字符串的指针
                ptr = self.func.builder.gep(str_global, [ir.Constant(Int, 0), ir.Constant(Int, 0)], inbounds=True, name="str_ptr")
                return self.func.builder.call(llvm.getFunction('print_str'), [ptr])
            else:
                # 假设是整数或字符
                value = self.visit(arg)
                if value.type == Int:
                    return self.func.builder.call(llvm.getFunction('print_i32'), [value])
                elif value.type == Char:
                    # 需要实现打印字符的函数
                    # 暂时使用 print_i32 将字符作为整数打印
                    return self.func.builder.call(llvm.getFunction('print_i32'), [ir.ZExt(value, Int)])
                else:
                    self.not_supports(f'Unsupported print argument type: {value.type}', node)
        else:
            # 处理其他函数调用
            args = [self.visit(arg) for arg in node.args]
            try:
                llvm_func = llvm.getFunction(func_id)
            except KeyError:
                self.not_supports(f'Call to undefined function "{func_id}".', node)
            return self.func.builder.call(llvm_func, args)

    def visit_If(self, node):
        b = self.func.builder
        pae = b.position_at_end
        br = b.branch

        test = self.visit(node.test)
        test = self.bool(test)
        
        then_block = self.func.getBlock('then')
        else_block = self.func.getBlock('else')
        end_block = self.func.getBlock('endif')
        
        b.cbranch(test, then_block, else_block)

        # Then block
        pae(then_block)
        for stmt in node.body: 
            self.visit(stmt)
        b.branch(end_block)

        # Else block
        pae(else_block)
        for stmt in node.orelse: 
            self.visit(stmt)
        b.branch(end_block)

        # End block
        pae(end_block)

    def visit_Expr(self, node):
        self.visit(node.value)

    def visit_While(self, node):
        if node.orelse: 
            self.not_supports('While - else statement', node)
        
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

        if isinstance(iter_node, ast.Call) and isinstance(iter_node.func, ast.Name) and iter_node.func.id == 'range':
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
                self.not_supports('range with more than 3 arguments', node)

            # 分配并初始化循环变量
            self.func.alloc(target.id, start)
            self.var_types[target.id] = Int

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
            self.not_supports('for loops over non-range iterables', node)

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
        list_ptr = self.visit(node.value)  # 可能是 [N x i32]* 或 [N x i8]* 或 i8*
        index = self.visit(node.slice)    # i32
        
        if isinstance(list_ptr.type.pointee, ir.ArrayType):
            # pointer to array, use two indices
            elt_ptr = self.func.builder.gep(list_ptr, [ir.Constant(Int, 0), index], inbounds=True, name="elt_ptr")
        elif list_ptr.type == PChar:
            # i8*, use single index
            elt_ptr = self.func.builder.gep(list_ptr, [index], inbounds=True, name="elt_ptr")
        else:
            self.not_supports(f'Unsupported subscript type: {list_ptr.type}', node)
        
        return self.func.builder.load(elt_ptr)

    def visit_Return(self, node):
        self.func.builder.ret(self.visit(node.value))

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python PyLL.py <source_file.py>")
        sys.exit(1)
    
    filename = sys.argv[1]
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            code = f.read()
        
        # 解析 Python 源代码为 AST
        parsed_ast = ast.parse(code, filename=filename)
        
        # 创建 Visitor 实例并遍历 AST
        visitor = Visitor('main', filename)
        visitor.visit(parsed_ast)
        
        # 生成 LLVM IR 文件
        with open('generated.ll', 'w') as f:
            f.write(str(llvm.module))
        
        # 输出 LLVM IR 到控制台（可选）
        for line in str(llvm.module).split("\n"): 
            print(line)
    
    except CompilerError as e:
        print(f"【Error】: {e}")
        sys.exit(1)
    except FileNotFoundError:
        print(f"【Error】: File '{filename}' not found.")
        sys.exit(1)
    except Exception as e:
        print(f"【Unexpected error】: {e}")
        sys.exit(1)
