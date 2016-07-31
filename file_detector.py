from pathlib import Path
import re

# Find all the files that Advanced BA Overlays over BA 7.20
# and then determine if they're different.(which they probably are)
# Make sure to skip unit files as they're expected. We want to find
# Other types of files that might've been changed and need to be upgraded.

ba_dir = Path("../ba720")
aba_dir = Path("../advanced_ba_v1.64_ba720")

skipre = re.compile("^(objects3d|unitpics|unittextures|units|sounds|bitmaps)", re.I)

aba_files = [str(x.relative_to(aba_dir)).lower() for x in aba_dir.rglob("*") if not x.is_dir()]
aba_nonunit = [x for x in aba_files if not skipre.match(x)]

ba_files = [str(x.relative_to(ba_dir)).lower() for x in ba_dir.rglob("*") if not x.is_dir()]
ba_nonunit = [x for x in ba_files if not skipre.match(x)]

for x in aba_nonunit:
	if x in ba_nonunit:
		print(x)
