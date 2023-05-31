all:
	@/bin/echo -n "No default target defined."
	@/bin/echo " Available: check, check_all"

check:
	python3 -m unittest discover --start-directory tests -v

check_all:
	ALLTESTS=1 python3 -m unittest discover --start-directory tests -v

.PHONY: all check check_all docs

docs:
	make -C docs html
