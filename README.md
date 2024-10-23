# Py2llvm

TODO:

- [ ] 支持字符串处理

- [ ] 支持数组

- [ ] 四则运算（逆波兰表达式）

- [ ] 递归？不知道行不行

- [ ] 增加args，使得可以编译给定路径的文件

- [ ] 输出报错和修改建议

构建：

```shell
cd parse
antlr4 Python3Simplified.g4 -Dlanguage=Python3 -o antlr_output
```