OUTPUT = output
LL_FILES = generated.ll comp.ll

all: $(OUTPUT)

$(OUTPUT): generated.ll
	python3 PyLL.py $(FILE)
	clang -O3 -S -emit-llvm comp.c -o comp.ll
	clang generated.ll comp.ll -o $(OUTPUT)

generated.ll: comp.c
	clang -O3 -S -emit-llvm comp.c -o generated.ll

clean:
	@echo "Cleaning up..."
	rm -f $(OUTPUT) $(LL_FILES)

.PHONY: all clean build

build:
	make $(OUTPUT) FILE=$(FILE)

