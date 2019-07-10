# System Room Monitor (SRM)
# For revision history, see the SRM System Summary Appendix A
# Ops database version 10.01

from datetime import timedelta, datetime
import time
import Adafruit_BBIO.GPIO as GPIO
import Adafruit_BBIO.ADC as ADC
import sys
import smtplib

# System Level (Global) variables
#
location = ''
cmd_file = '' 
db_file = ''
digiInPins = []
alarms = []
lts = None # loop time stamp
tm = None
lts_string_short = None


#===========================================================================================	
def main():

	global location
	global tm
	#global tm_file 
	global cmd_file 
	global db_file
	global alarms
	global digiInPins
	#global lts_string_compact
	global lts_string_short
	global lts #, lts_string_short #lts_string_long, 
	#global convert_UTC_to_pacific_time
	digiInPinNames = []
	
	# Configure variables, control loop and fault protection flag timers
	# loop period in seconds
	#
	#cf_load_config = True             #causes the configuration to load
	cf_loadDB = True                  #causes the database to load
	tmLoopPeriod = 20 * 60            # slow loop
	tmLoopLastFinish = time.time() - tmLoopPeriod
	pin12_last_state = 0
	pin14_last_state = 0
	convert_UTC_to_pacific_time = 0

	
	# check the configuration database for the tm file location
	# create the telemetery logger
	tm_file = ''
	#tz = 0
	with open('srm.config','r') as cnfDB:
		cnfLines = cnfDB.readlines()
		cnfDB.close()
				
		for textLine in cnfLines:	
			if textLine[0] != '#':
				dbFields = textLine.split(',')
				if dbFields[0] == 'TM':
					tm_file = dbFields[1].strip()
				if dbFields[0] == 'TZ':
					#tz = int(dbFields[1].strip())
					convert_UTC_to_pacific_time = int(dbFields[1].strip())

	#lts = datetime.now()- timedelta(hours=tz)
	#convert_UTC_to_pacific_time = tz
	lts = datetime.now()- timedelta(hours=convert_UTC_to_pacific_time)
	tm = Logger(tm_file,convert_UTC_to_pacific_time)
	
	# load the complete configuration database (srm.config) 
	with open('srm.config','r') as cnfDB:
		cnfLines = cnfDB.readlines()
		cnfDB.close()
				
		for textLine in cnfLines:	
			if textLine[0] != '#':
				dbFields = textLine.split(',')
							
				if dbFields[0] == 'TM':
					tm_file = dbFields[1].strip()
					tm.log('0',"BBB Startup with srm.py")
					tm.log('0',"telemetry file: " + tm_file)	
						
				if dbFields[0] == 'CMD':
					cmd_file = dbFields[1].strip()
					tm.log('0',"command file: " + cmd_file)
						
				if dbFields[0] == 'DB':
					db_file = dbFields[1].strip()
					tm.log('0',"database file: " + db_file)
	
		tm.log('0',"Timezone: UTC -" + str(convert_UTC_to_pacific_time))
		
	# Configure analog input pins
	#
	global analogPins
	AIN0 = AnalogPin("AIN0","descr","F",0,0)
	AIN1 = AnalogPin("AIN1","descr","F",0,0)
	AIN2 = AnalogPin("AIN2","descr","F",0,0)
	AIN3 = AnalogPin("AIN3","descr","F",0,0)
	AIN4 = AnalogPin("AIN4","descr","F",0,0)
	AIN5 = AnalogPin("AIN5","descr","F",0,0)
	AIN6 = AnalogPin("AIN6","descr","F",0,0)
	analogPins = [AIN0,AIN1,AIN2,AIN3,AIN4,AIN5,AIN6]
	ADC.setup()
	
	while True:		# this is the fast loop
		#
		# get local time and create a time stamp for this loop instance
		# lts = loop timestamp
		#
		lts = datetime.now()- timedelta(hours=convert_UTC_to_pacific_time)
		lts_string_short = "{0:02d}:{1:02d}".format(lts.hour,lts.minute)

		lts_string_compact = "{0}{1:02d}{2:02d}{3:02d}{4:02d}{5:02d}".format(lts.year,lts.month,lts.day,lts.hour,lts.minute,lts.second)
							
		# load the ops database (BBB03.db) into variables
		if cf_loadDB == True:
			with open(db_file,'r') as opsDB:
				opsLines = opsDB.readlines()
				opsDB.close()

				alarms = []					
				for textLine in opsLines:	
					if textLine[0] != '#':
						dbFields = textLine.split(',')

						if dbFields[0] == 'DGP': # read digital pin names			
							for pinName in dbFields[1:]:
								GPIO.setup(pinName, GPIO.IN)
								digiInPins.append(DigiPin(pinName))

						if dbFields[0] == 'LOC':
							global location
							location = dbFields[1].strip()
							tm.log('0', 'location: ' + location)	

						#if dbFields[0] == 'TZB':
						#	convert_UTC_to_pacific_time = int(dbFields[1])
						#	print(convert_UTC_to_pacific_time)
							
						# analog pins parameters (m and b)
						#
						if dbFields[0] == 'LRV':
							if dbFields[6]=='P9_39':
								AIN0.set_m(dbFields[11])
								AIN0.set_b(dbFields[12])
							if dbFields[6]=='P9_70':
								AIN1.set_m(dbFields[11])
								AIN1.set_b(dbFields[12])
							if dbFields[6]=='P9_37':
								AIN2.set_m(dbFields[11])
								AIN2.set_b(dbFields[12])
							if dbFields[6]=='P9_38':
								AIN3.set_m(dbFields[11])
								AIN3.set_b(dbFields[12])
							if dbFields[6]=='P9_33':
								AIN4.set_m(dbFields[11])
								AIN4.set_b(dbFields[12])
							if dbFields[6]=='P9_36':
								AIN5.set_m(dbFields[11])
								AIN5.set_b(dbFields[12])
							if dbFields[6]=='P9_35':
								AIN6.set_m(dbFields[11])
								AIN6.set_b(dbFields[12])
								
							
						if dbFields[0] == 'Alarm':
							new_alarm = Alarm(int(dbFields[1]),dbFields[6])
							new_alarm.set_triggerwait_time(int(dbFields[4]))
							new_alarm.set_response_period(int(dbFields[5]))
							if int(dbFields[3]) == 1 : new_alarm.Enable()
							if int(dbFields[2]) == 1 : new_alarm.Arm()
							for i in range(7,len(dbFields)):
								new_alarm.AddSendTo(dbFields[i].strip())
							alarms.append(new_alarm)
	
			tm.log('0', 'Ops Database Loaded')
			for a in alarms: tm.log('0', a.parameters)
			cf_loadDB = False	
			
				
		# ***********************************************************
		# * telemetry processing
		# *
		# ***********************************************************
		#
		# pre-read each pin lrv and set in each pin object
		#
		for pin in digiInPins:
			pin.read_and_store_lrv()
			
		for pin in analogPins:
			pin.read_and_store_lrv()
			
		# ***********************************************************
		# * alarm processing
		# *
		# ***********************************************************
		#
		# check alarm pin value real time
		#print(str(digiInPins[4].lrv) + ' ' + str(digiInPins[4].has_flipped) + ' ' + str(digiInPins[4]._last_change_time))
		
		for a in alarms:
				a.ProcessAlarm()
					
		# ***********************************************************
		# * command processing
		# *
		# ***********************************************************
		#
		# open the command file, read all commands contained, clear and close 
		# the command file
		try:
			with open(cmd_file, "r+") as cmdFile:
				commands = cmdFile.readlines()
				if len(commands) > 0:
					cmdFile.truncate(0)
				cmdFile.close()
		except:
			pass

		for command_line in commands:
			# check validity and cleanup command text
			#
			#print(len(command_line.strip()))
			ignore = False
			valid = True
			executed = False

			# ignore commands that are only blank lines (with a /n)
			#
			if len(command_line.strip()) <= 1:
				ignore = True
			
			try:
				command_parts = command_line.split(",")
				if not ignore:
					for i in range(len(command_parts)):
						
						# clean up the command parts, remove non-alpha and non-numeric characters
						#
						clean_part = ''
						for c in str(command_parts[i]):
							if c.isalpha() or c.isdigit(): clean_part += c
						
						# check validity of command position 0
						# starts with 'cmd', ends with a number ie 'cmd100'
						#
						if i == 0: 
							if clean_part[:3] != 'cmd': valid = False
							if not clean_part[3:].isdigit(): valid = False

						command_parts[i] = clean_part
					
					if valid:
						print(command_parts)
						command_parts[1] = "{0:08b}".format(int(command_parts[1], 16))
						scb = command_parts[1]
						
						if command_parts[0] == "cmd100":
							if scb == "00000000":               # status
								for a in alarms: tm.log('0',a.parameters)
								executed = True
							if scb[0] == "1":pass	            # shutdown BBB
							if scb[1] == "1":pass	            # restart BBB
							if scb[2] == "1":					# stop srm
								tm.log('0','srm terminated by CMD100')
								sys.exit('srm terminated by CMD100')
								executed = True
							if scb[3] == "1":               	# reload ops database
								cf_loadDB = True
								executed = True
							if scb[4] == "1":pass	            # set time to NTP server time
							if scb[5] == "1":pass	            # set time zone bias
							if scb[6] == "1":pass	            # set maximim log file size
							if scb[7] == "1":                   # clear log file
								pass

						elif command_parts[0] == "cmd101":tm.log('0', 'Command 101')
						
						elif command_parts[0] == "cmd102":
							passed_alarmID = int(command_parts[2])
							alarm_index = 99
							write_to_log = False
							for i in range(0,len(alarms)):
								if alarms[i].alarmID == passed_alarmID:
									alarm_index = i
									executed = True
							if scb[0] == "1":pass	            
							if scb[1] == "1":pass	            
							if scb[2] == "1":pass				
							if scb[3] == "1":               	# write alarm config to log
								write_to_log = True
								executed = True
							if scb[4] == "1":pass	            
							if scb[5] == "1":pass	            
							if scb[6] == "1":   	            # arm alarm
								alarms[alarm_index].Arm()
								executed = True
							elif scb[6] == "0":
								alarms[alarm_index].Disarm()
								executed = True
							if scb[7] == "1":                   # enable alarm
								alarms[alarm_index].Enable()
								executed = True
							elif scb[7] == "0":
								alarms[alarm_index].Disable()
								executed = True

							if write_to_log:
								for a in alarms: tm.log('0',a.parameters)
						
						if executed:
							tm.log('0', 'Executed Command: ' + str(command_parts))
						
					else: # if valid
						tm.log('0', 'Rejected Command Part: ' + command_line.strip())
			except:
				tm.log('0', 'Rejected Command: ' + command_line.strip())

			
		# ***********************************************************				
		# slower loop, tm output, slow alarms
		#
		# ***********************************************************		
		if time.time()-tmLoopLastFinish >= tmLoopPeriod:
			tmStream = '' # lts_string_compact + ' ' + 'BBB01' + ' ' + '1 '
		
			for pin in analogPins:
				# tmStream += '{:5.1f}F'.format(pin.lrvu())
				tmStream += str(pin.lrv)
				tmStream += ' '
				
			binary_text = ''	
			for pin in digiInPins:
				binary_text += '{0}'.format(pin.lrv)

			tmStream += hex(int(binary_text,2)).upper()[2:-1].zfill(8)

			for pin in digiInPins:
				tmStream += ' ' + str(pin.since_last_change)
			
			tmStream += ' '

			tm.log('1',tmStream)
			tmLoopLastFinish = time.time()
		#####
		# end of tm output loop	

		time.sleep(1)
	##### end of core loop
#===========================================================================================		

def AlarmCondition(alarmID):
# helper function for the alarm class, this is location dependent
# keeps the formulas outside the alarm class
# there needs to be an entry in this function for each alarm and they need to correspond to the
# BBB.db ops database entries.
# returns a tuple (state, lrv). 
#   state=True for alarm condition
#   lrv is the value of the lrv that caused the alarm (like a temperature)
	
	# Westridge Alarms
	if location == 'wli':
		if alarmID == 401: #server room door		
			pin = digiInPins[7]
			if pin.lrv == 0: return (True,0)
			else: return (False,1)
		if alarmID == 403: #room temperature high		
			pin = analogPins[0]
			alarm_lrv = pin.lrvu
			if alarm_lrv > 75.0: return (True,str(round(alarm_lrv,1)) + 'F')
			else: return (False,1)	
		if alarmID == 404: #room temperature low		
			pin = analogPins[0]
			alarm_lrv = pin.lrvu
			if alarm_lrv < 60.0: return (True,str(round(alarm_lrv,1)) + 'F')
			else: return (False,1)
		if alarmID == 406: #power out in server room		
			pin = digiInPins[12]
			if pin.lrv == 0: return (True,0)
			else: return (False,1)	
		if alarmID == 407: #building alarm set		
			pin = digiInPins[20]
			if pin.lrv == 0:
				if pin.just_flipped: return (True,1)
			return (False,0)
		if alarmID == 408: #building alarm disarm		
			pin = digiInPins[20]
			if pin.lrv == 1:
				if pin.just_flipped: return (True,1)
			return (False,0)
		if alarmID == 409: #building alarm not set at 9:00pm		
			pin = digiInPins[20]
			if pin.lrv == 1 and lts.hour == 21: #the alarm is disarmed and time is up
				return (True,1)
			return (False,0)

	# Faircove Alarms			
	if location == 'faircove':
		if alarmID == 401 or alarmID == 405: # hall door, alarm 401 or 405 condition met?		
			pin = digiInPins[12]
			if pin.lrv == 0: return (True,0)
			else: return (False,1)
		elif alarmID == 402:	# garage door left open, alarm 402 condition met?	
			pin = digiInPins[14]
			if pin.lrv == 0: return (True,0)
			else: return (False,1)
		elif alarmID == 410: # garage door #1 went up, alarm 410 condition met? Added 2018.11.26		
			pin = digiInPins[14]
			if pin.lrv == 0: 
				if pin.just_flipped: return (True,0)
			return (False,1)
			
class AnalogPin:
	
	def __init__(self, pin, descr, units, m, b):
		self._pinName = pin
		self._descr   = descr
		self._units   = units
		self._m       = float(m)
		self._b       = float(b)
		self._lrv = 0              # the read value for the lrv

	def read_and_store_lrv(self):
		#return r 
		# returns the raw lrv
		#
		averageRead = int(0)
		for x in range(0,4):
			averageRead = averageRead + int(ADC.read_raw(self._pinName))
			# time.sleep(1)
		self._lrv =  int(averageRead/5)
		
	@property			
	def lrv(self):
		# returns the raw lrv
		#
		return self._lrv
	
	@property		
	def lrvu(self):
		# returns the lrv converted to units using y = mx + b
		#
		return float((self._m * self._lrv) + self._b)

		
	def pinName(self): return self._pinName
	def units(self):   return self._units
	def m(self):       return self._m
	def b(self):	   return self._b
	def descr(self):   return self._descr

	def set_pinName(self,a):  self._pinName = str(a)
	def set_units(self,a):    self._units = str(a)
	def set_m(self,a):        self._m = float(a)
	def set_b(self,a):	      self._b = float(a)
	def set_descr(self,a):    self._descr = str(a)
		
class DigiPin:

	def __init__(self, pin):
		self._pinName = pin
		self._lrv = int(1) if GPIO.input(self._pinName) else int(0)
		# self._last_value = int(1) if GPIO.input(self._pinName) else int(0)
		self._has_flipped  = False
		self._just_flipped = False
		self._last_change_time = datetime.now()
	
	def read_and_store_lrv(self):
		self._new_value = int(1) if GPIO.input(self._pinName) else int(0)
		if self._new_value != self._lrv:
			self._last_change_time = datetime.now()
			self._has_flipped = True
			self._just_flipped = True
		else:
			self._just_flipped = False
		self._lrv = self._new_value 
		
	@property
	def since_last_change(self): #time since this LRV was last changed in Minutes
		if self._has_flipped:
			return int((datetime.now() - self._last_change_time).total_seconds())
		else:
			return -1

	@property		
	def lrv(self):
		return self._lrv 

	@property			
	def name(self):
	    return self._pinName

	@property			
	def has_flipped(self):
	    return self._has_flipped

	@property			
	def just_flipped(self):
	    return self._just_flipped		
	
class Logger:
	def __init__(self, log_file_name, tz_offset):
		self.log_file = str(log_file_name)
		self.tz = int(tz_offset)
		self.tm_sequence = 0
		self.lts_string_compact = '1' #time stamp in a string
		self.last_lts_string_compact = '0'
		
	def log(self, type, text):	
		self.lts_string_compact = "{0}{1:02d}{2:02d}{3:02d}{4:02d}{5:02d}".format(lts.year,lts.month,lts.day,lts.hour,lts.minute,lts.second)
		if self.last_lts_string_compact == self.lts_string_compact:
			self.tm_sequence += 1
		else:
			self.tm_sequence = 0
		self.tm_sequence_text = '{0:03d}'.format(self.tm_sequence)
		log_text = self.lts_string_compact + self.tm_sequence_text + ' ' + 'BBB01 ' + str(type) + ' ' + str(text)
		with open(self.log_file,'a') as lf:
			lf.write(log_text + '\n')
			lf.close()
		print (log_text)
		self.last_lts_string_compact = self.lts_string_compact

class Alarm:		
	def __init__(self, alarmID, description = ""):
		self._alarmID = alarmID
		self._description = description
		self._armed   = False
		self._enabled = False
		self._responsePeriod = 600
		#self._quietTime = 600
		self._sendTo = 'johnspielman@hotmail.com'
		self._triggerWaitTime = 0
		self._state = "M"
		self._lastRespondTime = 0
		self._triggerTime = 0
		self._last_condition = False
		self._current_condition = False
		self._notify_list = []

    # fixed parameters
    #
	@property
	def alarmID(self): return self._alarmID

    # changeable parameters
	#
	@property
	def description(self): return self._description

	@property
	def response_period(self): return self._responsePeriod
		
	def set_response_period(self, v):	self._responsePeriod = v
	def set_trigger_time(self, v): self._triggerTime = v
	
	#@property
	def trigger_wait_time(self): return self._triggerWaitTime
	def set_triggerwait_time(self, v): self._triggerWaitTime = v


	def ProcessAlarm(self):

		# alarm condition met?
		(self._current_condition, alarm_lrv) =  AlarmCondition(self._alarmID)

		if self._enabled:
			if self._current_condition:  #alarm condition met?
				if self._state == 'M':
					self._state = 'T'
					self._triggerTime = time.time()
					tm.log('A', 'Alarm:' + str(self._alarmID) + ' Triggered')
				if (time.time() - self._triggerTime >= self._triggerWaitTime):  # trigger timer run out?
					self._state = 'R'
					if (time.time() - self._lastRespondTime >= self._responsePeriod):  # response timer run out?
						self._lastRespondTime = time.time()
						alarm_message = lts_string_short + ' ' + self._description + ' ' + str(alarm_lrv)
						tm.log('A', 'Alarm:' + str(self._alarmID) + ' [' + alarm_message + ']')
						if self._armed:	
							for rx in self._notify_list:
								self.sendAlarm(rx,alarm_message)	# sending a text message	
			else:
				if self._state != 'M':
					self._state = 'M'
					self._triggerTime = time.time()
					tm.log('A', ' Alarm:' + str(self._alarmID) + ' RTN ')


		
	
    # Alarm status (armed or disarmed) parameters
    #
	def Arm(self):     self._armed = True		
	def Disarm(self):  self._armed = False
	def Enable(self):  self._enabled = True		
	def Disable(self): self._enabled = False
	
	@property
	def arm_status(self): 
		if self._armed:
			return 'armed'
		else:
			return 'disarmed'
	
	@property
	def enable_status(self): 
		if self._enabled:
			return 'enabled'
		else:
			return 'disabled'

	@property
	def state(self):
		return self._state

	@property
	def parameters(self):
		# returns a string with a summary of current alarm parameters
		#
		rx_list = ''
		for rx in self._notify_list: rx_list = rx_list + ' ' + rx
		rt =  'AlarmID=' + str(self._alarmID) 
		rt += ' ' + self.enable_status
		rt += ' ' + self.arm_status
		rt += ' ' + self._description
		rt += ' TWT=' + str(self._triggerWaitTime) + ' RT=' + str(self._responsePeriod)
		rt += ' SendTo=' + rx_list        
		return rt
	
	def AddSendTo(self, address):
		self._notify_list.append(address)
		
	def sendAlarm(self, toaddrs, message):
		message =  " " + message # this is required or the text won't display the message
		fromaddr = ''
		username = ''
		password = ''
		try:
			server = smtplib.SMTP_SSL('')
			server.login(username,password)
			server.sendmail(fromaddr, toaddrs, message)
			tm.log('A', ' Notified:' + toaddrs)
		except:
			tm.log('A', ' Notified: COULD NOT SEND NOTIFICATION')
		return()
		

		
#if __name__ == "__main__": main()		
main()

	
