from tkinter import *
import tkinter.messagebox
from PIL import Image, ImageTk
import socket, threading, sys, traceback, os
import time
import datetime
from RtpPacket import RtpPacket

CACHE_FILE_NAME = "cache-"
CACHE_FILE_EXT = ".jpg"

class ClientExtend:
	INIT = 0
	READY = 1
	PLAYING = 2
	state = INIT
	
	SETUP = 0
	PLAY = 1
	PAUSE = 2
	TEARDOWN = 3
	DESCRIBE = 4
	FORWARD = 5
	BACKWARD = 6
	
	firstPlay = True
	isPlaying = False
	counter = 0


	# Initiation..
	def __init__(self, master, serveraddr, serverport, rtpport, filename):
		self.master = master
		self.master.protocol("WM_DELETE_WINDOW", self.closeWindow)
		self.createWidgets()
		self.disableButtons()
		self.serverAddr = serveraddr
		self.serverPort = int(serverport)
		self.rtpPort = int(rtpport)
		self.fileName = filename
		self.hasRtpSocket = False
		self.rtspSeq = 0
		self.sessionId = 0
		self.requestSent = -1
		self.teardownAcked = 0
		self.connectToServer()
		self.frameNbr = 0
		self.isForward = 0
		self.isBackWard = 0
		self.currentTime = 0
		self.currentTimeFloat = 0
		self.totalTime = 0
		self.FPS = 0
		
		self.totalPackets = 0
		self.bytes = 0
		self.packets = 0
		self.packetsLost = 0
		self.lastSequence = 0
		
	# THIS GUI IS JUST FOR REFERENCE ONLY, STUDENTS HAVE TO CREATE THEIR OWN GUI 	
	def createWidgets(self):
		"""Build GUI."""
		
		# Create Play button		
		self.startPause = Button(self.master, width=20, padx=3, pady=3)
		self.startPause["text"] = "▶️"
		self.startPause["command"] = self.playMovie
		self.startPause.grid(row=1, column=0, padx=2, pady=2)
		
		# Create Rewind button			
		self.backward = Button(self.master, width=20, padx=3, pady=3)
		self.backward["text"] = "⏪"
		self.backward["command"] = self.backwardVideo
		self.backward.grid(row=1, column=1, padx=2, pady=2)
		
		# Create Teardown button
		self.teardown = Button(self.master, width=20, padx=3, pady=3)
		self.teardown["text"] = "⏹"
		self.teardown["command"] =  self.teardownMovie
		self.teardown.grid(row=1, column=2, padx=2, pady=2)

		# Create Describe Button
		self.describe = Button(self.master, width=15, padx=3, pady=3)
		self.describe["text"] = "Describe ★"
		self.describe["command"] = self.describeMovie
		self.describe.grid(row=2, column=3, padx=2, pady=2)

		# Create Fast Foward button			
		self.forward = Button(self.master, width=20, padx=3, pady=3)
		self.forward["text"] = "⏩"
		self.forward["command"] = self.forwardVideo
		self.forward.grid(row=1, column=3, padx=2, pady=2)
		
		# Create a label to display the movie
		self.label = Label(self.master, height=19, bg= "#000000")
		self.label.grid(row=0, column=0, columnspan=4, sticky=W+E+N+S, padx=5, pady=5) 
		
		#create a label to display totaltime of the movie
		self.totalTimeLabel = Label(self.master, text="Total Time: 00:00", font=("Arial", 12))
		self.totalTimeLabel.grid(row=2, column=1, padx=2, pady=2)

		#create a label to display remaining time of the movie
		self.remainingTimeLabel = Label(self.master, text="Remaining Time: 00:00", font=("Arial", 12))
		self.remainingTimeLabel.grid(row=2, column=2, padx=2, pady=2)

	# Disable buttons at each state
	def disableButtons(self):
		if self.state == self.INIT:
			self.startPause["text"] = "▶️"
			self.startPause["command"] = self.playMovie
			self.teardown["state"] = "disabled"
			self.describe["state"] = "disabled"
			self.forward["state"] = "disable"
			self.backward["state"] = "disable"
		elif self.state == self.READY:
			self.startPause["text"] = "▶️"
			self.startPause["command"] = self.playMovie
			self.teardown["state"] = "normal"
			self.describe["state"] = "normal"
			self.forward["state"] = "normal"
			self.backward["state"] = "normal"
		elif self.state == self.PLAYING:
			self.startPause["text"] = "⏸"
			self.startPause["command"] = self.pauseMovie
			self.teardown["state"] = "normal"
			self.describe["state"] = "normal"
			self.forward["state"] = "normal"
			self.backward["state"] = "normal"
	
	
	def exitClient(self):
		"""Close GUI button handler."""
		if self.hasRtpSocket:
			self.rtpSocket.shutdown(socket.SHUT_RDWR)
			self.rtpSocket.close()
		# Remove cache image stored in folder (ex: cache-123456.jpg)
		if os.path.isfile(CACHE_FILE_NAME + str(self.sessionId) + CACHE_FILE_EXT):
			os.remove(CACHE_FILE_NAME + str(self.sessionId) + CACHE_FILE_EXT)
		# close the GUI
		self.master.destroy()
		sys.exit(0)

	def setupMovie(self):
		"""Setup button handler."""
		if self.state == self.INIT:
			self.sendRtspRequest(self.SETUP)

	def pauseMovie(self):
		"""Pause button handler."""
		if self.state == self.PLAYING:
			self.sendRtspRequest(self.PAUSE)
	
	def playMovie(self):
		"""Play button handler."""
		if self.state == self.INIT:
			self.firstPlay = False
			self.isPlaying = True
			self.totalTime = 0
			self.totalPackets = 0
			self.bytes = 0
			self.packets = 0
			self.packetsLost = 0
			self.lastSequence = 0
			self.prevPacketArrivalTime = 0
			# self.sendRtspRequest(self.SETUP)
			self.setupMovie()
			# Wait for state to update to READY, so it can play after that
			while self.state != self.READY:
				continue

		if self.state == self.READY:
			# Create new thread that listens for RTPpackets
			# self.isPlaying = True
			threading.Thread(target=self.listenRtp).start()
			# Implement new event and assign to self.playEvent
			# The threading.Event provides an easy way to share a boolean variable _flag between threads that can act as a trigger for an action.
			# Initially, _flag is false
			self.playEvent = threading.Event()
			self.sendRtspRequest(self.PLAY)

	def reset(self):
		self.state = self.INIT
		self.disableButtons()
		self.rtspSeq = 0
		self.sessionId = 0
		self.requestSent = -1
		self.teardownAcked = 0
		self.connectToServer()
		self.frameNbr = 0
		self.isBackWard = 0
		self.isForward = 0
		self.currentTime = 0
		self.currentTimeFloat = 0
		# self.rtpSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

	def teardownMovie(self):
		"""Teardown button handler."""

		if self.state != self.INIT:
			# Remove cache image stored in folder (ex: cache-123456.jpg)
			if os.path.isfile(CACHE_FILE_NAME + str(self.sessionId) + CACHE_FILE_EXT):
				os.remove(CACHE_FILE_NAME + str(self.sessionId) + CACHE_FILE_EXT)
			self.displayStats()
			self.sendRtspRequest(self.TEARDOWN)
			time.sleep(0.5)
			self.reset()
			self.label.image = ''

	def describeMovie(self):
		"""Describe button handler"""
		self.sendRtspRequest(self.DESCRIBE)
	
	def forwardVideo(self):
		self.sendRtspRequest(self.FORWARD)
		self.isForward = 1
	
	def backwardVideo(self):
		self.sendRtspRequest(self.BACKWARD)
		if self.frameNbr <= 50:
			self.frameNbr = 0
		else:
			self.frameNbr -= 50
		self.isBackWard = 1
		
	def listenRtp(self):		
		"""Listen for RTP packets."""
		while True:
			try:
				data = self.rtpSocket.recv(20480)
				if data:
					rtpPacket = RtpPacket()
					rtpPacket.decode(data)
					
					packetArrivalTime = time.perf_counter()
					currFrameNbr = rtpPacket.seqNum()
					self.currentTime = int(currFrameNbr  // self.FPS)
					self.currentTimeFloat = currFrameNbr / self.FPS
					print("Current Seq Num: " + str(currFrameNbr))
					self.bytes += len(rtpPacket.getPacket())

					try:
						if (self.frameNbr + 1 != rtpPacket.seqNum() and self.isForward == 0 and self.isBackWard == 0):
							self.counter += 1

					except:
						traceback.print_exc(file=sys.stdout)

					if currFrameNbr > self.frameNbr: # Discard the late packet
						print(currFrameNbr)
						self.frameNbr = currFrameNbr
						self.updateMovie(self.writeFrame(rtpPacket.getPayload()))
					self.totalTimeLabel.configure(text="Total time: %02d:%02d" % (self.totalTime // 60, self.totalTime % 60))
					self.remainingTimeLabel.configure(text="Remaining time: %02d:%02d" % ((self.totalTime - self.currentTime)// 60, (self.totalTime - self.currentTime) % 60))

					#Update packets statistical information
					self.totalPackets += 1
					self.packets += 1
					self.packetsLost += currFrameNbr - self.lastSequence - 1
					self.lastSequence = currFrameNbr

			except:
				# Stop listening upon requesting PAUSE or TEARDOWN
				if self.playEvent.isSet(): 
					self.displayStats()
					break
				
				# Upon receiving ACK for TEARDOWN request,
				# close the RTP socket
				if self.teardownAcked == 1:
					self.rtpSocket.shutdown(socket.SHUT_RDWR)
					self.rtpSocket.close()
					self.hasRtpSocket = False
					break
					
	def writeFrame(self, data):
		"""Write the received frame to a temp image file. Return the image file."""
		cachename = CACHE_FILE_NAME + str(self.sessionId) + CACHE_FILE_EXT
		file = open(cachename, "wb")
		file.write(data)
		file.close()
		
		return cachename
	
	def updateMovie(self, imageFile):
		"""Update the image file as video frame in the GUI."""
		photo = ImageTk.PhotoImage(Image.open(imageFile))
		self.label.configure(image = photo, height=288) 
		self.label.image = photo
		
	def connectToServer(self):
		"""Connect to the Server. Start a new RTSP/TCP session."""
		# Create a new socket socket.socket(family=AF_INET, type=SOCK_STREAM, proto=0, fileno=None)
		# AF_INET is an address family for IPv4, AF_INET6 for IPv6
		# SOCK_STREAM is for TCP socket
		# SOCK_DGRAM is for UDP socket
		self.rtspSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		try:
			self.rtspSocket.connect((self.serverAddr, self.serverPort))
		except:
			tkinter.messagebox.showwarning('Connection Failed', 'Connection to \'%s\' failed.' %self.serverAddr)
	
	def sendRtspRequest(self, requestCode):
		"""Send RTSP request to the server."""	
		# Setup request
		if requestCode == self.SETUP and self.state == self.INIT:
			# target is the callable object to be invoked by the run() or the start() method
			threading.Thread(target=self.recvRtspReply).start()
			# Update RTSP seqnum
			self.rtspSeq += 1
			
			# RTSP request string that we should send
			req = "SETUP " + self.fileName + " RTSP/1.0\nCSeq: " + str(self.rtspSeq) + "\nTransport: RTP/UDP; client_port= " + str(self.rtpPort)
			
			# Keep track of sent request
			self.requestSent = self.SETUP
		
		# Play request
		elif requestCode == self.PLAY and self.state == self.READY:
			# Update RTSP seqnum
			self.rtspSeq += 1
			
			# RTSP request string that we should send
			req = "PLAY " + self.fileName + " RTSP/1.0\nCSeq: " + str(self.rtspSeq) + "\nSession: " + str(self.sessionId)
			
			# Keep track of sent request
			self.requestSent = self.PLAY
		
		# Pause request
		elif requestCode == self.PAUSE and self.state == self.PLAYING:
			# Update RTSP seqnum
			self.rtspSeq += 1
			
			# RTSP request string that we should send
			req = "PAUSE " + self.fileName + " RTSP/1.0\nCSeq: " + str(self.rtspSeq) + "\nSession: " + str(self.sessionId)
			
			# Keep track of sent request
			self.requestSent = self.PAUSE
			
			
		# Teardown request
		elif requestCode == self.TEARDOWN and self.state != self.INIT:
			# Update RTSP seqnum
			self.rtspSeq += 1
			
			# RTSP request string that we should send
			req = "TEARDOWN " + self.fileName + " RTSP/1.0\nCSeq: " + str(self.rtspSeq) + "\nSession: " + str(self.sessionId)
			
			# Keep track of sent request
			self.requestSent = self.TEARDOWN

		elif requestCode == self.DESCRIBE:
			self.rtspSeq += 1
			req = "DESCRIBE " + self.fileName + " RTSP/1.0\nCSeq: " + str(self.rtspSeq) + "\nSession: " + str(self.sessionId)
			self.requestSent = self.DESCRIBE

		elif requestCode == self.FORWARD:
			self.rtspSeq +=1
			req = "FORWARD " + self.fileName + " RTSP/1.0\nCSeq: " + str(self.rtspSeq) + "\nSession: " + str(self.sessionId)
			self.requestSent = self.FORWARD
		
		elif requestCode == self.BACKWARD:
			self.rtspSeq +=1
			req = "BACKWARD " + self.fileName + " RTSP/1.0\nCSeq: " + str(self.rtspSeq) + "\nSession: " + str(self.sessionId)
			self.requestSent = self.BACKWARD

		else:
			return
		
		# Use rtspSocket to send rtsp request
		self.rtspSocket.send(req.encode())
		print('\nRequest sent:\n' + req)
	
	
	def recvRtspReply(self):
		"""Receive RTSP reply from the server."""
		while True:
			reply = self.rtspSocket.recv(1024)
			if reply: 
				self.parseRtspReply(reply.decode("utf-8"))
			# Close the RTSP socket upon requesting Teardown
			if self.requestSent == self.TEARDOWN:
				self.rtspSocket.shutdown(socket.SHUT_RDWR)
				self.rtspSocket.close()
				break
	
	def parseRtspReply(self, data):
		"""Parse the RTSP reply from the server."""
		# List of strings separated by '\n' that is returned from the server 
		# ex: data = "RTSP/1.0 200 OK\nCSeq: 1\nSession: 123456"
		lines = data.split('\n')
		seqNum = int(lines[1].split(' ')[1])

		# Process only if the server reply's sequence number is the same as the request's
		if seqNum == self.rtspSeq:
			session = int(lines[2].split(' ')[1])
			# New RTSP session ID
			if self.sessionId == 0:
				self.sessionId = session
			
			# Process only if the session ID is the same
			if self.sessionId == session:
				if int(lines[0].split(' ')[1]) == 200: 
					if self.requestSent == self.SETUP:
						#-------------
						# TO COMPLETE
						#-------------
						# Update RTSP state.
						self.totalTime = float(lines[3].split(' ')[1])
						self.FPS = float(lines[4].split(' ')[1])
						self.state = self.READY
						# Open RTP port.
						if not self.hasRtpSocket:
							self.openRtpPort() 
						self.disableButtons()
					elif self.requestSent == self.PLAY:
						self.state = self.PLAYING

						self.disableButtons()
					elif self.requestSent == self.PAUSE:
						self.state = self.READY

						# The play thread exits (set flag to exit while loop)
						self.playEvent.set()
						self.disableButtons()

					elif self.requestSent == self.TEARDOWN:
						self.state = self.INIT	
						self.teardownAcked = 1 

					elif self.requestSent == self.DESCRIBE:
						self.displayDescription(lines)

	def displayDescription(self, lines):
		top = Toplevel()
		top.title("Description")
		top.geometry('300x180')
		Lb1 = Listbox(top, width=80, height=20)
		Lb1.insert(1, "Describe: ")
		Lb1.insert(2, "Name Video: " + str(self.fileName))
		Lb1.insert(3, lines[1])
		Lb1.insert(4, lines[2])
		Lb1.insert(5, lines[3])
		Lb1.insert(6, lines[4])
		Lb1.insert(7, lines[5])
		Lb1.insert(8, lines[6])
		Lb1.insert(9, lines[7])
		Lb1.insert(10, lines[8])
		Lb1.insert(11, "Current time: " + "%02d:%02d" % (self.currentTime // 60, self.currentTime % 60))
		Lb1.pack()
						
	def displayStats(self):
		"""Displays observed statistics"""
		packetLossRate = ((self.counter) / (self.totalPackets)) * 100
		
		top1 = Toplevel()
		top1.title("Statistics")
		top1.geometry('300x170')
		Lb2 = Listbox(top1, width=80, height=20)
		
		listbox_info = [
    		f"Current Packets No.{self.frameNbr}",
    		f"Total Streaming Packets: {self.totalPackets} packets",
    		f"Packets Received: {self.packets} packets",
    		f"Packets Lost: {self.counter} packets",
    		f"Packet Loss Rate: {packetLossRate}%",
    		f"Play time: {self.currentTimeFloat:.2f} seconds",
    		f"Bytes received: {self.bytes} bytes",
    		f"Video Data Rate: {int(self.bytes / self.currentTimeFloat)} bytes per second",
		]

		# Insert the information into the listbox
		for info in listbox_info:
			Lb2.insert(END, info)
		
		Lb2.pack()

	
	def openRtpPort(self):
		"""Open RTP socket binded to a specified port."""
		#-------------
		# TO COMPLETE
		#-------------
		# Create a new datagram socket to receive RTP packets from the server
		# AF_INET is an address family for IPv4, AF_INET6 for IPv6
		# SOCK_STREAM is for TCP socket
		# SOCK_DGRAM is for UDP socket
		self.rtpSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
		self.hasRtpSocket = True
		# Set the timeout value of the socket to 0.5sec
		self.rtpSocket.settimeout(0.5)
		
		try:
			# Bind the socket to the address using the RTP port given by the client user
			self.rtpSocket.bind(('', self.rtpPort))
		except:
			tkinter.messagebox.showwarning('Unable to Bind', 'Unable to bind PORT=%d' %self.rtpPort)

	def closeWindow(self):
		"""Handler on explicitly closing the GUI window."""
		self.pauseMovie()
		if tkinter.messagebox.askokcancel("Quit?", "Are you sure you want to quit?"):
			self.sendRtspRequest(self.TEARDOWN)
			self.exitClient()
		else: # When the user presses cancel, resume playing.
			self.playMovie()
