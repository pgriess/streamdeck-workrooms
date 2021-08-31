PLUGIN_ID=in.std.streamdeck.workplace

ROOT_DIR=$(shell dirname $(realpath $(firstword $(MAKEFILE_LIST))))
BUILD_DIR=$(ROOT_DIR)/build
DIST_DIR=$(ROOT_DIR)/dist

PLUGIN_DIR=$(BUILD_DIR)/$(PLUGIN_ID).sdPlugin
PLUGIN_FILE=$(DIST_DIR)/$(PLUGIN_ID).streamDeckPlugin

ASSETS=$(wildcard $(ROOT_DIR)/assets/*.png)
BINARIES=$(wildcard $(ROOT_DIR)/bin/*)

SOURCES = daemon.py
SOURCES += $(shell find $(ROOT_DIR)/streamdeck_workrooms -name '*.py')

.PHONY: clean install plugin

$(PLUGIN_FILE): $(DIST_DIR)/daemon $(ASSETS) $(BINARIES) $(ROOT_DIR)/manifest.json
	mkdir -p $(PLUGIN_DIR)
	cp -f $^ $(PLUGIN_DIR)
	rm -f $@
	$(ROOT_DIR)/tools/DistributionTool -b -i $(PLUGIN_DIR) -o $$(dirname $@)

$(DIST_DIR)/daemon: $(SOURCES)
	mkdir -p $$(dirname $@)
	$(ROOT_DIR)/env/bin/pyinstaller -Fc \
		--collect-submodules=websockets \
		-n $$(basename $@) --distpath=$$(dirname $@) \
		$(ROOT_DIR)/daemon.py

# Sometimes osascript fails with "Stream got an error: User cancelled"; ignore
# this with the '|| true' clause
install: $(PLUGIN_FILE)
	osascript -e 'tell application "Stream Deck" to quit' || true
	sleep 3
	rm -fr "$${HOME}/Library/Application Support/com.elgato.StreamDeck/Plugins/$(PLUGIN_ID).sdPlugin"
	open $(PLUGIN_FILE)

clean:
	rm -fr $(BUILD_DIR) $(DIST_DIR)

plugin: $(PLUGIN_FILE)
	echo -e '***** NEW PLUGIN BUILT *****\n$(PLUGIN_FILE)'
