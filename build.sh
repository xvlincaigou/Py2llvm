#!/bin/bash

rm output

# 关闭命令回显
set +x

# 运行 Python 脚本
python3 PyLL.py

# 使用 Clang 编译 C 文件为 LLVM IR
gcc -O3 -S -emit-llvm comp.c -o comp.ll

# 链接生成可执行文件
gcc generated.ll comp.ll -o output

# 输出一个空行
echo

# 运行生成的可执行文件
./output