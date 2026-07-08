# Evidence Graph Browser — deploy

The browser is **static** — HTML + one `graph.js` payload + three linked
artifacts. No server, no compute. Host it on S3 behind CloudFront.

## 1. Build the bundle (deterministic projection of one run)

```bash
python -m keystone.ui.graph_browser.build --domain gbm      # -> browser_out/gbm/
python -m keystone.ui.graph_browser.build --domain insulin  # -> browser_out/insulin/
```

Each folder is self-contained: `index.html`, `graph.js`, `graph.json`,
`why_panel.html`, `future_experiments.svg`, `evidence_graph.svg`.

## 2. Preview locally

```bash
python -m http.server -d browser_out/gbm 8010   # http://127.0.0.1:8010
```

## 3. Deploy to S3 + CloudFront

```bash
# one-time
aws s3 mb s3://keystone-graph-browser

# each release (fully static — no compute, no IAM app role needed)
aws s3 sync browser_out/gbm     s3://keystone-graph-browser/gbm     --delete
aws s3 sync browser_out/insulin s3://keystone-graph-browser/insulin --delete

# front with CloudFront for HTTPS + caching, then invalidate on redeploy
aws cloudfront create-invalidation --distribution-id <DIST_ID> --paths "/*"
```

`graph.js` sets `window.KEYSTONE_GRAPH`, so the page works from `file://`, S3,
or CloudFront with no CORS/fetch dependency.

## Boundary reminder (CONTRIBUTING rule 3)

The browser only **renders** the exported graph — the doubt bands are drawn from
the exported `{point, low, high}` intervals. If you ever need a *new* number,
compute it in `keystone/deterministic/` and re-export; never in the browser.
