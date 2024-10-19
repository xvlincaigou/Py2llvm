from llvmlite import ir
from llvmlite.ir import Type

Int = ir.IntType(32)
PInt = ir.PointerType(Int)
Bool = ir.IntType(1)
Void = ir.VoidType()

class Function:
    def __init__(self, func, init):
        self.func = func
        self.builder = ir.IRBuilder(self.getBlock('entry')) if init else None
        self.var = {}

    def getBlock(self, label_name):
        return self.func.append_basic_block(label_name)

    @staticmethod
    def get(module, name, typ, init=False):
        return Function(ir.Function(module, ir.FunctionType(*typ), name), init)

    def alloc(self, name, value):
        if name not in self.var:
            mem = self.builder.alloca(Int)
            self.builder.store(value, mem)
            self.var[name] = Variable(self, mem)
        else:
            self.builder.store(value, self.var[name].addr)


class Variable:
    def __init__(self, func, addr):
        self.func = func
        self.addr = addr

    def load(self):
        return self.func.builder.load(self.addr)


class LLVM:
    def __init__(self):
        self.module = ir.Module()
        self.main = Function.get(self.module, 'main', (Int, []), True)
        self.functions = {
            'main': self.main,
            'print': Function.get(self.module, 'print', (Int, [Int])),
        }

    def getBlock(self, label_name, func_name=None):
        if func_name is None: 
            func = self.main
        else: 
            func = self.functions[func_name]
        return func.getBlock(label_name)

    def getFunction(self, name):
        return self.functions[name].func

    def getBuilder(self, name):
        return self.functions[name].builder

    
