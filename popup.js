document.addEventListener('DOMContentLoaded', () => {
  const scanBtn = document.getElementById('scanBtn');
  const hideFullCheck = document.getElementById('hideFullCheck');
  const hideFarCheck = document.getElementById('hideFarCheck');
  const statusDiv = document.getElementById('status');

  // Load saved state
  chrome.storage.local.get(['hideFull', 'hideFar'], (result) => {
    hideFullCheck.checked = !!result.hideFull;
    hideFarCheck.checked = !!result.hideFar;
  });

  // Scan button click
  scanBtn.addEventListener('click', async () => {
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    
    if (!tab || !tab.url || !tab.url.includes('internship.cse.hcmut.edu.vn')) {
      statusDiv.textContent = 'Please run on internship portal.';
      statusDiv.style.color = 'red';
      return;
    }

    scanBtn.disabled = true;
    statusDiv.textContent = 'Scanning...';
    statusDiv.style.color = '#333';

    chrome.tabs.sendMessage(tab.id, { action: 'SCAN_ALL' }, (response) => {
      scanBtn.disabled = false;
      if (chrome.runtime.lastError) {
        statusDiv.textContent = 'Error: Refresh the page and try again.';
        statusDiv.style.color = 'red';
      } else if (response && response.status === 'done') {
        statusDiv.textContent = 'Scan complete!';
        statusDiv.style.color = 'green';
        setTimeout(() => { statusDiv.textContent = ''; }, 3000);
      }
    });
  });

  const applyHideBtn = document.getElementById('applyHideBtn');

  // Apply Hide button click
  applyHideBtn.addEventListener('click', async () => {
    const isFullChecked = hideFullCheck.checked;
    const isFarChecked = hideFarCheck.checked;
    
    // Save state
    chrome.storage.local.set({ hideFull: isFullChecked, hideFar: isFarChecked });
    
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    if (tab && tab.url && tab.url.includes('internship.cse.hcmut.edu.vn')) {
      chrome.tabs.sendMessage(tab.id, { action: 'TOGGLE_HIDE_FULL', value: isFullChecked });
      chrome.tabs.sendMessage(tab.id, { action: 'TOGGLE_HIDE_FAR', value: isFarChecked });
      
      statusDiv.textContent = 'Filters Applied!';
      statusDiv.style.color = 'green';
      setTimeout(() => { statusDiv.textContent = ''; }, 2000);
    }
  });
});
