from io import StringIO

def ConvertUnit(unit, weapons, features, sounds):
	# Convert a unit.
	pass
	
	
def ConvertWeapon(weapon):
	# Variable lists for conversion. These are constructed from ba938 lua files.
	# Variables not included here are assumed to be strings.
	bool_vars = ["avoidfeature", "tracks", "visibleshieldrepulse", "burnblow", "collideenemy", "waterbounce", "turret", "groundbounce", "waterweapon", "impactonly", "submissile", "noselfdamage", "commandfire", "soundtrigger", "firesubmersed", "collidefriendly", "paralyzer", "avoidfriendly", "avoidground", "stockpile", "smoketrail", "noexplode", "visibleshield", "smartshield", "hardstop", "canattackground", "shieldrepulser"]
	
	# int_vars = ["collidefriendly", "edgeeffectiveness", "shieldpowerregen", "coverage", "soundhitvolume", "visibleshieldhitframes", "shieldradius", "impactonly", "sprayangle", "metalpershot", "tolerance", "thickness", "heightboostfactor", "wobble", "turret", "corethickness", "shieldenergyuse", "turnrate", "burst", "impulsefactor", "weaponacceleration", "laserflaresize", "duration", "interceptedbyshieldtype", "intensity", "shieldstartingpower", "targetable", "firestarter", "areaofeffect", "craterboost", "numbounce", "targetborder", "hightrajectory", "shieldforce", "flighttime", "shieldpower", "reloadtime", "weapontimer", "accuracy", "predictboost", "range", "proximitypriority", "beamttl", "movingaccuracy", "soundstartvolume", "shieldintercepttype", "acceleration", "trajectoryheight", "stages", "impulseboost", "smoketrail", "cratermult", "bouncerebound", "cylindertargeting", "size", "soundtrigger", "craterareaofeffect", "dance", "paralyzetime", "leadbonus", "stockpiletime", "shieldmaxspeed", "energypershot", "interceptor", "projectiles", "startvelocity", "weaponvelocity" ]
	
	# float_vars = ["targetmoveerror", "bounceslip", "camerashake", "shieldpowerregenenergy", "thickness", "minintensity", "heightboostfactor", "soundstartvolume", "intensity", "separation", "soundhitwetvolume", "alphadecay", "size", "corethickness", "impulseboost", "weaponacceleration", "craterboost", "duration", "beamtime", "impulsefactor", "predictboost", "flamegfxtime", "proximitypriority", "sizegrowth", "weapontimer", "burstrate", "soundhitvolume", "weaponvelocity", "edgeeffectiveness", "flighttime", "trajectoryheight", "reloadtime", "shieldalpha", "cratermult", "bouncerebound", "mygravity"]
	
	new_weapon = dict()
	# Weapon information comes already with a sub-type. Make sure those are all ints too.
	
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
	
	return new_weapon

def ConvertSound(table):
	pass
	
def FormatLuaVar(var):
	if type(var) == type(""):
		return '"{0}"'.format(var)
	elif type(var) == type(bool()):
		return str(var).lower()
	else:
		return "{0}".format(var)
	
def MakeLuaCode(table, level=0, file=None):
	# Make the pretty lua code here.
	delimiter = "\t"
	clevel = level
	
	if file == None:
		file = StringIO()
	
	for key,value in table.items():
		if type(value) == type(dict()):
			file.write("\t"*clevel + "{0} = {{\n".format(key))
			MakeLuaCode(value, clevel+1, file)
			file.write("\t"*clevel + "},\n")
		else:
			file.write("\t"*clevel + "{0} = {1},\n".format(key, FormatLuaVar(value)))
			
	return file.getvalue()