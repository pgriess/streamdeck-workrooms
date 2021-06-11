SD_PLUGIN_DIR="$(HOME)/Library/Application Support/com.elgato.StreamDeck/Plugins"
PLUGIN_DIR=$(SD_PLUGIN_DIR)/in.std.fb.sdPlugin

install:
	rm -fr $(PLUGIN_DIR)
	mkdir $(PLUGIN_DIR)
	cp manifest.json en.json \
		env/bin/daemon \
		active.png muted.png \
		category.png "category@2x.png" \
		plugin.png "plugin@2x.png" \
		$(PLUGIN_DIR)
