from io import StringIO
import re
import collections
import copy

def FixNumeric(table):
	# Take numeric values stored as strings and convert them to int or float appropriately.
	table = copy.deepcopy(table)
	for key, value in table.items():
		if type(value) == type(dict()):
			table[key] = FixNumeric(value)
		elif type(value) == type(""):
			if value.isnumeric() and not value.isdecimal():
				table[key] = int(value)
			elif value.isdecimal():
				table[key] = float(value)
	return table

def ConvertUnits(units, weapons, features, sounds):
	# Convert units
	
	def cwep(weapons, index): # Add a weapon index only if it doesn't exist.
		if index not in weapons:
			weapons[index] = dict()

	
	weapons = LowerKeys(copy.deepcopy(weapons))
	features = LowerKeys(copy.deepcopy(features))
	sounds = LowerKeys(copy.deepcopy(sounds))
	units = LowerKeys(copy.deepcopy(units))
	new_units = dict()
	
	#### Load in weapon information.
	# Arrayed variables for weapons include: maindir, maxangledif, badtargetcategory, onlytargetcategory, and slaveto
	# def is a variable which contains the weaponN value which was a string pointing to the weapondef.
	# weapon* is now an array with these variables and the def variable.
	#### Load in sound information.
	# The soundcategory variable references the needed sound information. The full conversion for this has already
	# been done in the ConvertSounds() function. The sound category can then simply be substituted.
	
	weapon_array_re = re.compile("^(onlytargetcategory|maxangledif|maindir|weaponslaveto|weapon|(wpri_|wsec_|wspe_|wter_){0,1}badtargetcategory)([0-9]*)$")
	btg_numap = {"wpri_": 1, "wsec_": 2, "wspe_": 3, "wter_": 3}
	
	########## DEBUG
	#print(sorted(list(sounds.keys())))
	##########
	
	for unitname, unit in units.items():
		new_units[unitname] = dict()
		new_unit = new_units[unitname]
		allweap = dict()
		for var,data in unit.items():
			wepmatch = weapon_array_re.match(var)
			if wepmatch:
				mgroups = list(wepmatch.groups())
				
				if "weapons" not in new_unit:
					new_unit["weapons"] = dict()
				if "badtargetcategory" in mgroups[0]:
					if not mgroups[1]:	# We have an inspecific target category. Assume for all weapons.
						allweap[mgroups[0]] = data
						continue
					widx = btg_numap[mgroups[1]]
					cwep(new_unit["weapons"], widx)
					new_unit["weapons"][widx]["badtargetcategory"] = data
				else:
					if  mgroups[0] == "weaponslaveto":	# This variable gets a rename.
						mgroups[0] = "slaveto"
						
					if len(mgroups[2]) == 0:
						allweap[mgroups[0]] = data
						continue
					widx = int(mgroups[2]) # Badtargetcategory uses ints and we don't want to mix.
					cwep(new_unit["weapons"], widx)
					
					new_unit["weapons"][widx][mgroups[0]] = data
			elif "soundcategory" == var:
				if data.lower() == "none":
					continue
				
				new_unit["sounds"] = sounds[data.lower()]
			else:
				new_unit[var] = data
		for var,data in allweap.items():
			for widx,weap in new_unit["weapons"].items():
				if var not in weap:
					weap[var] = data
	
	return new_units
	
def ConvertFeatures(features):
	bool_types = ['reclaimable', 'blocking']
	
	# Most of my converters are creating a whole new tree, so I figured I'd do the same here.
	# There may be non-copied tables and lists in those other converters, which will need to be fixed.
	features = copy.deepcopy(features)
	# Convert features.
	for fname,featuredef in features.items():
		for key,var in featuredef.items():
			if key.lower() in bool_types:
				featuredef[key] = bool(int(var))
	return features
	
def ConvertWeapons(weapons):
	# Variable lists for conversion. These are constructed from ba938 lua files.
	# Variables not included here are assumed to be strings.
	bool_vars = ["avoidfeature", "tracks", "visibleshieldrepulse", "burnblow", "collideenemy", "waterbounce", "turret", "groundbounce", "waterweapon", "impactonly", "submissile", "noselfdamage", "commandfire", "soundtrigger", "firesubmersed", "collidefriendly", "paralyzer", "avoidfriendly", "avoidground", "stockpile", "smoketrail", "noexplode", "visibleshield", "smartshield", "hardstop", "canattackground", "shieldrepulser"]
	
	# Weapon information comes already with a sub-type. Make sure those are all ints too.
	for weapon_name,weapon in weapons.items():
		new_weapon = dict()
		for key,value in weapon.items():
			lkey = key.lower()
			if lkey in bool_vars:
				new_weapon[key] = bool(int(value))
			elif lkey == "damage":	# The damage table is all integers.
				damage = dict()
				for nkey, nval in value.items():
					try:
						damage[nkey] = int(nval)
						continue
					except (ValueError):
						pass
				
					damage[nkey] = float(nval)
				new_weapon["damage"] = damage;
			else:
				try:
					new_weapon[key] = int(value)
					continue
				except (ValueError):
					pass
				try:
					new_weapon[key] = float(value)
					continue
				except (ValueError):
					pass
				new_weapon[key] = value
		# Add def=weapon_name, because some ba938 units have it and I'm not sure
		# how it's used if it is at all.
		new_weapon['def'] = weapon_name
	return new_weapon

def ConvertSounds(table):
	# Convert sound.tdf information to the new structure. Turn numbered variables
	# into arrays.
	isarray = re.compile("^(.*)([0-9])+$")
	new_table = {}
	for key,value in table.items():
		new_sound = {}
		for sound,svalue in value.items():
			# If the item has numbers after it, assume it's an array. Convert accordingly.
			rer = isarray.match(sound)
			if rer:
				aname = rer.group(1)
				aindex = rer.group(2)
				if aname not in new_sound:
					new_sound[aname] = dict()
				new_sound[aname][aindex] = svalue
			else:
				new_sound[sound] = svalue
		new_table[key] = new_sound
				
	return new_table
	
def FormatLuaVar(var):
	if type(var) == type(""):
		return '"{0}"'.format(var)
	elif type(var) == type(bool()):
		return str(var).lower()
	else:
		return "{0}".format(var)

def _NumericIndices(table):
	for i in table.keys():
		if type(i) == type(""):
			if i.isnumeric() == False:
				return False
	return True
		
		
def MakeLuaCode(table, level=0, file=None, order_nums = True):
	# Make the pretty lua code here.
	# file - the StringIO, this could be removed and we could use the return values instead.
	# level - the indentation level
	# order_nums - order the numeric indices and correct them to be 1-indexed arrays?
	delimiter = "\t"
	clevel = level
	
	var_str = { False: "{0} = {1},\n", True: "[{0}] = {1},\n" }
	table_str = { False: "{0} = {{\n", True: "[{0}] = {{\n" }
	
	if file == None:
		file = StringIO()
	
	is_numeric = _NumericIndices(table)
	# Convert to an ordered dict if it's numeric. We want a dict because our indicies will start  at 1 and not 0.
	# An ordered dict will let us order it numerically and make it pretty. We also need to make arrays start
	# from 1 because that's how they are in the new BA code, even though it would depend on how
	# Spring interprets these arrays whether it matters or not.
	if is_numeric and order_nums:
		old_table = table
		table = collections.OrderedDict()
		keys = sorted(list(old_table.keys()))
		
		ioffset = 0
		if "0" in keys:
			ioffset = 1
		
		for key in keys:
			table[str(int(key)+ioffset)] = old_table[key]
	
	# Write the lua code to a StringIO
	skeys = list(table.keys())
	skeys.sort()
	for key in skeys:
		value = table[key]
		if type(value) == type(dict()):
			file.write("\t"*clevel + table_str[is_numeric].format(key))
			MakeLuaCode(value, clevel+1, file)
			file.write("\t"*clevel + "},\n")
		else:
			file.write("\t"*clevel + var_str[is_numeric].format(key, FormatLuaVar(value)))
			
	return file.getvalue()
	
# Convert all dict keys and sub-dict keys to lowercase.
def LowerKeys(data):
	ndata = dict()
	if type(data) == type(dict()):
		for key,value in data.items():
			if type(value) == type(dict()):
				value = LowerKeys(value)
			if type(key) == type(""):
				ndata[key.lower()] = value
			else:
				ndata[key] = value
	return ndata
	