function compileCode() {
    // Get the values from the input fields
    const htmlContent = document.getElementById('html').value;
    const cssContent = document.getElementById('css').value;
    const jsContent = document.getElementById('js').value;

    // Create a new HTML document for the output
    const outputFrame = document.createElement('iframe');
    outputFrame.style.width = '100%';
    outputFrame.style.height = '100%';
    document.getElementById('output').innerHTML = ''; // Clear the output area
    document.getElementById('output').appendChild(outputFrame);

    // Create a document in the iframe
    const iframeDoc = outputFrame.contentDocument || outputFrame.contentWindow.document;

    // Add HTML content
    iframeDoc.open();
    iframeDoc.write(htmlContent);
    iframeDoc.close();

    // Add CSS content
    const style = iframeDoc.createElement('style');
    style.textContent = cssContent;
    iframeDoc.head.appendChild(style);

    // Add JavaScript content
    const script = iframeDoc.createElement('script');
    script.textContent = jsContent;
    iframeDoc.body.appendChild(script);
}