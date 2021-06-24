(target) => {
    let re =
        (target === "mic") ? /mute/i :
        (target === "camera") ? /camera/i :
        null;

    if (re === null) {
        return;
    }

    Array.from(document.querySelectorAll('button'))
        .filter((n) => { return n.textContent.match(re); })
        .forEach((b) => { b.click(); });
}