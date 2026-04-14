# Documentation

This repo uses [Fern](https://buildwithfern.com) to build and publish the documentation site to `docs.nvidia.com/ising-calibration`.

## Structure

```
fern/
  docs.yml          # Global site config (theme, layout, nav, redirects)
  latest.yml        # Navigation tree for the "Latest" version
  fern.config.json  # Fern org + CLI version pin
  main.css          # NVIDIA theme overrides
  assets/           # Logo SVGs and favicon
  components/       # Custom MDX components (BadgeLinks, CustomFooter)

docs/latest/        # All documentation source files (.mdx)
  index.mdx
  quick-start/
  user-guide/
  developer-guide/
  _static/images/   # Images referenced by docs pages
```

## Prerequisites

- Node.js 20+

```bash
npm install -g fern-api
```

## Local preview

Run a live-reloading preview server from the repo root:

```bash
cd fern
fern docs dev
```

Fern will print a temporary preview URL. The preview rebuilds automatically when you save changes to `fern/` or `docs/`.

## Validate without publishing

Check configuration, navigation, and broken links without touching the live site:

```bash
cd fern
fern check
```

## Publish manually

Publishing requires the `DOCS_FERN_TOKEN` secret (see [CI setup](#ci-workflows) below).

**From your local machine:**

```bash
cd fern
FERN_TOKEN=<your-token> fern generate --docs
```

**Via git tag** (recommended for production releases):

```bash
git tag docs/v1.2.0
git push origin docs/v1.2.0
```

**Via GitHub Actions UI:** go to Actions → "Publish Fern Docs" → "Run workflow".

## Adding or editing pages

1. Create or edit an `.mdx` file under `docs/latest/`.
2. If it is a new file, add it to the navigation in [fern/latest.yml](../fern/latest.yml) under the appropriate section.

## CI workflows

Four GitHub Actions workflows are configured in [.github/workflows/](../.github/workflows/):

| Workflow | Trigger | What it does |
|---|---|---|
| `publish-fern-docs.yml` | Push to `main` (`docs/**` or `fern/**`), `docs/v*` tag, or manual dispatch | Publishes the live site |
| `fern-docs-preview-build.yml` | PR touching `fern/**` | Uploads sources and PR metadata as an artifact |
| `fern-docs-preview-comment.yml` | After preview-build completes | Builds a preview and posts the URL as a PR comment |
| `fern-docs-ci.yml` | PR touching `fern/**` | Validates autodocs generation |