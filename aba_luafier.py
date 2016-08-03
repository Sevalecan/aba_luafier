import os
from pathlib import Path
import re
import lupa
from lupa import LuaRuntime
import argparse
from loaders import LoadLUA,LoadTDF,FixUnitTypes,ExpandTable,LowerKeys
from converter import ConvertUnit, ConvertWeapon, MakeLuaCode
import collections

# Parse arguments
parser = argparse.ArgumentParser()
parser.add_argument("action", choices=["ctypes", "lsubs", "cweap", "convert"], nargs='?')
args = parser.parse_args()

# Set up the paths for our games to be analyzed.
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

# For weapons, badtargetcategory should get moved into the weapondef, as should weaponmaindir and onlytargetcategory

# Load ABA featuredefs. Features usually correspond to units, and the luafied units have feature
# information provided in the unitdef.
for i in (aba_dir / 'features').rglob('*.tdf'):
	feature = LoadTDF(str(i))
	aba_features.update(feature)

print("Features loaded: {0}".format(len(aba_features)))

# Load ABA units. The TDF loader works because FBI files are essentially the same format.
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

# Load ABA weapondefs.
for i in (aba_dir / 'weapons').rglob('*.tdf'):
	weapon = LoadTDF(str(i))
	aba_weapons.update(weapon)

#aba_weapons = LowerKeys(aba_weapons)
print("Weapons loaded {0}".format(len(aba_weapons)))

# Load ABA armor file.
aba_armor = LoadTDF(str((aba_dir / 'armor.txt')))
print("Armors loaded: {0}".format(len(aba_armor)))

# Load BA938 Luafied units.
for i in (ba_dir / 'units').glob('*.lua'):
	# print("Loading {0}".format(str(i.name)))
	unit = LoadLUA(i)
	ba_units.update(unit)

print("BA Units loaded {0}".format(len(ba_units)))

# Extract weapondefs from BA938 for comparison against ABA.
ba_weapons = {}
for key,value in ba_units.items():
	if value.get("weapondefs", None) != None:
		ba_weapons.update(value['weapondefs'])

print("{0} BA Weapons found.".format(len(ba_weapons)))
	

# Deal with the action now that we've loaded data.
print()
if args.action == "ctypes":
	print("Comparing variable types")
	ba_vlist = set()
	aba_vlist = set()
	
	# Get a list of variables from every unit in BA and ABA. Make sure these
	# are lowercase.
	for i in ba_units.values():
		for j,k in i.items():
			if type(k) != type({}):
				ba_vlist.add(j.lower())
				
	for h,i in aba_units.items():
		for j,k in i.items():
			if type(k) != type({}):
				aba_vlist.add(j.lower())
				
	# Get a list from the difference of each set. This tells us which
	# variables each 'game' has that the other doesn't.
	ba_uniq = list(ba_vlist.difference(aba_vlist))
	aba_uniq = list(aba_vlist.difference(ba_vlist))
	
	# Are useless variables used in aba? This set will tell.
	useless_aba = aba_vlist & useless_set
	
	# Use all values from the aba and ba unique variables and find the longest name in that set.
	# Add 2 for the column width so that there's some clear spacing for each column.
	col_width = max([len(word) for word in ba_uniq] + [len(word) for word in aba_uniq])+2

	ba_uniq.sort()
	aba_uniq.sort()
	rows = max(len(ba_uniq), len(aba_uniq))
	
	# Print the columns for the unique variables in each mod.
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
	
elif args.action == "cweap":
	baw_set = set(ba_weapons.keys())
	abaw_set = set(aba_weapons.keys())
	
	nset = baw_set & abaw_set
	dset = abaw_set - nset
	print(dset)	# Print the weapons that ABA has that BA does not.
	
	# Let's find the weapons used in ABA
	wexp = re.compile("^weapon[0-9]+$")
	aba_used_weapons = []
	for unit in aba_units.values():
		for var,data in unit.items():
			if wexp.match(var):
				aba_used_weapons.append(data.lower())
	# Let's make it a set and compare it with baw_set.
	aba_used_wset = set(aba_used_weapons)
	aba_ba_weapons = aba_used_wset & baw_set
	
	print()
	print("List weapons used in ABA that come from BA.")
	print(aba_ba_weapons)
	print()
	print("Bool types: [", end="")
	bool_set = set()
	for j in ba_weapons.values():
		for key,i in j.items():
			if type(i) == type(bool()):
				bool_set.add(key.lower())
	for i in bool_set:
		print("\"{0}\", ".format(i), end="")
	print("]")
	
	int_set = set()
	for j in ba_weapons.values():
		for key,value in j.items():
			if type(value) == type(int()):
				int_set.add(key.lower())
	print("\n\n\n")
	print("int types: [", end="")
	for i in int_set:
		print("\"{0}\", ".format(i), end="")
	print("]")
	
	float_set = set()
	for j in ba_weapons.values():
		for key,value in j.items():
			if type(value) == type(float()):
				float_set.add(key.lower())
	print("\n\n\n")
	print("float types: [", end="")
	for i in float_set:
		print("\"{0}\", ".format(i), end="")
	print("]")
elif args.action == "convert":
	output_path = Path("../aba165/units")
	new_weapons = dict()
	
	# First convert the weaponsdefs. We need these for the units.
	for key,value in aba_weapons.items():
		new_weapons[key] = ConvertWeapon(value)
		new_weapons[key]["def"] = key
	
