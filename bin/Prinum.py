
def sushu(number):
	for i in range (2,int(number**0.5)+1):
		if number%i==0:
			return False
	else:
		return True
n=int(input("Enter your number"))
while True:
     if sushu(n):
         print(str(n)+"is shu shu")    
     else:
         for j in range(2,n):
             if sushu(j):
                 if n%j==0:
                     print(j)
                     if sushu(n%j):
                         exit()
                     else:
                         n=n%j
