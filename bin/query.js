// The order of states returned [mic, camera] and the text of the states must
// match the Python code which interprets this. This function returns an array
// of values rather than a single one so that we can avoid issuing multiple
// queries per tick.
() => {
    let micText = Array.from(document.querySelectorAll('button'))
        .filter((n) => { return n.textContent.match(/mute/i); })
        .map((n) => { return n.textContent; })
        .join('');
    let micState =
        (micText === "Unmute Microphone") ? "OFF" :
        (micText === "Mute Microphone") ? "ON" :
        "UNKNOWN";

    let cameraText = Array.from(document.querySelectorAll('button'))
        .filter((n) => { return n.textContent.match(/camera/i); })
        .map((n) => { return n.textContent; })
        .join('');
    let cameraState =
        (cameraText === "Turn On Camera") ? "OFF" :
        (cameraText === "Turn Off Camera") ? "ON" :
        "UNKNOWN";

    return [micState, cameraState].join(" ");
}