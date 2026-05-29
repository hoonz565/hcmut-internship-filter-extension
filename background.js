// background.js — Manifest V3 Service Worker
//
// WHY THIS EXISTS:
//   content.js runs in the context of https://internship.cse.hcmut.edu.vn.
//   Browsers block cross-origin requests from a secure page to http://localhost
//   (Private Network Access restriction). The background service worker is NOT
//   bound to any tab origin, so it can freely fetch http://localhost:8000
//   without triggering CORS or Private Network Access errors.

const AI_API_URL = 'http://localhost:8000/api/v1/classify-company';

chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    if (request.action !== 'fetchAIClassification') return false;

    const { companyName, jdText } = request;

    fetch(AI_API_URL, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ company_name: companyName, jd_text: jdText }),
    })
        .then(async (res) => {
            if (!res.ok) {
                const errText = await res.text();
                sendResponse({ success: false, error: `HTTP ${res.status}: ${errText}` });
                return;
            }
            const data = await res.json();
            sendResponse({ success: true, data });
        })
        .catch((err) => {
            // Backend not running, network error, etc.
            sendResponse({ success: false, error: err.message });
        });

    return true; // Keep the message channel open for the async response
});
