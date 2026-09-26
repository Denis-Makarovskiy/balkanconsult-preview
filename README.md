# Balkan Consult — static browsing preview

Generated from the reviewed v74-rc5 public content only. The repository contains rendered HTML and public static assets, not the register database or server code. Every HTML page carries `noindex`; this is a publicly accessible preview, not private access. Search is limited to the exported public dossiers; personal requests, payments and server features are unavailable.

## Release guard

GitHub Pages deploys through `.github/workflows/pages.yml` only after `python3 qa/guard.py --site .` passes. The guard checks every public page, navigation, language and `noindex` markers, and rejects changed public files whose hashes were not sealed by the full source comparison in `qa/approved-files.json`. This is an AI rendering and consistency check, not a certificate of legal correctness.
