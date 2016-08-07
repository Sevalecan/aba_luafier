import os
from pathlib import Path
import re
import lupa
from lupa import LuaRuntime
import argparse
from loaders import LoadLua, LoadTDF, FixUnitTypes, ExpandTable
from converter import ConvertUnits, ConvertWeapons, MakeLuaCode, ConvertSounds, LowerKeys, ConvertFeatures, ConvertSideData, FormatDict
import collections

# Parse arguments
parser = argparse.ArgumentParser()
parser.add_argument("action", choices=["ctypes", "lsubs", "cweap", "convert_units", "cfeat", "list_sfx", "convert_armor", "test_armor"], nargs='?')
args = parser.parse_args()

# Set up the paths for our games to be analyzed.
ba_dir = Path("../ba938")
aba_dir = Path(".")
ba7_dir = Path("../ba720")
aba_new_dir = Path("../aba165")

aba_features = {}
aba_weapons = {}
aba_units = {}
ba_armor = {}
aba_armor = {}

ba_units = {}


# For weapons, badtargetcategory should get moved into the weapondef, as should weaponmaindir and onlytargetcategory

# Load ABA featuredefs. Features usually correspond to units, and the luafied units have feature
# information provided in the unitdef.
for i in (aba_dir / 'features').rglob('*.tdf'):
	feature = LoadTDF(str(i))
	aba_features.update(feature)

print("Features loaded: {0}".format(len(aba_features)))

ba7_features = dict()
for i in (ba7_dir / 'features').rglob('*.tdf'):
	feature = LoadTDF(str(i))
	ba7_features.update(feature)

ba7_features.update(aba_features)
aba_features = ba7_features

print("Features loaded: {0}".format(len(aba_features)))

# Load ABA units. The TDF loader works because FBI files are essentially the same format.
for i in (aba_dir / 'units').rglob('*.fbi'):
	unit = LoadTDF(str(i))
	unit = unit['UNITINFO']
	unit_name = ""
	FixUnitTypes(unit)
	for j,k in unit.items():
		if j.lower() == "unitname":
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

# Load ABA sidedata file.
aba_sidedata = LoadTDF(str((aba_dir / 'gamedata' / 'sidedata.tdf')))

# Load ABA sounds.
aba_sounds = LoadTDF(str((aba_dir / 'gamedata' / 'sound.tdf')))
print("Sounds loaded: {0}".format(len(aba_sounds)))

aba_armor = LoadTDF(str(aba_dir / 'armor.txt'))
print("Armor categories loaded: {0}".format(len(aba_armor)))

####### Some sound categories are missing from the advanced BA sound.tdf. Get them from BA 7.20
ba7_sounds = LoadTDF(str((ba7_dir / 'gamedata' / 'sound.tdf')))
ba7_sounds.update(aba_sounds)
aba_sounds = ba7_sounds

# Load BA938 Luafied units.
for i in (ba_dir / 'units').glob('*.lua'):
	# print("Loading {0}".format(str(i.name)))
	unit = LoadLua(i)
	ba_units.update(unit)

print("BA Units loaded {0}".format(len(ba_units)))

# Extract weapondefs from BA938 for comparison against ABA.
ba_weapons = {}
for key,value in ba_units.items():
	if value.get("weapondefs", None) != None:
		ba_weapons.update(value['weapondefs'])

print("{0} BA Weapons found.".format(len(ba_weapons)))

# Extract featuredefs from BA938 for comparison against ABA.
ba_features = {} # This doesn't really work since they named everything to 'dead' and 'heap'
for key,value in ba_units.items():
	if value.get("featuredefs", None) != None:
		ba_features.update(value['featuredefs'])

print("{0} BA Features found.".format(len(ba_features)))
	
# Load armordefs
ba_armor = LoadLua(str(ba_dir / 'gamedata' / 'armordefs.lua'))
print("{0} BA armor categories".format(len(ba_armor)))


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
	# Compare weapon information between the two mods.
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
	
	# We're going to find all the bool types, because those are the ones that are integers in
	# the original TDF files. We want them as bools when they get to lua... Probably.
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
	
	# Find the information placed in weapons section of BA units.
	ba_weaponvars = set()
	ba_weaponvars2 = list()
	
	for name, unit in ba_units.items():
		for varname, data in unit.items():
			if varname.lower() == "weapons":
				for h,i in data.items():
					for j,k in i.items():
						if j.lower() not in ba_weaponvars:
							ba_weaponvars2.append((j.lower(), type(k)));
						ba_weaponvars.add(j.lower())
	print("\n\n Weapon variables used: {0}".format(ba_weaponvars2))
	
elif args.action == "cfeat":
	feature_bool = set()
	for name,feature in ba_features.items():
		for j,k in feature.items():
			if type(k) == type(bool()):
				feature_bool.add(j)
				
	print("Bool types from features: {0}".format(feature_bool))
	
	pass
elif args.action == "convert_units":
	output_path = Path("../aba165/units")
	new_weapons = dict()
	
	# First convert the weaponsdefs. We need these for the units.
	new_weapons  = LowerKeys(ConvertWeapons(aba_weapons))
	new_sounds   = LowerKeys(ConvertSounds(aba_sounds))
	new_features = LowerKeys(ConvertFeatures(aba_features))
	new_sidedata = LowerKeys(ConvertSideData(aba_sidedata))
	
	# Looks like someone didn't test the sound categories very well. Let's try filling in the blanks.
	new_sounds["cor_com"]      = new_sounds["core_com"]
	new_sounds["none"]         = dict() # No, literally. Filling in the blanks.
	new_sounds["chopper"]      = new_sounds["cor_advtol"]
	new_sounds["core_fusion"]  = new_sounds["core_fus"]
	new_sounds["core_cseapln"] = new_sounds["cor_cseapln"]
	new_sounds["arm_tech_lab"] = new_sounds["core_gantry"]
	
	new_units = LowerKeys(ConvertUnits(aba_units, new_weapons, new_features, new_sounds, new_sidedata))
	
	# Output the units here.
	
	aba_new_udir = aba_new_dir / 'units'
	
	for unit,data in new_units.items():
		utable = {unit: data}
		ofile_name = str(aba_new_udir / (unit + '.lua'))
		ofile = open(ofile_name, "w", encoding="utf-8")
		ofile.write("return {\n")
		MakeLuaCode(utable, 1, ofile)
		ofile.write("}\n")
		ofile.close()
elif args.action == "convert_armor":
	aba_armor = LowerKeys(aba_armor)
	
	new_armor = dict()
	for category,info in aba_armor.items():
		if category not in ba_armor:
			new_armor[category] = []
			for index,value in info.items():
				new_armor[category].append(index)
		else:
			ba_cat = ba_armor[category].values()
			for index,value in info.items():
				if index not in ba_cat:
					if category not in new_armor:
						new_armor[category] = []
					new_armor[category].append(index)
	

	aba_new_armor = aba_new_dir / 'newarmor.lua'
	ofile_name = str(aba_new_armor)
	ofile = open(ofile_name, "w", encoding="utf-8")
	ofile.write("aba_armorDefs = {\n")
	MakeLuaCode(new_armor, 1, ofile)
	ofile.write("}")
	ofile.close()
elif args.action == "test_armor":
	aba_armordef = aba_new_dir / 'gamedata' / 'armordefs.lua'
	new_armor = LoadLua(aba_armordef)
	aba_armor = LowerKeys(aba_armor)
	
	for cat, table in aba_armor.items():
		if cat not in new_armor:
			print("Missing category {0} from armordefs.lua in ABA.".format(cat))
		else:
			new_armor_cat = list(new_armor[cat].values())
			for unit in table.keys():
				if unit not in new_armor_cat:
					print("Missing unit {0} from category {1} in armordefs.lua from ABA.".format(unit, cat))
					
	for cat, table in ba_armor.items():
		if cat not in new_armor:
			print("Missing category {0} from armordefs.lua in BA.".format(cat))
		else:
			new_armor_cat = list(new_armor[cat].values())
			for unit in table.values():
				if unit not in new_armor_cat:
					print("Missing unit {0} from category {1} in armordefs.lua from BA.".format(unit, cat))
					
			
	pass
elif args.action == "list_sfx":
	sfx_set = set()
	for key,value in ba_units.items():
		if "sfxtypes" in value:
			for i in value['sfxtypes'].keys():
				sfx_set.add(i)
	print("sfxtypes keys: {0}".format(sfx_set))
elif args.action == "merge_movedefs":
	# Apparently we already merged these... But I don't remember doing it, so I'm going to do it again.
	pass