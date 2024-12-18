# Py2llvm

TODO:

- [ ] 增加args，使得可以编译给定路径的文件

- [ ] 输出报错和修改建议

- [ ] 函数参数允许有多个 

- [X] 四则运算（逆波兰表达式）

- [ ] 多层缩进的问题

- [X] 支持数组

- [ ] 支持字符串处理

## 构建方法

```bash
# 构建
make build FILE=<file_name>
```

```bash
# 运行
./output
```

```bash
# 清理
make clean
```

## 依赖

- llvm
- llvmlite(python bindings for llvm)