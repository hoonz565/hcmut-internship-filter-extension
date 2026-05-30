document.addEventListener('DOMContentLoaded', async () => {
  // ── Element refs ──────────────────────────────────────────────────────────
  const scanBtn       = document.getElementById('scanBtn');
  const applyHideBtn  = document.getElementById('applyHideBtn');
  const statusDiv     = document.getElementById('status');
  const dynamicTagsContainer = document.getElementById('dynamic-tags-container');

  // Basic filters
  const hideFullCheck = document.getElementById('hideFullCheck');
  const hideFarCheck  = document.getElementById('hideFarCheck');

  // Industry filter toggles
  let INDUSTRY_FILTERS = [];

  const CORE_TAGS = ['Web', 'App', 'AI', 'Data', 'DevOps', 'Embedded'];
  const EMOJI_MAP = {
    'Web': '🌐',
    'App': '📱',
    'AI': '🤖',
    'Data': '📊',
    'DevOps': '⚙️',
    'Embedded': '🔌',
    'Other': '🏢'
  };

  try {
    const response = await chrome.runtime.sendMessage({ action: 'FETCH_TAGS' });
    let uniqueTags = new Set();

    if (response && response.success && response.data) {
      Object.values(response.data).forEach(tagsArray => {
        tagsArray.forEach(t => {
            if (t && t !== 'Other') uniqueTags.add(t);
        });
      });
    }

    let sortedTags = Array.from(uniqueTags).sort((a, b) => {
      let idxA = CORE_TAGS.indexOf(a);
      let idxB = CORE_TAGS.indexOf(b);
      if (idxA !== -1 && idxB !== -1) return idxA - idxB;
      if (idxA !== -1) return -1;
      if (idxB !== -1) return 1;
      return a.localeCompare(b);
    });

    if (sortedTags.length === 0) {
      sortedTags = [...CORE_TAGS];
    }

    sortedTags.forEach(tag => {
      const id = `filter_${tag.replace(/[^a-zA-Z0-9]/g, '')}`;
      const emoji = EMOJI_MAP[tag] ? EMOJI_MAP[tag] + ' ' : '🔖 ';
      
      const label = document.createElement('label');
      label.className = 'checkbox-wrapper';
      label.innerHTML = `
        <span>${emoji}${tag}</span>
        <div class="switch">
          <input type="checkbox" id="${id}">
          <span class="slider"></span>
        </div>
      `;
      dynamicTagsContainer.appendChild(label);

      INDUSTRY_FILTERS.push({
        key: id,
        el: document.getElementById(id),
        tags: [tag]
      });
    });
  } catch (error) {
    console.error("Error loading dynamic tags:", error);
  }

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
