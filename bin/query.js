// The order of states returned [mic, camera] and the text of the states must
// match the Python code which interprets this. This function returns an array
// of values rather than a single one so that we can avoid issuing multiple
// queries per tick.
() => {
    // Regular expressions to idetify buttons. These must be kept in-sync
    // between toggle.js <=> query.js
    // ***** BEGIN *****
    let micButtonRegex = /microphone/i;
    let cameraButtonRegex = /video|camera/i;
    let handButtonRegex = /hand/i;
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

    return [micState, cameraState, handState].join(" ");
}