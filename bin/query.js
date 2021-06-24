// The order of states returned [mic, camera] and the text of the states must
// match the Python code which interprets this. This function returns an array
// of values rather than a single one so that we can avoid issuing multiple
// queries per tick.
() => {
    let micText = Array.from(document.querySelectorAll('button'))
        .filter((n) => { return n.textContent.match(/microphone/i); })
        .map((n) => { return n.textContent; })
        .join('');
    let micState =
        (micText === "Unmute microphone") ? "OFF" :
        (micText === "Mute microphone") ? "ON" :
        "UNKNOWN";

    let cameraText = Array.from(document.querySelectorAll('button'))
        .filter((n) => { return n.textContent.match(/video/i); })
        .map((n) => { return n.textContent; })
        .join('');
    let cameraState =
        (cameraText === "Turn on video") ? "OFF" :
        (cameraText === "Turn off video") ? "ON" :
        "UNKNOWN";

    let handText = Array.from(document.querySelectorAll('button'))
        .filter((n) => { return n.textContent.match(/hand/i); })
        .map((n) => { return n.textContent; })
        .join('');
    let handState =
        (handText === "Raise hand") ? "OFF" :
        (handText === "Lower hand") ? "ON" :
        "UNKNOWN";

    return [micState, cameraState, handState].join(" ");
}