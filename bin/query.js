// The order of states returned [mic, camera] and the text of the states must
// match the Python code which interprets this.
(target) => {
    if (target === "mic") {
        let micText = Array.from(document.querySelectorAll('button'))
            .filter((n) => { return n.textContent.match(/mute/i); })
            .map((n) => { return n.textContent; })
            .join('');
        return (micText === "Unmute Microphone") ? "OFF" :
               (micText === "Mute Microphone") ? "ON" :
               "UNKNOWN";
    }

    if (target === "camera") {
        let cameraText = Array.from(document.querySelectorAll('button'))
            .filter((n) => { return n.textContent.match(/camera/i); })
            .map((n) => { return n.textContent; })
            .join('');
        return (cameraText === "Turn On Camera") ? "OFF" :
               (cameraText === "Turn Off Camera") ? "ON" :
               "UNKNOWN";
    }

    return "UNKNOWN";
}