// Function to delay execution
const delay = (ms) => new Promise(resolve => setTimeout(resolve, ms));

// UI rendering function (adds badges and classes)
function applyCompanyVisuals(box, isFull, isFar) {
    if (isFull) {
        box.classList.add('company-full');
        // Prevent adding duplicate badges if re-scanned
        if (!box.querySelector('.badge-full')) {
            const badgeFull = document.createElement('div');
            badgeFull.className = 'internship-badge badge-full';
            badgeFull.textContent = 'HẾT SLOT';
            box.appendChild(badgeFull);
        }
    }
    if (isFar) {
        box.classList.add('company-far');
        // Prevent adding duplicate badges if re-scanned
        if (!box.querySelector('.badge-far')) {
            const badgeFar = document.createElement('div');
            badgeFar.className = 'internship-badge badge-far';
            badgeFar.textContent = 'THỰC TẬP XA';
            box.appendChild(badgeFar);
        }
    }
}

async function scanCompanies(forceRefresh = false) {
    // Ensure elements are visible during the scanning process
    document.body.classList.remove('hide-full-companies');
    document.body.classList.remove('hide-far-companies');

    const logoBoxes = document.querySelectorAll('div.logo-box:not(.scanned)');
    
    // Retrieve current cache from local storage
    const storageData = await chrome.storage.local.get(['companyCache']);
    const cache = storageData.companyCache || {};
    let hasNewData = false;

    for (const box of logoBoxes) {
        // Mark as scanned to prevent duplicate processing in the current DOM state
        box.classList.add('scanned');

        const figure = box.querySelector('figure');
        if (!figure) continue;
        const dataId = figure.getAttribute('data-id');
        if (!dataId) continue;

        // Use cached data for instant rendering if available AND forceRefresh is false
        if (!forceRefresh && cache[dataId]) {
            applyCompanyVisuals(box, cache[dataId].isFull, cache[dataId].isFar);
            continue; 
        }

        // Fetch from API if not in cache OR if a force refresh is explicitly requested
        try {
            await delay(300); 
            let url = `https://internship.cse.hcmut.edu.vn/home/company/id/${dataId}`;
            let response = await fetch(url, { headers: { 'Accept': 'application/json' } });
            
            if (!response.ok) continue;
            
            let text = await response.text();
            let data;
            try {
                data = JSON.parse(text);
            } catch (e) {
                console.error(`[HCMUT Intern] API returned non-JSON for ${dataId}.`);
                continue;
            }

            const item = data.item || data.data || data;

            let isFull = false;
            let isFar = false;
            const desc = item.description ? item.description.toLowerCase() : "";
            const work = item.work ? item.work.toLowerCase() : "";

            // Determine FULL status based on description keywords or accepted students count
            if (desc.includes("chương trình đã nhận đủ sv") || desc.includes("đã nhận đủ") || work.includes("đã nhận đủ")) {
                isFull = true;
            }
            if (item.studentAccepted !== undefined && item.maxAcceptedStudent > 0 && item.studentAccepted >= item.maxAcceptedStudent) {
                isFull = true;
            }

            // Determine FAR status based on description keywords
            if (desc.includes("vì địa điểm thực tập xa trường đh bách khoa") || work.includes("thực tập xa")) {
                isFar = true;
            }

            // Apply visual changes to the DOM
            applyCompanyVisuals(box, isFull, isFar);

            // Save the newly fetched data to the cache object
            cache[dataId] = { isFull, isFar };
            hasNewData = true;

        } catch (error) {
            console.error(`[HCMUT Intern] Error fetching data for ${dataId}:`, error);
        }
    }

    // If new data was fetched, update the cache in local storage
    if (hasNewData) {
        await chrome.storage.local.set({ companyCache: cache });
    }

    // Restore hide/show filters based on user's last saved preference
    restoreHideState();
    return true;
}

// Function to restore hide/show settings
function restoreHideState() {
    chrome.storage.local.get(['hideFull', 'hideFar'], (result) => {
        if (result.hideFull) document.body.classList.add('hide-full-companies');
        else document.body.classList.remove('hide-full-companies');
        
        if (result.hideFar) document.body.classList.add('hide-far-companies');
        else document.body.classList.remove('hide-far-companies');
    });
}


const observer = new MutationObserver((mutations) => {
    const unScannedBoxes = document.querySelectorAll('div.logo-box:not(.scanned)');
    if (unScannedBoxes.length > 0) {
        scanCompanies(); 
    }
});

// Start observing changes on the entire body tag
observer.observe(document.body, { childList: true, subtree: true });

// Initial run on page load
restoreHideState();


// ---------------------------------------------------------
// MESSAGE LISTENER (From Popup)
// ---------------------------------------------------------
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    if (request.action === 'SCAN_ALL') {
        // Pass 'true' to forceRefresh, ignoring the cache and fetching fresh data from the server
        scanCompanies(true).then(() => {
            sendResponse({ status: "done" });
        });
        return true; // Keep the message channel open for async response
    }

    if (request.action === 'TOGGLE_HIDE_FULL') {
        if (request.value) {
            document.body.classList.add('hide-full-companies');
        } else {
            document.body.classList.remove('hide-full-companies');
        }
        sendResponse({ status: "updated" });
    }

    if (request.action === 'TOGGLE_HIDE_FAR') {
        if (request.value) {
            document.body.classList.add('hide-far-companies');
        } else {
            document.body.classList.remove('hide-far-companies');
        }
        sendResponse({ status: "updated" });
    }
});