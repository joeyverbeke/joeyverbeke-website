# Joey Verbeke — self-hosted portfolio

This is a framework-free static portfolio: 28 HTML pages, one local stylesheet,
one local JavaScript file, and locally hosted images and fonts. It has no build
step and no dependency on a website platform, package manager, or CMS.

The only intentional runtime exceptions are the embedded Vimeo, YouTube,
SoundCloud, and Tribune-hosted media players. If those providers are blocked,
the rest of each page remains fully functional.

## Preview locally

Run:

```sh
python3 serve-local.py
```

Then open the URL printed in the terminal. The server supports the same clean,
extensionless routes configured for Vercel.

If port 8766 is already in use, choose another local port with
`python3 serve-local.py --port 8092`.

## Later deployment

When this local version has been approved, import the repository into Vercel
with the **Other** framework preset and no build command. `vercel.json` keeps
clean URLs, legacy redirects, and long-lived caching for hash-named media.

The site should be previewed on Vercel before connecting the domain. Keep the
old hosting account active until the production domain and SSL pass a fresh
network and visual audit.

## Maintenance

`content-manifest.json` inventories the generated pages and assets.
`scripts/migrate_static.py` can regenerate the semantic pages from the locally
preserved baseline commit. The Work Sans font is bundled under the SIL Open
Font License in `assets/fonts/OFL.txt`.
