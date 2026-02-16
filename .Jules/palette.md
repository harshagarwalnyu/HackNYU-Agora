## 2025-05-24 - File Upload Accessibility
**Learning:** Upload panels often use simple `div`s with `onClick` but forget keyboard users.
**Action:** Always wrap file drop zones in `role="button"`, add `tabIndex="0"`, and handle `onKeyDown` (Enter/Space) to trigger the hidden file input.
