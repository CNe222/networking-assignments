import sys
from tkinter import Tk
from Client import Client
from ClientExtend import ClientExtend

if __name__ == "__main__":
	try:
		serverAddr = sys.argv[1]
		serverPort = sys.argv[2]
		rtpPort = sys.argv[3]
		fileName = sys.argv[4]	
	except:
		print("[Usage: ClientLauncher.py Server_name Server_port RTP_port Video_file]\n")	

	print("Choose the type of Media Player:\n- Normal Media Player: Enter 'n'\n- Extend Media Player: Enter 'e'")

	while True:
		typ = str(input())
		if typ == 'n':
			root = Tk()
			app = Client(root, serverAddr, serverPort, rtpPort, fileName)
			app.master.title("Normal Media Player")
			break
		elif typ == 'e':
			root = Tk()
			app = ClientExtend(root, serverAddr, serverPort, rtpPort, fileName)
			app.master.title("Extend Media Player")
			break	
		else:
			print("You must enter 'n' or 'e'!")
	
	
	# Create a new client
	root.mainloop()
	