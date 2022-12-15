(target) => {
    // Regular expressions to idetify buttons. These must be kept in-sync
    // between toggle.js <=> query.js
    // ***** BEGIN *****
    let micButtonRegex = /^(mute|unmute) microphone$/i;
    let cameraButtonRegex = /^turn (off|on) (video|camera)$/i;
    let handButtonRegex = /^(raise|lower) hand$/i;
    let callButtonRegex = /^(join as )|(join room)|(join workroom)|(end call)/i;
    // ***** END *****

    let re =
        (target === "mic") ? micButtonRegex :
        (target === "camera") ? cameraButtonRegex :
        (target === "hand") ? handButtonRegex :
        (target == "call") ? callButtonRegex :
        null;

    if (re === null) {
        return;
    }

    Array.from(document.querySelectorAll('div'))        
        .filter((n) => { return n.ariaLabel != null })
        .filter((n) => { return n.ariaLabel.match(re); })
        .forEach((b) => { b.click(); });
}
