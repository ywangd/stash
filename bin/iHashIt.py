# iHashIt by SnowleopardXI | Hash your string!
```Hash utilities
```
from __future__ import absolute_import, print_function
import hashlib, inspect, console

hash_methods = {name: method for name, method in inspect.getmembers(hashlib) if name in hashlib.algorithms_guaranteed}


def main():
	method = str(console.input_alert("iHashIt by SnowleopardXI", "Enter a hash method (type list to get a list of available hash methods, extra for more info.)\nExample: md5"))
	if method == 'list':
		list = console.alert("iHashIt by SnowleopardXI", "List of available hash methods:\n\n" + "\n".join(sorted(hashlib.algorithms_guaranteed)))
	if method == 'extra':
		console.alert("iHashIt by SnowleopardXI", "Created on Wednesday, 22 August 2018 by SnowleopardXI on Pythonista 3, for Python 3.\nMade using hashlib library.\nLICENSE: GNU GPL v3.0\n----------\nHow does it work?\n1. User input using console.input_alert(\"iHashIt\", \"Description of user input\") and putting it into a variable\n2. Converting user input (which is a string) to a bytearray (I called it bytestring lol) in order to make hashing with user input (string) possible.\n3. Using hashlib for the rest.\n----------\nHUGE SHOUTOUT to Omz::software for creating Pythonista! I\'m a total noob, but at least I created some cool scripts with it, also using its great documentation!\nAlso a big thank you to cclauss for making the code shorter, more effective and compatible with both python 2 and 3!")
	string = console.input_alert("iHashIt", "Enter a string to hash")
	try:
		m = hash_methods[method]()
	except IndexError:
		print("Unknown hashing method")
		return 1
	m.update(b"" + bytearray(string, "utf-8"))
	fmt = "Your [{}] hashed string is:{}\nDigest size: {}\nBlock size: {}\n\n"
	print(fmt.format(method.upper(), m.hexdigest(), m.digest_size, m.block_size))
	print("iHashIt by SnowleopardXI")


if __name__ == '__main__':
	main()
# huge thanks to cclauss for making the code shorter and compatible with both python 2 and 3
