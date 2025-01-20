# Google Calendar Event Creator

## Overview
This project provides a Flask-based web application to create Google Calendar events using user input processed via the OpenAI API. The application supports Google OAuth 2.0 for authorization and utilizes Let's Encrypt SSL certificates for secure deployment.

## Prerequisites
Before running the application, ensure you have the following:

- **Python 3.x** installed
- **Flask** and dependencies
- **Google Calendar API credentials** (`credentials.json`)
- **OpenAI API key**
- **Let's Encrypt SSL certificates**

## Setup Instructions

### 1. Obtain OpenAI API Key
1. Visit [OpenAI's platform](https://platform.openai.com/).
2. Sign in or create an account.
3. Navigate to the API section to generate an API key.
4. Replace `YOUR-OPENAI-API-KEY` in the code with your actual key.

### 2. Setup Google Calendar API
1. Go to the [Google Cloud Console](https://console.developers.google.com/).
2. Create a new project.
3. Enable the Google Calendar API.
4. Create OAuth 2.0 credentials and download the `credentials.json` file.
5. Place `credentials.json` in the project directory.
6. Add the following under **Authorized JavaScript origins** for browser-based requests:
   - `http://localhost:5000`
   - `https://yourdomain.com`
7. Add the following under **Authorized redirect URIs**:
   - `http://localhost:5000/oauth2callback`
   - `https://yourdomain.com/oauth2callback`

### 3. Obtain SSL Certificates (Let's Encrypt)
1. Install Certbot following the instructions for your web server and OS.
2. Run the command to obtain certificates:
   ```bash
   sudo certbot certonly --standalone -d yourdomain.com
   ```
3. Replace `PATH/fullchain.pem` and `PATH/privkey.pem` in the code with your certificate paths.

### 4. Install Dependencies
Run the following command to install the required Python libraries:
```bash
pip install -r requirements.txt
```

### 5. Configure and Use Chrome Extension
The Chrome extension files are available in the `extension/` folder of this repository.

1. Open `extension/background.js` and modify the following line to point to your server:
   ```javascript
   const url = "https://yourdomain.com:5000/create_event"; // Replace with your URL
   ```
2. Open `chrome://extensions/` in your Chrome browser.
3. Enable Developer mode (toggle in the top-right corner).
4. Click on **Load unpacked**, and select the `extension/` folder from the repository.
5. The extension will be added to Chrome and ready to use.
6. To use the extension, select text on a webpage, right-click, and choose **Send to Calendar** from the context menu.

### 6. Run the Application
Start the Flask application by running:
```bash
python app.py
```
The application will be accessible at `https://yourdomain.com:5000`.

## Usage

### 1. Authorize Google Calendar Access
Visit the following URL in your browser to authorize access:
```
https://yourdomain.com:5000/authorize
```
After successful authorization, credentials will be saved to `cred.json`.

### 2. Create an Event
You can create an event using the Chrome extension:
1. Select the desired text on any webpage.
2. Right-click and choose **Send to Calendar** from the context menu.
3. The event will be created, and a confirmation will be displayed.

Alternatively, you can send a POST request with JSON input:
```bash
curl -X POST https://yourdomain.com:5000/create_event \
    -H "Content-Type: application/json" \
    -d '{"text": "Meeting with team at 10 AM on Monday"}'
```
The response will contain the Google Calendar event link.

## Error Handling
- Ensure that `cred.json` is present after authorization.
- Verify API keys and credentials if encountering authentication issues.
- Check the Flask application logs for detailed error messages.

## Security Considerations
- Keep `credentials.json` and `cred.json` secure.
- Use environment variables instead of hardcoded keys.
- Renew Let's Encrypt certificates regularly to avoid expiration.

## License
This project is licensed under the MIT License.

