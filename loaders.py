import os
from pathlib import Path
import re
import lupa
from lupa import LuaRuntime
import argparse



# Converts a Lua table to nested dicts.
def ExpandTable(table):
	indices = []
	lint = lupa.LuaRuntime()
	tabletype = type(lint.eval('{a=[[b]]}'))
	try:
		table = dict(table)
		indices = [(table, x) for x in table.keys()]
		
		while len(indices) > 0:
			tb,key = indices.pop()
			try:
				if type(tb[key]) != tabletype:
					continue
				tb[key] = dict(tb[key])
				indices.extend([(tb[key], x) for x in tb[key].keys()])
			except (ValueError, TypeError):
				pass
	except (ValueError, TypeError):
		pass
	return table

def LoadLUA(filepath):
	lua = LuaRuntime(unpack_returned_tuples=True)
	lua_code = filepath.read_bytes().decode('utf-8')
	unit = lua.execute(lua_code)
	
	return ExpandTable(unit)

class ExitLoop( Exception ):
		pass
	
def FixUnitTypes(unit):
	strfields = ["category", "buildpic", "buildinggrounddecaltype", "collisionvolumeoffsets", "collisionvolumescales", "collisionvolumetype", "corpse", "description", "explodeas", "icontype", "name", "objectname", "selfdestructas", "yardmap", "side", "name", "badtargetcategory", "copyright", "defaultmissiontype", "nochasecategory", "selfdestructas", "unitname", re.compile("w[a-z]{3}_badtargetcategory", re.I), re.compile("weapon[0-9]+", re.I), re.compile("weaponmaindir[0-9]+", re.I), re.compile("onlytargetcategory[0-9]*", re.I), re.compile("badtargetcategory[0-9]+", re.I), re.compile("explosiongenerator[0-9]+", re.I), "soundcategory", "designation", "tedclass", "movementclass", "tracktype", "flankingbonusdir", "script"]
	boolfields = ["usebuildinggrounddecal", "builder", "canmove"]
	loadfields = ["soundcategory"]
	retype = type(re.compile(""))
	
	for i in unit.keys():
		j = i.lower()
		
		try:
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
				pass
		except ExitLoop:
			pass
	return unit

	

class TDFFrame:
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
	f = open(filename, 'rb')
	tdf_data = f.read().decode("latin_1")
	#tdf_data = f.read().decode("UTF-8", "ignore")
	newlines = "\r\n"
	spaces = "\t "
	frames = []
	line = 1
	fr = TDFFrame()
	for i in tdf_data:
		if i == '\n':
			line = line + 1
		if i == "/":	# Count slashes for comments.
			fr.slashcount = fr.slashcount + 1
		else:
			if fr.slashcount > 0 and fr.state == 2: # Handle comments on a header line.
				raise Exception("TDF Error: Expecting '{' in " + filename + ":" + str(line))
			fr.slashcount = 0
			
		
		if fr.state == 0:	# Waiting for a section header.
			if i == '[': # Begin section header
				fr.name = []
				fr.state = 1
		elif fr.state == 1: # Reading the header
			if i == ']':
				fr.cursec = ''.join(fr.name)
				fr.sections[fr.cursec] = {}
				fr.state = 2
				continue
			elif i not in newlines:
				fr.name.append(i)
			else:
				raise Exception("TDF Error: newline or carriage return in section header.")
		elif fr.state == 2:	# Waiting for a data section.
			if fr.slashcount == 2:
				fr.state = 4
				fr.restate = 2
			if i in newlines or i in spaces:
				pass
			elif i == "{":
				fr.name = []
				fr.state = 3
			elif i != '/':
				raise Exception("TDF Error: Expecting '{' in " + filename + ":" + str(line))
		elif fr.state == 3:	# Waiting for end of data section or some data.
			if fr.slashcount == 2:
				fr.state = 4
				fr.retstate = 3
			elif i == "}":
				if len(frames):
					parent = frames[-1]
					parent.sections[parent.cursec][fr.cursec] = fr.sections[fr.cursec]
					fr = frames.pop()
				else:
					fr.state = 0
			elif i in newlines:
				fr.name = []
			elif i == "=":
				fr.cname = "".join(fr.name)
				fr.value = []
				fr.state = 5
			elif i == "[":
				frames.append(fr)
				fr = TDFFrame()
				fr.state = 1
			elif i not in spaces:
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

