# HCMUT Internship Filter Extension

![Chrome Web Store Users](https://img.shields.io/chrome-web-store/users/hklenfojmhmabaeodimglmcpoaeoeeka?style=for-the-badge&logo=googlechrome&logoColor=white&color=blue)
![Chrome Web Store Rating](https://img.shields.io/chrome-web-store/rating/hklenfojmhmabaeodimglmcpoaeoeeka?style=for-the-badge&logo=googlechrome&logoColor=white)
![Chrome Web Store Version](https://img.shields.io/chrome-web-store/v/hklenfojmhmabaeodimglmcpoaeoeeka?style=for-the-badge&logo=googlechrome&logoColor=white)
![Chrome Web Store Installs](https://img.shields.io/badge/Installs-375-blue?style=for-the-badge&logo=googlechrome&logoColor=white)

A Manifest V3 Chrome Extension specifically designed for students of Ho Chi Minh City University of Technology (HCMUT - Bách Khoa). This extension helps filter out companies on the CSE Internship Portal that have already recruited enough students or are located too far from the campus.

## Release Notes

### v1.1 (Current)
- **Instant Document Preview:** Added a "Open in new tab (Xem trước)" button next to all PDF and DOCX files.
- **Zero Download Clutter:** Prevent a messy downloads folder! PDFs open natively in your browser, while Word documents (.docx) are seamlessly routed through Google Docs Viewer.

### v1.0
- Initial release.
- Added "Hết Slot" (Full) and "Thực Tập Xa" (Far) company filtering capabilities.

## Features

- **Professional UI:** Modern light theme matching HCMUT colors with a clean BK logo header.
- **Scan Companies:** Quickly scans the list of companies on the internship portal via background API requests.
- **Filter "Hết Slot" (Full):** Identifies companies that have explicitly stated they have enough students. Marked with a **Yellow border** and a bottom-right badge.
- **Filter "Thực Tập Xa" (Far):** Identifies companies located far away from the HCMUT campus. Marked with a **Purple border** and a top-right badge.
- **Clear Identification:** Companies matching both criteria show both indicators clearly, making it easy to see all statuses at a glance.
- **Instant Document Preview (New in v1.1):** Say goodbye to cluttered downloads! Instantly preview PDF and DOCX files directly in a new tab with zero loading time. PDFs open natively, while Word documents are seamlessly routed through Google Docs Viewer.


## Installation

You can easily install the extension directly from the Chrome Web Store:

1. Go to the extension page: **[HCMUT Internship Filter on Chrome Web Store](https://chromewebstore.google.com/detail/hcmut-internship-filter/hklenfojmhmabaeodimglmcpoaeoeeka)** 
2. Click the **"Add to Chrome"** button.
3. Click **"Add extension"** when the confirmation popup appears.
4. **Tip:** Click the puzzle icon 🧩 in your Chrome toolbar and click the "Pin" 📌 icon next to the extension to keep it easily accessible!

## How to Use

1. **Open the Portal:** Navigate to the [HCMUT CSE Internship Portal](https://internship.cse.hcmut.edu.vn/). You will see the standard grid of company logos.
![Initial State](image/before.png)

2. **Quick Scan:** Click on the extension icon in your Chrome toolbar and click the **Quick Scan** button. The extension will begin scanning each company logo sequentially.
![Scanning in Progress](image/scanning.png)

3. **Apply Filters:** Once scanning is complete, check the filters you want to apply (Hide Full or Hide Far) and click the **Apply Filters** button. The selected companies will instantly disappear from the page!
![Filtered View](image/after.png)

4. **Focus on Opportunities:** With the irrelevant companies hidden, you can now focus entirely on the open opportunities that are still recruiting and conveniently located!
