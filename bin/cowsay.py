#by Siddharth Duahantha
#28 July 2017
from sys import argv

cow =  """         \   ^__^ 
          \  (oo)\_______
             (__)\       )\/\\
                 ||----w |
                 ||     ||
    """

#creating cow's speech bubble
def main(): 
	length_of_text = len(text)
	lenght_of_lines = length_of_text + 2
	print(' ' + '_' * lenght_of_lines)
	
	formated = text.center(length_of_text+2)
	print(formated.join('<>'))
	print(' ' + '-' * lenght_of_lines)
	print(cow)

try:
	text = text = ' '.join(argv[1:]) #This is lets me take a big string
	main()

except IndexError:
	print('usage: cowsay <text>')
