n=777767777

def isPrime(n):
	if n==2:
		return 1
	if n%2==0:
		return 0
	i=3
	res=1
	while i*i<=n and res:
		if n%i==0:
			res=0
		i=i+2
	return res

i=2
while i<1000:
	if isPrime(i):
		print(i)
	i=i+1
