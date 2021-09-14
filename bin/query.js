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
    let callButtonRegex = /^(join as )|(join room)|(end call)/i;
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

    let micOffRegex = /^unmute microphone$/i;
    let micOnRegex = /^mute microphone$/i;
    let micText = Array.from(document.querySelectorAll('span'))
        .filter((n) => { return n.textContent.match(micButtonRegex); })
        .map((n) => { return n.textContent; })
        .join('');
    let micState =
        (micText.match(micOffRegex)) ? "OFF" :
        (micText.match(micOnRegex)) ? "ON" :
        "UNKNOWN";

    let cameraOffRegex = /^turn on (camera|video)$/i;
    let cameraOnRegex = /^turn off (camera|video)$/i;
    let cameraText = Array.from(document.querySelectorAll('span'))
        .filter((n) => { return n.textContent.match(cameraButtonRegex); })
        .map((n) => { return n.textContent; })
        .join('');
    let cameraState =
        (cameraText.match(cameraOffRegex)) ? "OFF" :
        (cameraText.match(cameraOnRegex)) ? "ON" :
        "UNKNOWN";

    let handOffRegex = /^raise hand$/i;
    let handOnRegex = /^lower hand$/i;
    let handText = Array.from(document.querySelectorAll('span'))
        // Node.textContent rolls up text from all child nodes. If there are
        // nested spans, this will cause /all/ of the spans to match. Really we
        // just want the leaf. Strip out all nodes that have children.
        .filter((n) => { return n.childElementCount === 0 })
        .filter((n) => { return n.textContent.match(handButtonRegex); })
        .map((n) => { return n.textContent; })
        .join('');
    let handState =
        (handText.match(handOffRegex)) ? "OFF" :
        (handText.match(handOnRegex)) ? "ON" :
        "UNKNOWN";

    let callOffRegex = /^(join as )|(join room)/i;
    let callOnRegex = /^end call$/i;
    let callText = Array.from(document.querySelectorAll('span'))
        // Node.textContent rolls up text from all child nodes. If there are
        // nested spans, this will cause /all/ of the spans to match. Really we
        // just want the leaf. Strip out all nodes that have children.
        .filter((n) => { return n.childElementCount === 0 })
        .filter((n) => { return n.textContent.match(callButtonRegex); })
        .map((n) => { return n.textContent; })
        .join('');
    let callState =
        (callText.match(callOffRegex)) ? "OFF" :
        (callText.match(callOnRegex)) ? "ON" : "UNKNOWN";

    return [micState, cameraState, handState, callState].join(" ");
}
