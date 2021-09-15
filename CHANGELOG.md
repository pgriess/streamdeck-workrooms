# 2.0.1
- Fix issue with the "call" button in some pre-call screens

# 2.0
- Add new action to connect or disconnect from a workroom
- Slight visual tweaks to icons
- Collect anonymized analytics on usage, errors, and performance

# 1.0.2
- Don't start Chrome if it's not already running
- Fix bug where a user screen sharing could confuse the query system
- Detect the post-call survey (star rating) which used to cause an E2 and now
  shows all actions as disabled since there is no active call

# 1.0.1
- Fix bug with action being stored in a folder that can cause the plugin state
  to become unsynchronized from the Stream Deck
- Add heuristic to detect end-of-call scenario and display NONE buttons rather
  than "E2", indicating that the plugin couldn't understand the webpage

# 1.0
- Expose error codes through action titles; use openUrl action to open relevant
  wiki page when invoking action
- Re-theme icons to better match Workplace Rooms

# 0.2
- Handle calls where there is no hand button to not display an error
- Use openUrl action to open help wiki in unexpected states
- Better matching of button identifiers and values via regexes

# 0.1.1
- Use URLs to identify call tabs rather than title
- Handle subprocess invocation failure more gracefully rather than requiring a
  restart of the entire process

# 0.1
- Initial release
