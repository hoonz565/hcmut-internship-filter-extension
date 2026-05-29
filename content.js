// Function to delay execution
const delay = (ms) => new Promise(resolve => setTimeout(resolve, ms));

// Store the recently clicked company ID to construct the file download link
let lastClickedCompanyId = null;

// Listen for clicks on the entire page to grab the company ID before the modal opens
document.addEventListener('click', (e) => {
    const box = e.target.closest('.logo-box');
    if (box) {
        const figure = box.querySelector('figure');
        if (figure) {
            lastClickedCompanyId = figure.getAttribute('data-id');
        }
    }
}, true); // Use capture phase to ensure it runs before React's event handlers


// ─────────────────────────────────────────────────────────────────────────────
// AI JD CLASSIFICATION
// ─────────────────────────────────────────────────────────────────────────────



/**
 * Fetch industry tags and key skills for a company from the FastAPI backend.
 *
 * Uses `sessionStorage` as a client-side cache so the same company is never
 * POSTed twice within the same browser tab session.
 *
 * @param {string} companyName  Human-readable name (used as the cache key and MongoDB key).
 * @param {string} jdText       Raw JD / description text to send to Gemini.
 * @returns {Promise<{industry_tags: string[], key_skills: string[], cached: boolean} | null>}
 *          Returns null on any error so callers can fail gracefully.
 */
async function fetchCompanyTags(companyName, jdText) {
    // ── 1. Check sessionStorage cache ──────────────────────────────────────
    const cacheKey = `ai_tags:${companyName}`;
    const stored = sessionStorage.getItem(cacheKey);
    if (stored) {
        try {
            return JSON.parse(stored);
        } catch {
            // Corrupt entry — fall through and re-fetch
            sessionStorage.removeItem(cacheKey);
        }
    }

    // ── 2. Proxy the request through the background service worker ─────────
    //   Direct fetch() to http://localhost from a https:// content script is
    //   blocked by Chrome's Private Network Access policy. The background
    //   worker is origin-free and can reach localhost without restriction.
    try {
        const response = await chrome.runtime.sendMessage({
            action: 'fetchAIClassification',
            companyName,
            jdText,
        });

        if (!response || !response.success) {
            console.error(`[HCMUT AI] Background fetch failed for "${companyName}": ${response?.error}`);
            return null;
        }

        const data = response.data;

        // ── 3. Persist to sessionStorage ───────────────────────────────────
        sessionStorage.setItem(cacheKey, JSON.stringify(data));
        return data;

    } catch (error) {
        // chrome.runtime.sendMessage throws if the background worker is not ready
        console.error(`[HCMUT AI] sendMessage error for "${companyName}": `, error);
        return null;
    }
}

/**
 * Silently store the AI-returned industry tags on the company card element.
 * No DOM visuals are rendered — the tags are kept as a data attribute so
 * the filter logic can read them at any time.
 *
 * @param {Element} box          The `.logo-box` element for the company card.
 * @param {{ industry_tags: string[] }} tagsData
 */
function storeAiTags(box, tagsData) {
    if (!tagsData || !tagsData.industry_tags) return;
    // Normalise to lowercase for reliable matching
    box.dataset.aiTags = tagsData.industry_tags.map(t => t.toLowerCase()).join(',');
}

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

            // ── AI Classification ───────────────────────────────────────────────────
            // Build the JD text from whatever text fields are available in the API response.
            // IMPORTANT: Replace `item.name` with the actual company name field if it
            // differs in the portal's API (e.g. item.companyName, item.title, etc.).
            const companyName = item.name || item.companyName || item.title || dataId;
            const jdText = [item.description, item.work, item.requirement, item.benefit]
                .filter(Boolean)   // drop undefined/null fields
                .join('\n\n');

            if (jdText.trim().length > 0) {
                // Fire-and-forget: don't await so the main scan loop isn't blocked.
                // Tags are stored silently as a data attribute — no DOM visuals.
                fetchCompanyTags(companyName, jdText).then(tagsData => {
                    if (tagsData) {
                        storeAiTags(box, tagsData);
                    }
                });
            }
            // ── End AI Classification ───────────────────────────────────────────────

            // Save the newly fetched data to the cache object
            cache[dataId] = { isFull, isFar, files: item.internshipFiles || [] };
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

    // Process PDF/DOCX file links
    processFileLinks();
});

async function processFileLinks() {
    const fileLinks = document.querySelectorAll('a.d-block.text-info:not(.processed-file-link)');
    if (fileLinks.length === 0) return;

    const storageData = await chrome.storage.local.get(['companyCache']);
    const cache = storageData.companyCache || {};

    fileLinks.forEach(link => {
        const text = link.textContent.trim().toLowerCase();
        if (text.endsWith('.pdf') || text.endsWith('.docx') || text.endsWith('.doc')) {
            link.classList.add('processed-file-link');

            // Inject the button INSIDE the <a> tag.
            // - It preserves the d-block layout so each file stays on its own row.
            // - It flows inline with the text preventing messy line breaks.
            // - React will automatically clean up this button if the component re-renders (preventing duplicate buttons).

            const fileName = link.textContent.trim();

            // Create "Open in new tab" button
            const openBtn = document.createElement('button');
            openBtn.textContent = 'Mở tab mới (Xem trước)';
            // Style it like a small badge/button
            openBtn.style.padding = '4px 8px';
            openBtn.style.fontSize = '12px';
            openBtn.style.cursor = 'pointer';
            openBtn.style.border = 'none';
            openBtn.style.borderRadius = '4px';
            openBtn.style.backgroundColor = '#17a2b8';
            openBtn.style.color = 'white';
            openBtn.style.fontWeight = 'bold';
            openBtn.style.whiteSpace = 'nowrap';

            // Construct the original file link based on the clicked company ID and filename
            // The fixed formula of the university server is: /company/{companyId}{fileName}
            let fileUrl = null;
            if (lastClickedCompanyId) {
                fileUrl = `https://internship.cse.hcmut.edu.vn/company/${lastClickedCompanyId}${fileName}`;
            }

            openBtn.onclick = (e) => {
                e.preventDefault();
                e.stopPropagation();

                if (fileUrl) {
                    if (fileName.toLowerCase().endsWith('.pdf')) {
                        // Modern browsers natively support fast direct PDF viewing, bypassing Google Docs
                        window.open(fileUrl, '_blank');
                    } else {
                        // Word files (.docx, .doc) cannot be rendered natively by browsers, so they must be routed through Google Docs Viewer
                        const viewerUrl = `https://docs.google.com/viewer?url=${encodeURIComponent(fileUrl)}`;
                        window.open(viewerUrl, '_blank');
                    }
                } else {
                    alert("Không tìm thấy ID công ty. Vui lòng tắt bảng này và click lại vào công ty!");
                }
            };

            // Add margin to separate from the filename
            openBtn.style.marginLeft = '10px';

            // Append the button inside the link tag
            link.appendChild(openBtn);
        }
    });
}

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

    if (request.action === 'APPLY_INDUSTRY_FILTER') {
        applyIndustryFilter(request.activeTags || []);
        sendResponse({ status: "updated" });
    }
});

/**
 * Show or hide company cards based on AI industry tags.
 *
 * @param {string[]} activeTags
 *   Flat list of lowercase keyword strings derived from the popup's checked
 *   industry toggles (e.g. ['web', 'mobile', 'app', 'ai', 'ml']).
 *   An empty array means "no industry filter is active" — all cards are shown.
 */
function applyIndustryFilter(activeTags) {
    const allBoxes = document.querySelectorAll('div.logo-box');

    // No industry filter active → reveal all cards (only Full/Far rules apply)
    if (activeTags.length === 0) {
        allBoxes.forEach(box => {
            box.style.display = '';
        });
        return;
    }

    allBoxes.forEach(box => {
        const rawTags = box.dataset.aiTags || '';

        if (rawTags === '') {
            // AI tags not yet fetched for this card — leave it visible so we
            // don't hide companies we haven't classified yet.
            box.style.display = '';
            return;
        }

        // Check if at least one active keyword appears in the stored tags string
        const hasMatch = activeTags.some(keyword => rawTags.includes(keyword));
        box.style.display = hasMatch ? '' : 'none';
    });
}