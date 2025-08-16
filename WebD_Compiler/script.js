function compileCode() {

    const htmlContent = document.getElementById('html').value;
    const cssContent = document.getElementById('css').value;
    const jsContent = document.getElementById('js').value;


    const outputFrame = document.createElement('iframe');
    outputFrame.style.width = '100%';
    outputFrame.style.height = '100%';
    document.getElementById('output').innerHTML = '';
    document.getElementById('output').appendChild(outputFrame);


    const iframeDoc = outputFrame.contentDocument || outputFrame.contentWindow.document;


    iframeDoc.open();
    iframeDoc.write(htmlContent);
    iframeDoc.close();


    const style = iframeDoc.createElement('style');
    style.textContent = cssContent;
    iframeDoc.head.appendChild(style);


    const script = iframeDoc.createElement('script');
    script.textContent = jsContent;
    iframeDoc.body.appendChild(script);

}