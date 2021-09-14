(target) => {
    // Regular expressions to idetify buttons. These must be kept in-sync
    // between toggle.js <=> query.js
    // ***** BEGIN *****
    let micButtonRegex = /^(mute|unmute) microphone$/i;
    let cameraButtonRegex = /^turn (off|on) (video|camera)$/i;
    let handButtonRegex = /^(raise|lower) hand$/i;
    let callButtonRegex = /^(join as )|(join room)|(end call)/i;
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

    Array.from(document.querySelectorAll('span'))
        // Node.textContent rolls up text from all child nodes. If there are
        // nested spans, this will cause /all/ of the spans to match. Really we
        // just want the leaf. Strip out all nodes that have children.
        .filter((n) => { return n.childElementCount === 0 })
        .filter((n) => { return n.textContent.match(re); })
        .forEach((b) => { b.click(); });
}
