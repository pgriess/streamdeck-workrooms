ROOT_DIR=$(shell dirname $(realpath $(firstword $(MAKEFILE_LIST))))
SD_PLUGIN_DIR="$(HOME)/Library/Application Support/com.elgato.StreamDeck/Plugins"
PLUGIN_DIR=$(SD_PLUGIN_DIR)/in.std.fb.sdPlugin
ASSETS=$(wildcard $(ROOT_DIR)/assets/*.png)
BINARIES=$(wildcard $(ROOT_DIR)/bin/*)
SOURCES=$(shell find $(ROOT_DIR)/streamdeck_workrooms -name '*.py')

.PHONY: install clean

$(ROOT_DIR)/dist/daemon: $(SOURCES)
	$(ROOT_DIR)/env/bin/pyinstaller -Fc \
		-n $$(basename $@) --distpath=$$(dirname $@) \
		./streamdeck_workrooms/daemon.py

install:
	rm -fr $(PLUGIN_DIR)
	mkdir $(PLUGIN_DIR)
	cp manifest.json en.json \
		env/bin/daemon \
		$(ASSETS) \
		$(BINARIES) \
		$(PLUGIN_DIR)

clean:
	rm -fr $(ROOT_DIR)/build $(ROOT_DIR)/dist
