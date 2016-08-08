from io import StringIO
import re
import collections
import copy

# So apparently python people don't like type checking in python, and instead want you to just try a function
# and catch an exception if it's not available in that class. That makes sense for a form of polymorphism,
# but in this case, there are 3 different basic types stored in each dict that gets passed to the conversion
# functions. None of these are compatible and I don't want to treat them like one object. I fail to see how
# "Duck typing" applies here, and I think it's another one of those over-generalized and over-enforced
# guidelines.

class FormatDict(dict):
	def __init__(self, *args, display_num=True):
		super().__init__(args)
		self.display_num = display_num
		pass

def FixNumeric(table):
	# Take numeric values stored as strings and convert them to int or float appropriately.
	table = copy.deepcopy(table)
	for key, value in table.items():
		if type(value) is dict:
			table[key] = FixNumeric(value)
		elif type(value) is str:
			if value.isnumeric() and not value.isdecimal():
				table[key] = int(value)
			elif value.isdecimal():
				table[key] = float(value)
	return table

def ConvertSideData(side_data):
	side_data = copy.deepcopy(side_data)
	can_build = side_data["CANBUILD"]
	new_build = dict()
	side_data["CANBUILD"] = new_build
	
	cb_re = re.compile("^canbuild([0-9]+)$")
	
	for unit,data in can_build.items():
		new_build[unit] = dict()
		for key,build in data.items():
			match = cb_re.match(key)
			if not match:
				raise Exception("Invalid buildopption")
			new_build[unit][match.group(1)] = build.lower()
			
	return side_data

def ConvertUnits(units, weapons, features, sounds, sidedata):
	# Convert units	
		
	# Usless tags mentioned here: https://github.com/ZeroK-RTS/SpringRTS-Tools/blob/41e0673f11ca5e90e354664cbab29fa7c40b609c/SpringModEdit/Procedures/removeUselessTags.lua
	# Some defaults listed in rts/Sim/Units/UnitDef.cpp for spring. URL: https://goo.gl/G4zUyE
	# This can help us get rid of variables that are sensibly defaulted in Spring.
	useless_tags = ["maneuverleashlength", 	"bmcode",
					"canreclamate",			"scale",
				    "steeringmode",			"tedclass",
					"designation",			"defaultmissiontype"]
	useless_set = set(useless_tags)
	
	def cwep(weapons, index): # Add a weapon index only if it doesn't exist.
		if index not in weapons:
			weapons[index] = dict()

	
	weapons   = LowerKeys(copy.deepcopy(weapons))
	features  = LowerKeys(copy.deepcopy(features))
	sounds    = LowerKeys(copy.deepcopy(sounds))
	units     = LowerKeys(copy.deepcopy(units))
	sidedata  = LowerKeys(copy.deepcopy(sidedata))
	canbuild  = sidedata["canbuild"]
	new_units = dict()
	
	#### Load in weapon information.
	# Arrayed variables for weapons include: maindir, maxangledif, badtargetcategory, onlytargetcategory, and slaveto
	# def is a variable which contains the weaponN value which was a string pointing to the weapondef.
	# weapon* is now an array with these variables and the def variable.
	#### Load in sound information.
	# The soundcategory variable references the needed sound information. The full conversion for this has already
	# been done in the ConvertSounds() function. The sound category can then simply be substituted.
	
	weapon_array_re = re.compile("^(onlytargetcategory|maxangledif|maindir|weaponslaveto|weapon|(wpri_|wsec_|wspe_|wter_){0,1}badtargetcategory)([0-9]*)$")
	explosiongenerator_re = re.compile("^explosiongenerator([0-9]+)$")
	btg_numap = {"wpri_": 1, "wsec_": 2, "wspe_": 3, "wter_": 3}
	
	########## DEBUG
	#print(list(weapons.keys()))
	##########
	
	for unitname, unit in units.items():
		new_units[unitname] = dict()
		new_unit = new_units[unitname]
		allweap = dict()
		weapondef = dict()
		weapon_set = set()
		if unitname in canbuild:
			new_unit["buildoptions"] = canbuild[unitname]
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
					cwep(new_unit["weapons"], widx)	# Create weapon entry only if it doesn't exist.
					new_unit["weapons"][widx]["badtargetcategory"] = data
				else:
					if  mgroups[0] == "weaponslaveto":	# This variable gets a rename.
						mgroups[0] = "slaveto"
					elif mgroups[0] == "weapon":
						weapon_set.add(data.lower())
						
					if len(mgroups[2]) == 0:       # We have an inspecific weapon data. Put it in the allweaps dict
						allweap[mgroups[0]] = data # so it can be applied to all weapons.
						continue
					widx = int(mgroups[2]) # Badtargetcategory uses ints and we don't want to mix.
					cwep(new_unit["weapons"], widx)
					
					if mgroups[0] == "weapon":	# The weapon(0-9) variables have to be renamed to 'def'
						weapon_var_name = "def"
					else:
						weapon_var_name = mgroups[0]
					new_unit["weapons"][widx][weapon_var_name] = data
			elif "soundcategory" == var:
				if data.lower() == "none":
					continue
				
				new_unit["sounds"] = sounds[data.lower()]
			elif "corpse" == var: # Need to loop through corpses, could be multiple stages. Let's play it safe.
				new_unit["corpse"] = data
				next_corpse = data
				if "featuredefs" not in new_unit:
					new_unit["featuredefs"] = {}
				while next_corpse != None:
					cur_corpse = {next_corpse.lower() : features[next_corpse.lower()]}
					corpse_name = next_corpse.lower()
					if "featuredead" in cur_corpse[corpse_name]:
						next_corpse = cur_corpse[corpse_name]["featuredead"]
					else:
						next_corpse = None
					new_unit["featuredefs"].update(cur_corpse)
			elif "sfxtypes" == var:
				sfxtypes = dict()
				new_unit["sfxtypes"] = sfxtypes
				for var0, data0 in data.items():
					expmatch = explosiongenerator_re.match(var0)
					if expmatch:
						if "explosiongenerators" not in sfxtypes:
							sfxtypes["explosiongenerators"] = FormatDict(display_num=False)
						sfxtypes["explosiongenerators"][int(expmatch.group(1))] = data0
			else:
				new_unit[var] = data
		for var,data in allweap.items():
			for widx,weap in new_unit["weapons"].items():
				if var not in weap:
					weap[var] = data
		
		for weapon in weapon_set:
			weapondef[weapon] = weapons[weapon]
		if len(weapon_set) > 0:
			new_unit["weapondefs"] = weapondef
	
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
	
	shield_re = re.compile("^shield(.*)$")
	
	weapons = copy.deepcopy(weapons)
	# Weapon information comes already with a sub-type. Make sure those are all ints too.
	new_weapons = dict()
	for weapon_name,weapon in weapons.items():
		new_weapon = dict()
		for key,value in weapon.items():
			lkey = key.lower()
			
			shield_match = shield_re.match(lkey)
			
			if lkey == "cylindertargetting":
				lkey = "cylindertargeting"
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
			elif lkey == "isshield":	# isShield is now weaponType=Shield
				new_weapon["weapontype"] = "Shield"
			elif lkey == "beamweapon":
				new_weapon["weapontype"] = "BeamLaser"
			elif shield_match:
				if "shield" not in new_weapon:
					new_weapon["shield"] = dict()
				shield_var = shield_match.group(1)
				if shield_var == "badcolor" or shield_var == "goodcolor":
					colors = value.split()
					
					new_weapon["shield"][shield_var] = colors
				else:
					new_weapon["shield"][shield_var] = value
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
		new_weapons[weapon_name] = new_weapon
	return new_weapons

def ConvertSounds(table):
	# Convert sound.tdf information to the new structure. Turn numbered variables
	# into arrays.
	table = copy.deepcopy(table)
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
	if type(var) is str:
		try:
			var = int(var)
			return '{0}'.format(var)
		except ValueError:
			pass
		try:
			var = float(var)
			return '{0}'.format(var)
		except ValueError:
			pass
		return '"{0}"'.format(var.strip('"'))
	elif type(var) is bool:
		return str(var).lower()
	else:
		return "{0}".format(var)

def _NumericIndices(table):
	for i in table.keys():
		if type(i) is str:
			if i.isnumeric() == False:
				return False
	return True
	
# We need to watch out for special characters in a key.
def FormatLuaKey(key):
	if isinstance(key, int):
		return key
		
	special_keys = re.compile("(else|^[0-9]|-|\+)")

	if special_keys.search(key) and not key.isnumeric():
		return '["' + key + '"]'
	return key
		
def MakeLuaCode(table, level=0, file=None, order_nums = True, indent="    ", aligneq=False, index_arrays=True):
	# Make the pretty lua code here.
	# file - the StringIO, this could be removed and we could use the return values instead.
	# level - the indentation level
	# order_nums - order the numeric indices and correct them to be 1-indexed arrays?
	delimiter = "\t"
	clevel = level

	# Ok, let's deal with lists. What if the table is a list? Then we convert it to a FormatDict
	# Since a list doesn't allow another part of the program to specify indicies independently,
	# we just don't print them.
	if isinstance(table, list):
		old_list = table
		table = FormatDict(display_num=False)
		index_arrays = False
		for i in range(0, len(old_list)):
			table[i] = old_list[i]
	
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
		keypairs = [[int(key), key] for key in old_table.keys()]
		keypairs.sort(key=lambda x: x[0])
		
		# Make sure the keys are sequential and starting from 1, otherwise Lua breaks stuff.
		for i in range(0,len(keypairs)):
			keypairs[i][0] = i + 1
		
		ioffset = 0
		if (0,"0") in keypairs:
			ioffset = 1
		
		for key in keypairs:
			table[key[0]] = old_table[key[1]]
	
	# This will allow us to throw the sub-dicts at the end of the file regardless of alphabetical order,
	# just like ba938 appears to do.
	def LuaSort(item):
		if isinstance(table[item], (dict, list)):
			return "b"+item
		else:
			return "a"+item
	# Write the lua code to a StringIO
	
	# Print with integer index format or string index format?
	# -- Always use [[]] quotes for lua strings, it's a pretty safe bet.
	var_str = { False: "{0} = {1},\n", True: "[{0}] = {1},\n" }
	table_str = { False: "{0} = {{\n", True: "[{0}] = {{\n" }
	
	# We want to pad variable names tom align the equal signs. This will only apply to
	# non numerically indexed tables only for the time being. The numerically indexed
	# tables will align themselves according to every 10^n items in the list. Not a big deal.
	
	skeys = list(table.keys())
	if not is_numeric:
		skeys.sort(key=LuaSort)
		column_width = max([len(x) for x in skeys])
		# Do the equal sign alignment.
		if aligneq:
			var_str[False] = "{{0{0}}} = {1},\n".format(": <{0}".format(column_width), "{1}")
			table_str[False] = "{{0{0}}} = {{{{\n".format(": <{0}".format(column_width))
	elif not index_arrays:
		var_str[True] = "{1},\n"
		table_str[True] = "{{\n"

	for key in skeys:
		value = table[key]
		if isinstance(value, (dict, list)):
			file.write(indent*clevel + table_str[is_numeric].format(FormatLuaKey(key)))
			sub_index_arrays = index_arrays
			try:
				sub_index_arrays = value.display_num
			except AttributeError:
				pass
			MakeLuaCode(value, clevel+1, file, index_arrays=sub_index_arrays)
			file.write(indent*clevel + "},\n")
		else:
			file.write(indent*clevel + var_str[is_numeric].format(FormatLuaKey(key), FormatLuaVar(value)))
			
			
	if isinstance(file, StringIO):
		return file.getvalue()
	else:
		return None
	
# Convert all dict keys and sub-dict keys to lowercase.
def LowerKeys(data):
	# This allows us to retain the FormatDict and information for it when lowering keys.
	ndata = type(data)()
	try:
		ndata.display_num = data.display_num
	except AttributeError:
		pass
		
	if isinstance(data, dict):
		for key,value in data.items():
			if isinstance(value, dict):
				value = LowerKeys(value)
			try:
				key = key.lower()
			except AttributeError:
				pass
			ndata[key] = value
	return ndata

def LowerValues(data):
	ndata = dict()
	for key,value in data.items():
		if type(value) is str:
			ndata[key] = value.lower()
		elif type(value) is dict:
			ndata[key] = LowerValues(value)
	return ndata