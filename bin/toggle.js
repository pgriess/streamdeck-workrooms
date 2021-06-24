(target) => {
    let re =
        (target === "mic") ? /microphone/i :
        (target === "camera") ? /video/i :
        (target === "hand") ? /hand/i :
        null;

    if (re === null) {
        return;
    }

    Array.from(document.querySelectorAll('button'))
        .filter((n) => { return n.textContent.match(re); })
        .forEach((b) => { b.click(); });
}