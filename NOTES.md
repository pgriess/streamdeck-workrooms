The Elgato SDK is documented [here](https://developer.elgato.com/documentation/stream-deck/sdk/overview/).

Their HTML apps can't shell out, probably want to run something else.  Unfortunately other native samples are all C++ or ObjC. The flow looks possible to re-implement -- it's just passing some metadata to an executable which is then used to set up a WebSockets connection.

Use Python to re-implement this? The 'websockets' module looks fine.

Distribution via py2app if desired.

Talking to Chrome can be done using AppleScript; see `query_mute_state.osa`. Either shell out to this or possibly use OSAKit via pyobjc-framework-OSAKit?

Get callbacks from Chrome by registering an attribute MutationObserver on the mute button that fires an XHP request to an HTTP server in the Python process. Do this to avoid polling for state changes.

# 6/10

* Mute / un-mute works

* `query_mute_state` / `toggle_mute_state` work, but are hacky garbage

* Logging goes to ~/.streamdeck.log

* There's no way to represent the UNKNOWN state. If we stick with manifest-defined states (max 2), we'll have to use text to indicate this. Probably another argument in favor of dropping states alltogether.
