def factorial(n):
	if n <= 1:
		return 1
	else:
		return n * factorial(n - 1)

numbers = [1, 2, 3, 4, 5]
for num in numbers:
	print(factorial(num))
	x = (2 * num) + 5 // 3
print("Done!")