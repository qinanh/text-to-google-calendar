# Chrome Extension to Send Selected Text

This Chrome extension allows users to select text on a webpage and send it to a specified URL using a background script. The extension captures the selected text and communicates with the background script to perform the action.

## Project Structure

```
chrome-extension
├── src
│   ├── background.js
│   ├── content.js
│   └── manifest.json
├── package.json
└── README.md
```

## Files Description

- **src/background.js**: The background script that listens for messages from the content script and sends the selected text to the specified URL using a fetch request.

- **src/content.js**: The content script that interacts with the web page, capturing the selected text and sending a message to the background script.

- **src/manifest.json**: The configuration file for the Chrome extension, defining the extension's name, version, permissions, and scripts.

- **package.json**: The configuration file for npm, listing the dependencies and scripts for the project.

## Installation

1. Clone the repository or download the project files.
2. Open Chrome and navigate to `chrome://extensions/`.
3. Enable "Developer mode" in the top right corner.
4. Click on "Load unpacked" and select the `chrome-extension` directory.

## Usage

1. Select any text on a webpage.
2. The extension will automatically send the selected text to the specified URL.

## License

This project is licensed under the MIT License.