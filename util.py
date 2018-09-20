import datetime

def timestamp():
	return '[' + datetime.datetime.now().strftime('%X') + ']'
