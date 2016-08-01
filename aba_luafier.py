import os
from pathlib import Path
import re
import lupa
from lupa import LuaRuntime
import argparse

# Parse arguments
parser = argparse.ArgumentParser()
parser.add_argument("action", choices=["ctypes", "lsubs"], nargs='?')

args = parser.parse_args()

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



ba_dir = Path("../ba938")
aba_dir = Path(".")

aba_features = {}
aba_weapons = {}
aba_units = {}

ba_units = {}

# Usless tags mentioned here: https://github.com/ZeroK-RTS/SpringRTS-Tools/blob/41e0673f11ca5e90e354664cbab29fa7c40b609c/SpringModEdit/Procedures/removeUselessTags.lua
# Some defaults listed in rts/Sim/Units/UnitDef.cpp for spring. URL: https://goo.gl/G4zUyE
# This can help us get rid of variables that are sensibly defaulted in Spring.
useless_tags = ["maneuverleashlength",
	"bmcode",
	"canreclamate",
	"scale",
	"steeringmode",
	"tedclass",
	"designation",
"defaultmissiontype"]
useless_set = set(useless_tags)


for i in (aba_dir / 'features').rglob('*.tdf'):
	feature = LoadTDF(str(i))
	aba_features.update(feature)

print("Features loaded: {0}".format(len(aba_features)))

for i in (aba_dir / 'units').rglob('*.fbi'):
	unit = LoadTDF(str(i))
	unit = unit['UNITINFO']
	unit_name = ""
	FixUnitTypes(unit)
	for j,k in unit.items():
		if j.lower() == "name":
			unit_name = k
	aba_units.update({unit_name: unit})

print("Units loaded {0}".format(len(aba_units)))

for i in (aba_dir / 'weapons').rglob('*.tdf'):
	weapon = LoadTDF(str(i))
	aba_weapons.update(weapon)

print("Weapons loaded {0}".format(len(aba_weapons)))

aba_armor = LoadTDF(str((aba_dir / 'armor.txt')))

print("Armors loaded: {0}".format(len(aba_armor)))

for i in (ba_dir / 'units').glob('*.lua'):
	# print("Loading {0}".format(str(i.name)))
	unit = LoadLUA(i)
	ba_units.update(unit)

print("BA Units loaded {0}".format(len(ba_units)))

# Deal with the action now that we've loaded data.
print()
if args.action == "ctypes":
	print("Comparing variable types")
	ba_vlist = set()
	aba_vlist = set()
	for i in ba_units.values():
		for j,k in i.items():
			if type(k) != type({}):
				ba_vlist.add(j.lower())
	for h,i in aba_units.items():
		for j,k in i.items():
			if type(k) != type({}):
				aba_vlist.add(j.lower())
				
	ba_uniq = list(ba_vlist.difference(aba_vlist))
	aba_uniq = list(aba_vlist.difference(ba_vlist))
	
	useless_aba = aba_vlist & useless_set
	
	col_width = max([len(word) for word in ba_uniq] + [len(word) for word in aba_uniq])+2

	ba_uniq.sort()
	aba_uniq.sort()
	rows = max(len(ba_uniq), len(aba_uniq))
	print("BA".ljust(col_width) + "ABA".ljust(col_width))
	for i in range(0,rows):
		ba_text = ""
		aba_text = ""
		try:
			ba_text = ba_uniq[i]
		except IndexError:
			pass
		try:
			aba_text = aba_uniq[i]
		except IndexError:
			pass
		print(ba_text.ljust(col_width) + aba_text.ljust(col_width))
		
	print(useless_aba)
elif args.action == "lsubs":
	subdir_list = set([])
	print("Listing sub-dict names found in all lua units.")
	# Basically anything that expands into a sub dictionary in a unit is in the old format
	# a reference to other information such as weapons and sounds. This will tell us all
	# of the external reference information types that we need to combine into the unit file.
	for h,i in ba_units.items():
		for j,k in i.items():
			if type(k) == type({}):
				#if j.lower() not in subdir_list:
					#print()
					#print("{0} in {1}:    {2}".format(j, h, k))
				subdir_list.add(j.lower())
	print("Subdicts in BA: {0}".format(subdir_list))
				
	
