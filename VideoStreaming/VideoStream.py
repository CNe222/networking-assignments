import cv2
import datetime
class VideoStream:
	def __init__(self, filename):
		self.filename = filename
		try:
			self.file = open(filename, 'rb')
		except:
			raise IOError
		self.frameNum = 0
		self.isForward = False
		# init totalFrames to 0
		self.totalFrames = 0

		# read through file to upate totalFrames
		while True:
			data = self.file.read(5)
			if data:
				framelength = int(data)
				# Read the current frame
				data = self.file.read(framelength)
				self.totalFrames += 1
			else:
				self.file.seek(0)
				break

		self.totalTime = self.totalFrames * 0.05


	def getTotalTime(self):
		return self.totalTime
	
	def setForward(self):
		self.isForward = 1
		
	def nextFrame(self):
		"""Get next frame."""
		
		forwardFrames = 1
		if self.isForward:
			forwardSeconds = 2
			forwardFrames = int(self.getFPS() * forwardSeconds)
			self.isForward = False

		for _ in range(forwardFrames):
			data = self.file.read(5) # Get the framelength from the first 5 bits

			if data: 
				framelength = int(data)
				# Read the current frame
				data = self.file.read(framelength)
				self.frameNum += 1
		return data
		
	def prevFrame(self):
		backwardSeconds = 2
		backwardFrames = int(self.getFPS() * backwardSeconds)
		
		# change the pointer of video to the beginning of the file
		data = self.file.seek(0)
		# The frame number that we want to reach
		prevFrameNum = self.frameNum - backwardFrames
		self.frameNum = 0
		for _ in range(prevFrameNum):
			data = self.nextFrame()

		return data

	def frameNbr(self):
		"""Get frame number."""
		return self.frameNum
	
	def getFPS(self):
		fps = self.totalFrames // self.totalTime
		return fps
	
