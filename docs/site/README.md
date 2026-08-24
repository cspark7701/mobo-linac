# nkm-injection.github.io

Official documentation and project web portal for **Multi-Objective Bayesian Optimization for a 200 MeV Electron Injector Linac** (`mobo_linac`).

Live Website: [https://nkm-injection.github.io](https://nkm-injection.github.io)  
Main Code Repository: [https://github.com/cspark7701/mobo_linac](https://github.com/cspark7701/mobo_linac)

---

## Directory Structure

```
site/
├── index.html                           # Main web portal (MathJax, Chart.js, responsive RTD theme)
├── style.css                            # Unified stylesheet (glassmorphism UI & responsive layout)
├── .nojekyll                            # Bypass Jekyll processing on GitHub Pages
├── consolidated_report/
│   └── consolidated_report.pdf          # Full compiled technical report PDF
└── README.md                            # Site repository documentation
```

---

## Local Development & Preview

To preview the website locally:

```bash
# Using Python built-in HTTP server
python -m http.server 8000 --directory docs/site

# Or if inside the site directory
cd docs/site
python -m http.server 8000
```

Then open [http://localhost:8000](http://localhost:8000) in your web browser.

---

## Synchronization with `mobo_linac` Main Repository

The source files for this website are maintained and generated within `docs/site/` in the main repository:

```bash
# In main mobo_linac repository:
./scripts/sync_site.sh

# Or with custom target repository path:
./scripts/sync_site.sh /path/to/nkm-injection.github.io
```

---

## Citation & Authorship

- **Author**: Chong Shik Park
- **Affiliation**: Department of Accelerator Science and Center for Accelerator Research, Korea University, Sejong, 30019 Republic of Korea
- **Context**: Presented at ICABU 2025 (`v1.0.0`)
