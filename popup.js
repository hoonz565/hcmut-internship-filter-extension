document.addEventListener('DOMContentLoaded', () => {
  // ── Element refs ──────────────────────────────────────────────────────────
  const scanBtn       = document.getElementById('scanBtn');
  const applyHideBtn  = document.getElementById('applyHideBtn');
  const statusDiv     = document.getElementById('status');

  // Basic filters
  const hideFullCheck = document.getElementById('hideFullCheck');
  const hideFarCheck  = document.getElementById('hideFarCheck');

  // Industry filter toggles
  const INDUSTRY_FILTERS = [
    { key: 'filterWeb',      el: document.getElementById('filterWeb'),      tags: ['Web'] },
    { key: 'filterApp',      el: document.getElementById('filterApp'),      tags: ['App'] },
    { key: 'filterAI',       el: document.getElementById('filterAI'),       tags: ['AI'] },
    { key: 'filterData',     el: document.getElementById('filterData'),     tags: ['Data'] },
    { key: 'filterDevOps',   el: document.getElementById('filterDevOps'),   tags: ['DevOps'] },
    { key: 'filterEmbedded', el: document.getElementById('filterEmbedded'), tags: ['Embedded'] },
  ];

  // ── Load persisted state on popup open ───────────────────────────────────
  const allStorageKeys = [
    'hideFull', 'hideFar',
    ...INDUSTRY_FILTERS.map(f => f.key),
  ];

  chrome.storage.local.get(allStorageKeys, (result) => {
    hideFullCheck.checked = !!result.hideFull;
    hideFarCheck.checked  = !!result.hideFar;
    INDUSTRY_FILTERS.forEach(f => {
      f.el.checked = !!result[f.key];
    });
  });

  // ── Scan button ───────────────────────────────────────────────────────────
  scanBtn.addEventListener('click', async () => {
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });

    if (!tab || !tab.url || !tab.url.includes('internship.cse.hcmut.edu.vn')) {
      setStatus('Please run on internship portal.', 'red');
      return;
    }

    scanBtn.disabled = true;
    setStatus('Scanning…', '#0084ff');

    chrome.tabs.sendMessage(tab.id, { action: 'SCAN_ALL' }, (response) => {
      scanBtn.disabled = false;
      if (chrome.runtime.lastError) {
        setStatus('Error: Refresh the page and try again.', 'red');
      } else if (response && response.status === 'done') {
        setStatus('Scan complete! Apply filters below.', '#013b8e');
        clearStatusAfter(3000);
      }
    });
  });

  // ── Apply Filters button ──────────────────────────────────────────────────
  applyHideBtn.addEventListener('click', async () => {
    const isFullChecked = hideFullCheck.checked;
    const isFarChecked  = hideFarCheck.checked;

    // Build the active industry tag keywords from checked toggles
    const activeIndustryTags = INDUSTRY_FILTERS
      .filter(f => f.el.checked)
      .flatMap(f => f.tags);   // flatten all keyword arrays into one list

    // Persist everything to storage
    const storagePayload = {
      hideFull: isFullChecked,
      hideFar:  isFarChecked,
    };
    INDUSTRY_FILTERS.forEach(f => {
      storagePayload[f.key] = f.el.checked;
    });
    chrome.storage.local.set(storagePayload);

    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    if (!tab || !tab.url || !tab.url.includes('internship.cse.hcmut.edu.vn')) return;

    // Send the three filter messages to the content script
    chrome.tabs.sendMessage(tab.id, { action: 'TOGGLE_HIDE_FULL', value: isFullChecked });
    chrome.tabs.sendMessage(tab.id, { action: 'TOGGLE_HIDE_FAR',  value: isFarChecked });
    chrome.tabs.sendMessage(tab.id, {
      action: 'FILTER_COMPANIES',
      activeTags: activeIndustryTags,
    });

    setStatus('Filters Applied!', 'green');
    clearStatusAfter(2000);
  });

  // ── Helpers ───────────────────────────────────────────────────────────────
  function setStatus(text, color) {
    statusDiv.textContent  = text;
    statusDiv.style.color  = color;
  }

  let _clearTimer = null;
  function clearStatusAfter(ms) {
    if (_clearTimer) clearTimeout(_clearTimer);
    _clearTimer = setTimeout(() => { statusDiv.textContent = ''; }, ms);
  }
});
