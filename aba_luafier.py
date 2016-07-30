import os
from pathlib import Path
import re
import lupa
from lupa import LuaRuntime

## Code for finding items in a path object.
#pp = Path(config['badir'])	
#	if "units" in [x.name.lower() for x in pp.iterdir()]:
#		print("Found units dir!")

# Possibly make it iterative by using index chains.
#def ExpandLTable(table):
#	try:
#		table = dict(table)
#		for key, value in table.items():
#			try:
#				table[key] = ExpandLTable(value)
#			except (ValueError, TypeError):
#				pass
#	
#	except (ValueError, TypeError):
#		pass
#	return table
	
# Converts a Lua table to nested dicts.
def ExpandTable(table):
	indices = []
	try:
		table = dict(table)
		indices = [(table, x) for x in table.keys()]
		
		while len(indices) > 0:
			tb,key = indices.pop()
			try:
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


errortypes = {}
def LoadFBI(filename):
	fbif = open(filename, 'r')
	fbi_data = {}
	strfields = ["category", "buildpic", "buildinggrounddecaltype", "collisionvolumeoffsets", "collisionvolumescales", "collisionvolumetype", "corpse", "description", "explodeas", "icontype", "name", "objectname", "selfdestructas", "yardmap", "side", "name", "badtargetcategory", "copyright", "defaultmissiontype", "nochasecategory", "selfdestructas", "unitname", re.compile("w[a-z]{3}_badtargetcategory", re.I), re.compile("weapon[0-9]+", re.I), re.compile("weaponmaindir[0-9]+", re.I), re.compile("onlytargetcategory[0-9]*", re.I), re.compile("badtargetcategory[0-9]+", re.I), re.compile("explosiongenerator[0-9]+", re.I), "soundcategory", "designation", "tedclass", "movementclass", "tracktype", "flankingbonusdir", "script"]
	boolfields = ["usebuildinggrounddecal", "builder", "canmove"]
	loadfields = ["soundcategory"]
	
	for i in fbif.readlines():
		i = i.strip();
		if i[0:2] == "//":
			continue
		j = i.split("=", 1)
		retype = type(re.compile(""))
		
		if i[0:2] == "//":
			continue
		
		if len(j) > 1:
			j[0] = j[0].lower().strip()
			j[1] = j[1].split('//')[0].strip().rstrip(';')
			
			try:
				for k in strfields:
					if type(k) == type("") and j[0] == k:
						fbi_data[j[0]] = str(j[1])
						raise ExitLoop
					elif type(k) == retype:
						if k.match(j[0]):
							fbi_data[j[0]] = str(j[1])
							raise ExitLoop
				for k in boolfields:
					if j[0] == k:
						fbi_data[j[0]] = bool(j[1])
						raise ExitLoop
				try:
					fbi_data[j[0]] = int(j[1])
				except ValueError as e:
					try:
						fbi_data[j[0]] = float(j[1])
					except ValueError as f:
						global errortypes
						if j[0] not in errortypes:
							errortypes[j[0]] = j[1]
					
			except ExitLoop:
				pass
		
	
	return fbi_data

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
	
def LoadTDF(filename):
	f = open(filename, 'rb')
	tdf_data = f.read().decode("utf-8")
	newlines = ['\r', '\n']
	spaces = ['\t', ' ']
	frames = []
	fr = TDFFrame()
	for i in tdf_data:
		if i == "/":	# Count slashes for comments.
			fr.slashcount = fr.slashcount + 1
		else:
			fr.slashcount = 0
		
		if fr.state == 0:	# Waiting for a section header.
			if i == '[': # Begin section header
				fr.name = []
				fr.state = 1
		elif fr.state == 1:
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
			else:
				raise Exception("TDF Error: Expecting '{'")
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



ba_dir = Path("../ba938")
aba_dir = Path(".")

aba_udir = aba_dir / 'units'
aba_units = []
for i in aba_udir.glob('*.fbi'):
	if i.is_file():
		aba_units.append(LoadFBI(str(i.absolute())))

#for i in aba_units:
#	print("{0}".format(i['name']))

aba_w = aba_dir / 'weapons' / 'weapons.tdf'

aba_weapon = LoadTDF(str(aba_w.absolute()))
weapkey = sorted(list(aba_weapon.keys()))[0]

print("Weapon: {0}".format(weapkey))
for i in sorted(aba_weapon[weapkey].keys()):
	print(" \"{0}\": {1}".format(i, aba_weapon[weapkey][i]))

for key,value in errortypes.items():
	print("Error in '{0}' = '{1}'".format(key, value))