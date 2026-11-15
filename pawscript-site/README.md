# Pawscript — pet video storefront prototype

An interactive, mobile-first e-commerce concept site for personalized talking-pet videos.

## Live preview
https://pawscript-pet-video-demo.onrender.com

## Prototype includes
- Responsive English-language marketing landing page
- Six scene concepts: Podcast, TED-style talk, Pet News, Awards, Courtroom, Roast
- Local pet photo preview (no uploads to a server)
- Interactive configurator: scenario, pet name, voice, script, duration
- Illustrative pricing: 15s €14.99, 30s €24.99, 45s €34.99
- Concept order review modal, FAQ, and mobile navigation
- No payment processing, uploads, AI calls, or video generation

## Hosting
The preview is deliberately isolated on the `pawscript-website-demo` branch, inside `pawscript-site/`.
The original repository's `main` branch has not been modified.

Render static site:
- Branch: `pawscript-website-demo`
- Publish directory: `pawscript-site`
- Build command: `echo 'Pawscript static site ready'`
- Automatic deploys on push

To run locally: download `index.html` and open it in a browser. Internet access is needed for Google Fonts and the photo placeholders.

## Before a real launch
1. Pick a final brand and confirm legal/trademark/domain availability.
2. Replace all third-party stock photos with owned/licensed pet footage, including actual demo videos.
3. Build a secure file-upload pipeline (object storage, validation, signed URLs and deletion policies).
4. Integrate a video-generation worker with job queue, status tracking and retry policy.
5. Connect checkout, taxes/VAT, email delivery and refunds.
6. Add terms, privacy notice, consent, customer support and realistic delivery guarantees.
7. Test generation costs, lip-sync quality and end-to-end delivery before publishing claims.

This is a concept only. Do not interpret the listed prices or delivery targets as a live offer.
