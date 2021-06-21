ROOT_DIR=$(shell dirname $(realpath $(firstword $(MAKEFILE_LIST))))
SD_PLUGIN_DIR="$(HOME)/Library/Application Support/com.elgato.StreamDeck/Plugins"
PLUGIN_DIR=$(SD_PLUGIN_DIR)/in.std.fb.sdPlugin
ASSETS=$(wildcard $(ROOT_DIR)/assets/*.png)

install:
	rm -fr $(PLUGIN_DIR)
	mkdir $(PLUGIN_DIR)
	cp manifest.json en.json \
		env/bin/daemon \
		$(ASSETS) \
		$(PLUGIN_DIR)
