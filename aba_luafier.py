import os
from pathlib import Path
import re
import lupa
from lupa import LuaRuntime
import argparse
from loaders import LoadLUA,LoadTDF,FixUnitTypes,ExpandTable

# Parse arguments
parser = argparse.ArgumentParser()
parser.add_argument("action", choices=["ctypes", "lsubs"], nargs='?')

args = parser.parse_args()

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
				
	
