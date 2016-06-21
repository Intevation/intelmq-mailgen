all:
	@/bin/echo -n "No default target defined."
	@/bin/echo " Available: check, check_all"

check:
	cd tests && python3 -m unittest -v

check_all:
	cd tests && ALLTESTS=1 python3 -m unittest -v

.PHONY: all check check_all
