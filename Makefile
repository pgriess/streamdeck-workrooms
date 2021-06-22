PLUGIN_ID=in.std.streamdeck.workrooms

ROOT_DIR=$(shell dirname $(realpath $(firstword $(MAKEFILE_LIST))))
BUILD_DIR=$(ROOT_DIR)/build
DIST_DIR=$(ROOT_DIR)/dist

PLUGIN_DIR=$(BUILD_DIR)/$(PLUGIN_ID).sdPlugin
PLUGIN_FILE=$(DIST_DIR)/$(PLUGIN_ID).streamDeckPlugin

ASSETS=$(wildcard $(ROOT_DIR)/assets/*.png)
BINARIES=$(wildcard $(ROOT_DIR)/bin/*)
SOURCES=$(shell find $(ROOT_DIR)/streamdeck_workrooms -name '*.py')

.PHONY: clean

$(PLUGIN_FILE): $(DIST_DIR)/daemon $(ASSETS) $(BINARIES) $(ROOT_DIR)/manifest.json $(ROOT_DIR)/en.json
	mkdir -p $(PLUGIN_DIR)
	cp -f $^ $(PLUGIN_DIR)
	rm -f $@
	$(ROOT_DIR)/tools/DistributionTool -b -i $(PLUGIN_DIR) -o $$(dirname $@)

$(DIST_DIR)/daemon: $(SOURCES)
	mkdir -p $$(dirname $@)
	$(ROOT_DIR)/env/bin/pyinstaller -Fc \
		--collect-submodules=websockets \
		-n $$(basename $@) --distpath=$$(dirname $@) \
		./streamdeck_workrooms/daemon.py

clean:
	rm -fr $(BUILD_DIR) $(DIST_DIR)
