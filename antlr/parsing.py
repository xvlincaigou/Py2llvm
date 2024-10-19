from antlr4 import *
from antlr_output.Python3SimplifiedLexer import Python3SimplifiedLexer
from antlr_output.Python3SimplifiedParser import Python3SimplifiedParser
import tkinter as tk
from tkinter import ttk
from antlr4.tree.Trees import Trees

class Python3SimplifiedLexerPLUS(Python3SimplifiedLexer):
    def __init__(self, input=None):
        super().__init__(input)
        self.indent_stack = [0]  # 栈来存储缩进级别
        self.pending_dedents = 0

    def getIndent(self):
        current_indent = self.getIndentationCount(self._input.LA(1))
        last_indent = self.indent_stack[-1]

        if current_indent > last_indent:
            self.indent_stack.append(current_indent)
            return self.createToken(Python3SimplifiedLexer.INDENT)
        elif current_indent < last_indent:
            while self.indent_stack and current_indent < self.indent_stack[-1]:
                self.indent_stack.pop()
                self.pending_dedents += 1
            return self.createToken(Python3SimplifiedLexer.DEDENT)

    def getIndentationCount(self, text):
        return len(text)  # 假设每个缩进是一个制表符


code = open('code.py').read()
input_stream = InputStream(code)
lexer = Python3SimplifiedLexerPLUS(input_stream)
token_stream = CommonTokenStream(lexer)

# 填充 tokens
token_stream.fill()

# 打印所有的 tokens
for token in token_stream.getTokens(start=0, stop=1000):
    print(token)

parser = Python3SimplifiedParser(token_stream)
tree = parser.program()
print(tree.toStringTree(recog=parser))


def display_ast(tree, parser):
    root = tk.Tk()
    root.title("Abstract Syntax Tree")
    
    tree_view = ttk.Treeview(root)
    tree_view.pack(expand=True, fill='both')
    
    def add_node(parent, ast_node):
        node_text = Trees.getNodeText(ast_node, ruleNames=parser.ruleNames)
        node_id = tree_view.insert(parent, 'end', text=node_text)
        for i in range(ast_node.getChildCount()):
            add_node(node_id, ast_node.getChild(i))
        # for child in ast_node.getChild():
        #     add_node(node_id, child)
    
    add_node('', tree)
    
    root.mainloop()

# 调用函数显示AST
display_ast(tree, parser)



# from antlr4 import *
# from antlr_output.Python3SimplifiedLexer import Python3SimplifiedLexer
# from antlr_output.Python3SimplifiedParser import Python3SimplifiedParser
# from ANTLRToPythonAST import ANTLRToPythonAST
# import ast

# # ... 其他代码保持不变 ...

# parser = Python3SimplifiedParser(token_stream)
# tree = parser.program()

# # 使用转换器
# converter = ANTLRToPythonAST()
# python_ast = converter.visit(tree)

# # 打印 Python AST
# print(ast.dump(python_ast, indent=2))

# # 如果你还想显示图形化的 AST，可以保留原来的 display_ast 函数调用
# display_ast(tree, parser)