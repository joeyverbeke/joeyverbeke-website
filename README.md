# Joey Verbeke website — Vercel deployment

This directory is the cleaned static deployment copy of the archived website. It
contains the homepage and 27 distinct portfolio pages, with their locally archived,
original-resolution media files.

## Deploy with a Git repository

1. Make this directory the root of a Git repository and push it to your personal
   GitHub account. Alternatively, if the parent repository is used, select
   `website-for-vercel` as the Vercel project's Root Directory.
2. Import the repository in Vercel.
3. Select **Other** as the framework preset.
4. Leave the build command empty. There is no framework build step.
5. Deploy the preview and test it before connecting `joeyverbeke.com`.

`vercel.json` removes `.html` from public URLs, maps old hashed project URLs to their
actual standalone project pages, redirects retired template/collection URLs, and enables
long-lived caching for hash-named media.

The cleanup removed duplicate Squarespace collection captures, the duplicate `/home-1`
page, empty legacy collection shells, and the template blog pages. Media referenced only
by those removed pages was also removed. The full untouched archive remains in the
parent directory.

## Size note

The directory is approximately 243 MB. A Vercel Hobby CLI upload has a documented
100 MB source limit, so use the Git-connected deployment workflow first. The full raw
crawl and its duplicate recovery media remain in the parent archive and are not part of
this deployment directory.

Do not cancel Squarespace or change DNS until the Vercel preview has been checked and
the manual recovery tasks in the parent archive are complete.
