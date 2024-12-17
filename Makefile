OUTPUT = output
LL_FILES = generated.ll comp.ll

all: $(OUTPUT)

$(OUTPUT): generated.ll
	@echo "Building executable..."
	python3 PyLL.py $(FILE)
	clang -O3 -S -emit-llvm comp.c -o comp.ll
	clang generated.ll comp.ll -o $(OUTPUT)

generated.ll: comp.c
	@echo "Generating LLVM IR for comp.c..."
	clang -O3 -S -emit-llvm comp.c -o generated.ll

clean:
	@echo "Cleaning up..."
	rm -f $(OUTPUT) $(LL_FILES)

.PHONY: all clean build

build:
	@echo "Building with custom file: $(FILE)"
	make $(OUTPUT) FILE=$(FILE)

