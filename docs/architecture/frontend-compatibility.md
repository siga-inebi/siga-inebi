# Frontend Compatibility and Static Budgets

## Browser and device contract

The reference low-end profile is an Android phone with 2 GB RAM and a 360 x 640 viewport. Production JavaScript explicitly targets Chrome 107, Edge 107, Firefox 104, and Safari 16, preserving the Vite 7 baseline while making the transpilation contract reviewable.

Release smoke coverage is expected on current and current-1 Chrome for Android, plus current Firefox and Safari. The camera preview requires a secure context, `navigator.mediaDevices.getUserMedia`, and user permission. It prefers the rear camera with `facingMode: { ideal: "environment" }`; closing, retrying, unmounting, or receiving an unusable stream stops every acquired track.

QR decoding and attendance movement registration are not part of this compatibility layer.

## Static resource budgets

`npm run build` generates the Vite manifest and then runs `scripts/check-build-budget.mjs`. The checker follows static imports from the manifest entry for initial transfer and computes each reachable lazy route's additional static imports. Sizes use gzip compression for transfer budgets and raw bytes for raster assets. Vite asset inlining is disabled so emitted graphics remain visible to the manifest-based gate instead of bypassing their dedicated cap as data URLs.

| Metric | Maximum |
| --- | ---: |
| Initial HTML, CSS, JavaScript, and referenced graphics | 230,000 gzip bytes |
| Increment for any lazy route | 20,000 gzip bytes |
| Initial resources plus any one lazy route | 250,000 gzip bytes |
| Any emitted raster graphic | 25,000 raw bytes |

The caps are deliberate ceilings based on the measured pre-change build: 281,735 initial gzip bytes, 877-11,793 gzip bytes per lazy route, and an 87,787-byte source logo. The logo is emitted from a right-sized 128 x 128 WebP source; this removes the dominant avoidable initial transfer while preserving more than 2x pixel density at its largest 56 px display size.

API responses and user-uploaded media are excluded. They require representative datasets and separate runtime limits rather than a static build manifest. A budget increase must update this document with measured evidence and remain a strict cap.
