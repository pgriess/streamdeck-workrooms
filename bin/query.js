// The order of states returned [mic, camera] and the text of the states must
// match the Python code which interprets this. This function returns an array
// of values rather than a single one so that we can avoid issuing multiple
// queries per tick.
() => {
    // Regular expressions to idetify buttons. These must be kept in-sync
    // between toggle.js <=> query.js
    // ***** BEGIN *****
    let micButtonRegex = /^(mute|unmute) microphone$/i;
    let cameraButtonRegex = /^turn (off|on) (video|camera)$/i;
    let handButtonRegex = /^(raise|lower) hand$/i;
    let callButtonRegex = /^(join as )|(join room)|(join workroom)|(end call)/i;
    // ***** END *****

    // Detect post-call screens and short-circuit the rest of the checks.
    // Return the sentinel NONE value so that the daemon can handle this
    // appropriately.
    //
    // There are two variants of this
    //
    //  1. A post-call survey with a bunch of buttons.
    //
    //  2. A splash page indicates that the call is no longer active.
    let ratingButtonRegex = /^very good$/i;
    let svgText = Array.from(document.querySelectorAll("svg"))
        .map((n) => { return n.getAttribute("aria-label") || ""; })
        .filter((t) => { return t.match(ratingButtonRegex); })
        .join("");
    if (svgText !== "") {
        return "NONE";
    }

    let leftButtonRegex = /^you left the room$/i;
    let leftText = Array.from(document.querySelectorAll("div"))
        .filter((n) => { return n.textContent.match(leftButtonRegex); })
        .join("");
    if (leftText !== "") {
        return "NONE";
    }

    let micOff = "Unmute microphone";
    let micOn = "Mute microphone";
    let micOffQuery = Array.from(document.querySelectorAll(`[aria-label="${micOff}"]`));
    let micOnQuery = Array.from(document.querySelectorAll(`[aria-label="${micOn}"]`));
    let micState =
        micOffQuery.length > 0 ? "OFF" :
        micOnQuery.length > 0 ? "ON" :
        "UNKNOWN";

    let cameraOff = "Turn on video";
    let cameraOn = "Turn off video";
    let cameraOffQuery = Array.from(document.querySelectorAll(`[aria-label="${cameraOff}"]`));
    let cameraOnQuery = Array.from(document.querySelectorAll(`[aria-label="${cameraOn}"]`));        
    let cameraState =
        cameraOffQuery.length > 0 ? "OFF" :
        cameraOnQuery.length > 0 ? "ON" :
        "UNKNOWN";

    let handOff = "Raise hand";
    let handOn = "Lower hand";
    let handOffQuery = Array.from(document.querySelectorAll(`[aria-label="${handOff}"]`));
    let handOnQuery = Array.from(document.querySelectorAll(`[aria-label="${handOn}"]`));        
    let handState =
        handOffQuery.length > 0 ? "OFF" :
        handOnQuery.length > 0 ? "ON" :
        "UNKNOWN";
    
    let callOff = "Join Workroom"
    let callOn = "End call";
    let callOffQuery = Array.from(document.querySelectorAll(`[aria-label="${callOff}"]`));    
    let callOnQuery = Array.from(document.querySelectorAll(`[aria-label="${callOn}"]`));        
    let callState =
        callOffQuery.length > 0 ? "OFF" :
        callOnQuery.length > 0 ? "ON" : "UNKNOWN";

    return [micState, cameraState, handState, callState].join(" ");
}
