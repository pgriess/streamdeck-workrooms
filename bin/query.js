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
    // ***** END *****

    let micOffRegex = /^unmute microphone$/i;
    let micOnRegex = /^mute microphone$/i;
    let micText = Array.from(document.querySelectorAll('button'))
        .filter((n) => { return n.textContent.match(micButtonRegex); })
        .map((n) => { return n.textContent; })
        .join('');
    let micState =
        (micText.match(micOffRegex)) ? "OFF" :
        (micText.match(micOnRegex)) ? "ON" :
        "UNKNOWN";

    let cameraOffRegex = /^turn on (camera|video)$/i;
    let cameraOnRegex = /^turn off (camera|video)$/i;
    let cameraText = Array.from(document.querySelectorAll('button'))
        .filter((n) => { return n.textContent.match(cameraButtonRegex); })
        .map((n) => { return n.textContent; })
        .join('');
    let cameraState =
        (cameraText.match(cameraOffRegex)) ? "OFF" :
        (cameraText.match(cameraOnRegex)) ? "ON" :
        "UNKNOWN";

    let handOffRegex = /^raise hand$/i;
    let handOnRegex = /^lower hand$/i;
    let handText = Array.from(document.querySelectorAll('button'))
        .filter((n) => { return n.textContent.match(handButtonRegex); })
        .map((n) => { return n.textContent; })
        .join('');
    let handState =
        (handText.match(handOffRegex)) ? "OFF" :
        (handText.match(handOnRegex)) ? "ON" :
        "UNKNOWN";

    // Heuristic to detect pages which match the call URL, but don't have any
    // call buttons. Rather than returning UNKNOWN for these (which would
    // result in an error show to the user), return our sentinel NONE value so
    // that the daemon handles this appropriately.
    //
    // N.B. The array length check is based on the pre-call UI having 7 buttons
    //      and the in-call UI having 10. Anything less than 7 is "probably"
    //      the post-call UI.
    //
    // Fixes #22
    if (micState === "UNKNOWN" &&
            cameraState === "UNKNOWN" &&
            handState === "UNKNOWN" &&
            Array.from(document.querySelectorAll('button')).length < 7) {
        return "NONE";
    }

    return [micState, cameraState, handState].join(" ");
}