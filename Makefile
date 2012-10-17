.PHONY: all install uninstall clean

PYTHON := python
BOOTSTRAP := MaggotDict.pretzel.bootstrap
INSTALL := $(DESTDIR)/usr/bin/maggot-dict-cli

all: maggot-dict-cli

maggot-dict-cli: maggot-dict-cli.py MaggotDict
	@$(PYTHON) -m$(BOOTSTRAP) -m$< MaggotDict > $@
	@chmod 775 $@

install: clean all
	@install -m775 maggot-dict-cli $(INSTALL)

uninstall:
	@test -f $(INSTALL) && rm $(INSTALL)

clean:
	@test -f maggot-dict-cli && rm maggot-dict-cli

# vim: nu ft=make columns=120 :
