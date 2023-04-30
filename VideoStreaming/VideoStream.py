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
		self.isForward = 0
		self.totalFrame = 0
	def get_total_time(self):
		data = cv2.VideoCapture(self)
		frames = data.get(cv2.CAP_PROP_FRAME_COUNT)
		fps = data.get(cv2.CAP_PROP_FPS)
	
		seconds = round(frames / fps)
		video_time = datetime.timedelta(seconds=seconds)

		return seconds
	
	def setForward(self):
		self.isForward = 1
		
	def nextFrame(self):
		"""Get next frame."""
		if self.isForward == 1: #case client require forward video
			forwardFrame = int(self.totalFrame*0.1)
			remainFrame = int (self.totalFrame - self.frameNum)
			if forwardFrame > remainFrame:
				forwardFrame = remainFrame
			self.isForward = 0
		else:
			forwardFrame = 1
		if forwardFrame:
			for i in range(forwardFrame):
				data = self.file.read(5) # Get the framelength from the first 5 bits
				if data: 
					framelength = int(data)
									
					# Read the current frame
					data = self.file.read(framelength)
					self.frameNum += 1
			return data
		
	def prevFrame(self):
		prevFrames = int(self.totalFrame * 0.1)
		if prevFrames >= self.frameNum:
			data = self.file.seek(0)
			self.frameNum = 0
			if data:
				framelength = int(data)
				data = self.file.read(framelength)
				self.frameNum += 1
		else:
			data = self.file.seek(0)
			back_Frames = self.frameNum - prevFrames
			self.frameNum = 0
			for i in range(back_Frames):
				data = self.nextFrame()
		return data

	def frameNbr(self):
		"""Get frame number."""
		return self.frameNum
	

	
