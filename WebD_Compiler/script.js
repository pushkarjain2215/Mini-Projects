function compileCode() {
    const htmlContent = document.getElementById("html").value;
    const cssContent = document.getElementById("css").value;
    const jsContent = document.getElementById("js").value;

    const outputFrame = document.createElement("iframe");
    outputFrame.style.width = "100%";
    outputFrame.style.height = "100%";
    document.getElementById("output").innerHTML = "";
    document.getElementById("output").appendChild(outputFrame);

    const iframeDoc =
        outputFrame.contentDocument || outputFrame.contentWindow.document;

    iframeDoc.open();
    iframeDoc.write(htmlContent);
    iframeDoc.close();

    const style = iframeDoc.createElement("style");
    style.textContent = cssContent;
    iframeDoc.head.appendChild(style);

    const script = iframeDoc.createElement("script");

    script.textContent = `
        (function() {
            const originalConsoleLog = console.log;
            console.log = function(message) {
                window.parent.postMessage({ type: 'console', message: message }, '*');
                originalConsoleLog(message);
            };
        })();
        ${jsContent}
    `;
    iframeDoc.body.appendChild(script);
}

window.addEventListener("message", function (event) {
    if (event.data.type === "console") {
        const consoleOutput = document.getElementById("console");
        const newLog = document.createElement("div");
        newLog.textContent = event.data.message;
        consoleOutput.appendChild(newLog);
    }
});
