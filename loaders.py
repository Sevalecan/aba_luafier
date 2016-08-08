import os
from pathlib import Path
import re
import lupa
from lupa import LuaRuntime
import argparse
from converter import FixNumeric

# Converts a Lua table to nested dicts.
def ExpandTable(table):
	indices = []
	lint = lupa.LuaRuntime()
	tabletype = type(lint.eval('{a=[[b]]}'))	# Get type info for a lupa table.
	try:
		# Convert the table to a dict if possible.
		table = dict(table)
		# Set up a list and continue through the tree converting
		# lUA tables whenever encountered.
		indices = [(table, x) for x in table.keys()]
		
		while len(indices) > 0:
			tb,key = indices.pop()
			try:
				# Convert sub-variable to dict if possible.
				if type(tb[key]) != tabletype:
					continue
				tb[key] = dict(tb[key])
				indices.extend([(tb[key], x) for x in tb[key].keys()])
			except (ValueError, TypeError):
				pass
	except (ValueError, TypeError):
		pass # If not possible to convert to a dict, assume it is a primitive Python type
		pass # and needs no further manipulation.
	return table

def LoadLua(filepath):
	if type(filepath) == type(""):
		filepath = Path(filepath)
	lua = LuaRuntime(unpack_returned_tuples=True)
	lua_code = filepath.read_bytes().decode('utf-8')
	unit = lua.execute(lua_code)
	
	return ExpandTable(unit)

# Custom exception for dropping out of more than one loop at a time.
class ExitLoop( Exception ):
		pass
	
def FixUnitTypes(unit):
	# List the unit fields that should be a string type and make sure to convert them accordingly.
	strfields = ["category", "buildpic", "buildinggrounddecaltype", "collisionvolumeoffsets", "collisionvolumescales", "collisionvolumetype", "corpse", "description", "explodeas", "icontype", "name", "objectname", "selfdestructas", "yardmap", "side", "name", "badtargetcategory", "copyright", "defaultmissiontype", "nochasecategory", "selfdestructas", "unitname", re.compile("w[a-z]{3}_badtargetcategory", re.I), re.compile("weapon[0-9]+", re.I), re.compile("weaponmaindir[0-9]+", re.I), re.compile("onlytargetcategory[0-9]*", re.I), re.compile("badtargetcategory[0-9]+", re.I), re.compile("explosiongenerator[0-9]+", re.I), "soundcategory", "designation", "tedclass", "movementclass", "tracktype", "flankingbonusdir", "script"]
	# List of boolean fields for conversion. FBI Files used 1/0, lua uses true/false
	boolfields = ["usebuildinggrounddecal", "builder", "canmove"]
	loadfields = ["soundcategory"]
	retype = type(re.compile(""))	# Get type information for compiled regular expression.
	
	for i in unit.keys():
		# lowercase keys make for easy comparison.
		j = i.lower()
		
		try:
			# Check if the variable is in strfields or boolfields and try to convert.
			# Else try converting to int, or if that fails, float.
			# If call conversions fail, do nothing???
			for k in strfields:
				if type(k) == retype:
					if k.match(j):
						unit[i] = str(unit[i])
						raise ExitLoop
				elif j == k:
					unit[i] = str(unit[i])
					raise ExitLoop
			for k in boolfields:
				if k == j:
					unit[i] = bool(unit[i])
					raise ExitLoop
			try:
				unit[i] = int(unit[i])
				raise ExitLoop
			except (ValueError, TypeError):
				pass
			try:
				unit[i] = float(unit[i])
			except (ValueError, TypeError):
				pass	# Reaching this point could indicate a problem with the FBI file format.
		except ExitLoop:
			pass
	return unit

	

class TDFFrame:	# Class for holding frame information while parsing TDF files.
	def __init__(self):
		self.sections = {}
		self.cursec = ""
		self.name = []
		self.cname = ""
		self.value = []
		self.cvalue = ""
		self.state = 0
		self.retstate = 0
		self.slashcount = 0

# TDFs, FBIs and the like all seem to be exactly the same format.
# We can probably just use LoadTDF on all of them.		
def LoadTDF(filename):
	filename = str(filename)
	f = open(filename, 'rb')
	tdf_data = f.read().decode("latin_1")	# Encoding is latin_1. This is determined by a single unicode
											# character present in one file.
	#tdf_data = f.read().decode("UTF-8", "ignore")
	newlines = "\r\n"
	spaces = "\t "
	frames = []	# TDFFrames stack.
	line = 1	# What line we're on for detecting a syntax error.
	fr = TDFFrame()	# Initialize the current frame. Each sub-structure in a TDF gets its own parsing frame.
	for i in tdf_data:	# Iterate over data loaded from the TDF or FBI file.
		if i == '\n':	# Detect newline.
			line = line + 1
		if i == "/":	# Count slashes for comments.
			fr.slashcount = fr.slashcount + 1
		else:
			if fr.slashcount > 0 and fr.state == 2: # Handle comments on a header line.
				raise Exception("TDF Error: Expecting '{' in " + filename + ":" + str(line))
			fr.slashcount = 0
			
		if fr.state == 0:	# Waiting for a section header. TODO: Check for comment in this state as well.
			if i == '[': # Begin section header
				fr.name = []
				fr.state = 1
		elif fr.state == 1: # Reading the header
			if i == ']':
				fr.cursec = ''.join(fr.name)	# Get the name from parsed characters.
				fr.sections[fr.cursec] = {}		# Clear the current section as we've
				fr.state = 2					# just entered a new one.
				continue
			elif i not in newlines:
				fr.name.append(i)				# load section name.
			else:
				raise Exception("TDF Error: newline or carriage return in section header.")
		elif fr.state == 2:	# Waiting for a data section.
			if fr.slashcount == 2:				# If we have a comment, skip until the next line.
				fr.state = 4					# Set to comment state.
				fr.restate = 2					# Remember the context the comment was placed in.
			if i in newlines or i in spaces:
				pass
			elif i == "{":	# Entered data section. Initialize name list and change state.
				fr.name = []
				fr.state = 3
			elif i != '/':	# Disallow anything other than the section block or a comment here.
				raise Exception("TDF Error: Expecting '{' in " + filename + ":" + str(line))
		elif fr.state == 3:	# Waiting for end of data section or some more data.
			if fr.slashcount == 2:	# Skip comment for this line, remember state.
				fr.state = 4
				fr.retstate = 3
			elif i == "}":	    # Data section ended.
				if len(frames): # Drop to the next highest frame if there is one.
					parent = frames[-1]
					parent.sections[parent.cursec][fr.cursec] = fr.sections[fr.cursec]
					fr = frames.pop()
				else:
					fr.state = 0	# Else exit to state 0 and wait for EOF or another section header.
			elif i in newlines:	# Skip
				fr.name = []
			elif i == "=":	# Variable name complete, next load the data in the variable.
				fr.cname = "".join(fr.name)
				fr.value = []
				fr.state = 5
			elif i == "[":	# A sub-section was encountered. Create a new TDF frame and push this one to the stack.
				frames.append(fr)
				fr = TDFFrame()
				fr.state = 1	# In a new frame, but our section header has already started, so go to state 1.
			elif i not in spaces:	# Append another name character to the list.
				fr.name.append(i)
		elif fr.state == 4: # We're in a comment. Wait for line end.
			if i in newlines:
				fr.state = fr.retstate
		elif fr.state == 5: # Now reading the value for an item. Wait for semicolon.
			if i == ";":
				fr.cvalue = "".join(fr.value)
				fr.sections[fr.cursec][fr.cname] = fr.cvalue
				fr.state = 3
			else:
				fr.value.append(i)
	return fr.sections


