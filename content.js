// Function to delay execution
const delay = (ms) => new Promise(resolve => setTimeout(resolve, ms));

async function scanCompanies() {
  const logoBoxes = document.querySelectorAll('div.logo-box:not(.scanned)');
  
  for (const box of logoBoxes) {
    // Mark as scanned to prevent duplicate processing
    box.classList.add('scanned');
    
    const figure = box.querySelector('figure');
    if (!figure) continue;
    
    const dataId = figure.getAttribute('data-id');
    if (!dataId) continue;
    
    try {
      // Respect rate limit
      await delay(300);
      
      let data = null;
      let url = `https://internship.cse.hcmut.edu.vn/home/company/id/${dataId}`;
      
      let response = await fetch(url, { headers: { 'Accept': 'application/json' } });
      if (!response.ok) {
        console.warn(`[HCMUT Intern] Failed to fetch data for ${dataId}. Status: ${response.status}`);
        continue;
      }
      
      let text = await response.text();
      try {
        data = JSON.parse(text);
      } catch (e) {
        console.error(`[HCMUT Intern] API returned non-JSON for ${dataId}. Response snippet:`, text.substring(0, 150));
        continue;
      }
      
      const item = data.item || data.data || data; 
      
      console.log(`[HCMUT Intern] Scanning: ${item.fullname || item.shortname || dataId}`, item);

      // Determine FULL status
      let isFull = false;
      const desc = item.description ? item.description.toLowerCase() : "";
      const work = item.work ? item.work.toLowerCase() : "";
      
      if (desc.includes("chương trình đã nhận đủ sv") || desc.includes("đã nhận đủ") || work.includes("đã nhận đủ")) {
        isFull = true;
      }
      // If accepted students has reached the maximum, the company won't take more interns
      if (
        item.studentAccepted !== undefined &&
        item.maxAcceptedStudent !== undefined &&
        item.maxAcceptedStudent > 0 &&
        item.studentAccepted >= item.maxAcceptedStudent
      ) {
        isFull = true;
      }
      
      // Determine FAR status
      let isFar = false;
      if (desc.includes("vì địa điểm thực tập xa trường đh bách khoa") || work.includes("thực tập xa")) {
        isFar = true;
      }
      
      if (isFull) console.log(`[HCMUT Intern] -> Marked as FULL: ${dataId}`);
      if (isFar) console.log(`[HCMUT Intern] -> Marked as FAR: ${dataId}`);
      
      // Apply FULL styling and badge
      if (isFull) {
        box.classList.add('company-full');
        
        const badgeFull = document.createElement('div');
        badgeFull.className = 'internship-badge badge-full';
        badgeFull.textContent = 'HẾT SLOT';
        box.appendChild(badgeFull);
      }
      
      // Apply FAR styling and badge
      if (isFar) {
        box.classList.add('company-far');
        
        const badgeFar = document.createElement('div');
        badgeFar.className = 'internship-badge badge-far';
        badgeFar.textContent = 'THỰC TẬP XA';
        box.appendChild(badgeFar);
      }
      
    } catch (error) {
      console.error(`[HCMUT Intern] Fetch Error for company ${dataId}:`, error);
    }
  }
  
  // Return true when done to notify popup
  return true;
}

// Listen for messages from popup
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === 'SCAN_ALL') {
    scanCompanies().then(() => {
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

// Load initial states from storage
chrome.storage.local.get(['hideFull', 'hideFar'], (result) => {
  if (result.hideFull) {
    document.body.classList.add('hide-full-companies');
  }
  if (result.hideFar) {
    document.body.classList.add('hide-far-companies');
  }
});
