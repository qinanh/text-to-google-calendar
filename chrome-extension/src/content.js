// This file captures the selected text and sends a message to the background script.

document.addEventListener('mouseup', () => {
    const selectedText = window.getSelection().toString();
    if (selectedText) {
        chrome.runtime.sendMessage({ text: selectedText });
    }
});