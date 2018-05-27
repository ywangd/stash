from __future__ import print_function
# by Siddharth Duahantha
# 28 July 2017
import sys
import argparse

COW =  """         \   ^__^ 
          \  (oo)\_______
             (__)\       )\/\\
                 ||----w |
                 ||     ||
    """


def get_cow(text): 
	"""create a string of a cow saying things."""
	lines = text.split("\n")
	nlines = len(lines)
	longest_line = max([len(l) for l in lines])
	lenght_of_lines = longest_line + 2
	ret = (' ' + '_' * lenght_of_lines + "\n")
	if nlines == 1:
		formated = text.center(longest_line + 2)
		ret += formated.join('<>') + "\n"
	else:
		t = ""
		for i in range(nlines):
			line = lines[i].center(longest_line + 2)
			if i == 0:
				t += ("/" + line + "\\\n")
			elif i == (nlines - 1):
				t += ("\\" + line + "/\n")
			else:
				t += ("|" + line + "|\n")
		ret += t
	ret += (' ' + '-' * lenght_of_lines + "\n")
	ret += COW
	return ret


def main():
	"""main function"""
	# todo: lookuo real description
	parser = argparse.ArgumentParser(description="Let a cow speak for you")
	parser.add_argument("text", nargs="*", default=None, help="text to say")
	ns = parser.parse_args()
	
	if (ns.text is None) or (len(ns.text) == 0):
		text = ""
		while True:
			inp = sys.stdin.read(4096)
			if inp.endswith("\n"):
				inp = inp[:-1]
			if not inp:
				break
			text += inp
	else:
		text = " ".join(ns.text)
	
	cow = get_cow(text)
	print(cow)
	

if __name__ == "__main__":
	main()