from antlr4 import *
from antlr_output.Python3SimplifiedLexer import Python3SimplifiedLexer
from antlr_output.Python3SimplifiedParser import Python3SimplifiedParser

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
for token in token_stream.getTokens(start=0, stop=token_stream.__sizeof__()):
    print(token)

parser = Python3SimplifiedParser(token_stream)
tree = parser.program()
print(tree.toStringTree(recog=parser))

# from antlr4.tree.Trees import Trees
# from antlr4_tools import TreeViewer

# # 打开解析树 GUI 窗口
# viewer = TreeViewer(parser.ruleNames, tree)
# viewer.show()