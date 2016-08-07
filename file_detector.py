from pathlib import Path
import re

# Find all the files that Advanced BA Overlays over BA 7.20
# and then determine if they're different.(which they probably are)
# Make sure to skip unit files as they're expected. We want to find
# Other types of files that might've been changed and need to be upgraded.

ba_dir = Path("../ba720")
aba_dir = Path("../advanced_ba_v1.64_ba720")

# It's basically implied that we need these excluded folders, so don't complicate the comparison. Lots of files here.
# gamedata/explosions needed as well, still present in 938.
skipre = re.compile("^(objects3d|unitpics|unittextures|units|sounds|bitmaps|scripts)", re.I)

aba_files = [str(x.relative_to(aba_dir)).lower() for x in aba_dir.rglob("*") if not x.is_dir()]
aba_nonunit = [x for x in aba_files if not skipre.match(x)]

ba_files = [str(x.relative_to(ba_dir)).lower() for x in ba_dir.rglob("*") if not x.is_dir()]
ba_nonunit = [x for x in ba_files if not skipre.match(x)]

print("Overwritten files: ")
for x in aba_nonunit:
	if x in ba_nonunit:
		print("  " + str(x))

print()
print("ABA only files:")
for x in aba_nonunit:
	if x not in ba_nonunit:
		print("  " + str(x))
