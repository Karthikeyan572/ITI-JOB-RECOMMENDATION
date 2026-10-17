# Frontend upload error handling fix

## Problem
The frontend treated every upload/API exception as `NOT_A_RESUME`, then displayed a rejection message that specifically claimed the file was an academic survey. This could mislabel backend downtime, network errors, parsing exceptions, or other processing failures as document rejection.

## Change
- API/network failures now use the distinct `API_ERROR` state.
- The academic/non-resume rejection panel only appears when the backend explicitly returns `NOT_A_RESUME`.
- Processing failures show “We Couldn't Analyze This File” and clarify that a processing error is not a document rejection.
- The rejection copy no longer claims academic sections were detected unless the backend's actual rejection reason says so.

## Validation
The frontend source was updated. A fresh production build still needs to be run locally with `npm ci` and `npm run build` because frontend dependency installation is environment-dependent.
