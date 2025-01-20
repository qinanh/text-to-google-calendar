// This file contains the background script for the Chrome extension. It listens for messages from the content script and sends the selected text to the specified URL using a fetch request.

chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    if (request.action === "sendText") {
        const url = "https://example.com:port/create_event"; // Replace with your URL
        const data = {
            text: request.text
        };

        fetch(url, {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify(data)
        })
        .then(response => response.json())
        .then(data => {
            console.log("Success:", data);
            sendResponse({status: "success", data: data});
        })
        .catch((error) => {
            console.error("Error:", error);
            sendResponse({status: "error", error: error});
        });

        return true; // Indicates that the response will be sent asynchronously
    }
});