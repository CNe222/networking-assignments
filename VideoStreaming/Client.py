from tkinter import *
import tkinter.messagebox
from PIL import Image, ImageTk
import socket, threading, sys, traceback, os

from RtpPacket import RtpPacket

CACHE_FILE_NAME = "cache-"
CACHE_FILE_EXT = ".jpg"

class Client:
	INIT = 0
	READY = 1
	PLAYING = 2
	state = INIT
	
	SETUP = 0
	PLAY = 1
	PAUSE = 2
	TEARDOWN = 3
	
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
		self.rtspSeq = 0
		self.sessionId = 0
		self.requestSent = -1
		self.teardownAcked = 0
		self.connectToServer()
		self.frameNbr = 0
		
	# THIS GUI IS JUST FOR REFERENCE ONLY, STUDENTS HAVE TO CREATE THEIR OWN GUI 	
	def createWidgets(self):
		"""Build GUI."""
		# Create Setup button
		self.setup = Button(self.master, width=20, padx=3, pady=3)
		self.setup["text"] = "Setup"
		self.setup["command"] = self.setupMovie
		self.setup.grid(row=1, column=0, padx=2, pady=2)
		
		# Create Play button		
		self.start = Button(self.master, width=20, padx=3, pady=3)
		self.start["text"] = "Play"
		self.start["command"] = self.playMovie
		self.start.grid(row=1, column=1, padx=2, pady=2)
		
		# Create Pause button			
		self.pause = Button(self.master, width=20, padx=3, pady=3)
		self.pause["text"] = "Pause"
		self.pause["command"] = self.pauseMovie
		self.pause.grid(row=1, column=2, padx=2, pady=2)
		
		# Create Teardown button
		self.teardown = Button(self.master, width=20, padx=3, pady=3)
		self.teardown["text"] = "Teardown"
		self.teardown["command"] =  self.exitClient
		self.teardown.grid(row=1, column=3, padx=2, pady=2)
		
		# Create a label to display the movie
		self.label = Label(self.master, height=19)
		self.label.grid(row=0, column=0, columnspan=4, sticky=W+E+N+S, padx=5, pady=5) 

	# Disable buttons at each state
	def disableButtons(self):
		if self.state == self.INIT:
			self.setup["state"] = "normal"
			self.start["state"] = "disabled"
			self.pause["state"] = "disabled"
			self.teardown["state"] = "disabled"
		elif self.state == self.READY:
			self.setup["state"] = "disabled"
			self.start["state"] = "normal"
			self.pause["state"] = "disabled"
			self.teardown["state"] = "normal"
		elif self.state == self.PLAYING:
			self.setup["state"] = "disabled"
			self.start["state"] = "normal"
			self.pause["state"] = "normal"
			self.teardown["state"] = "normal"

	
	def setupMovie(self):
		"""Setup button handler."""
		if self.state == self.INIT:
			self.sendRtspRequest(self.SETUP)
	
	def exitClient(self):
		"""Teardown button handler."""
		self.sendRtspRequest(self.TEARDOWN)
		# close the GUI
		self.master.destroy()
		# Remove cache image stored in folder (ex: cache-123456.jpg)
		os.remove(CACHE_FILE_NAME + str(self.sessionId) + CACHE_FILE_EXT)

	def pauseMovie(self):
		"""Pause button handler."""
		if self.state == self.PLAYING:
			self.sendRtspRequest(self.PAUSE)
	
	def playMovie(self):
		"""Play button handler."""
		if self.state == self.READY:
			# Create new thread that listens for RTPpackets
			threading.Thread(target=self.listenRtp).start()
			# Implement new event and assign to self.playEvent
			# The threading.Event provides an easy way to share a boolean variable _flag between threads that can act as a trigger for an action.
			# Initially, _flag is false
			self.playEvent = threading.Event()
			# Ensure that _flag is false using clear method
			self.sendRtspRequest(self.PLAY)

	
	def listenRtp(self):		
		"""Listen for RTP packets."""
		while True:
			try:
				data = self.rtpSocket.recv(20480)
				if data:
					rtpPacket = RtpPacket()
					rtpPacket.decode(data)
					
					currFrameNbr = rtpPacket.seqNum()
					print("Current Seq Num: " + str(currFrameNbr))
										
					if currFrameNbr > self.frameNbr: # Discard the late packet
						self.frameNbr = currFrameNbr
						self.updateMovie(self.writeFrame(rtpPacket.getPayload()))
			except:
				# Stop listening upon requesting PAUSE or TEARDOWN
				if self.playEvent.isSet(): 
					break
				
				# Upon receiving ACK for TEARDOWN request,
				# close the RTP socket
				if self.teardownAcked == 1:
					self.rtpSocket.shutdown(socket.SHUT_RDWR)
					self.rtpSocket.close()
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
			req = "PLAY " + self.fileName + " RTSP/1.0\nCSeq: " + str(self.rtspSeq) + " Session: " + str(self.sessionId)
			
			# Keep track of sent request
			self.requestSent = self.PLAY
		
		# Pause request
		elif requestCode == self.PAUSE and self.state == self.PLAYING:
			# Update RTSP seqnum
			self.rtspSeq += 1
			
			# RTSP request string that we should send
			req = "PAUSE " + self.fileName + " RTSP/1.0\nCSeq: " + str(self.rtspSeq) + " Session: " + str(self.sessionId)
			
			# Keep track of sent request
			self.requestSent = self.PAUSE
			
			
		# Teardown request
		elif requestCode == self.TEARDOWN and not self.state == self.INIT:
			# Update RTSP seqnum
			self.rtspSeq += 1
			
			# RTSP request string that we should send
			req = "TEARDOWN " + self.fileName + " RTSP/1.0\nCSeq: " + str(self.rtspSeq) + " Session: " + str(self.sessionId)
			
			# Keep track of sent request
			self.requestSent = self.PAUSE

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
						self.state = self.READY
						# Open RTP port.
						self.openRtpPort() 
					elif self.requestSent == self.PLAY:
						self.state = self.PLAYING
					elif self.requestSent == self.PAUSE:
						# self.state = ...
						self.state=self.READY
						# The play thread exits. A new thread is created on resume.
						self.playEvent.set()
					elif self.requestSent == self.TEARDOWN:
						# self.state = ...
						self.state = self.INIT
						# Flag the teardownAcked to close the socket.
						self.teardownAcked = 1 

					# Disable and activate buttons on each state of client
					self.disableButtons()

	
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
			self.exitClient()
		else: # When the user presses cancel, resume playing.
			self.playMovie()
