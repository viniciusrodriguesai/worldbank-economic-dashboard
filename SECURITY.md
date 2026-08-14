# Security policy

## Reporting a vulnerability

Do not open a public issue for a suspected vulnerability. Use GitHub's private security
advisory reporting for this repository. Include the affected endpoint or component,
reproduction steps, impact, and a suggested mitigation when possible. Never include real
credentials or personal data in a report.

The maintainer will acknowledge a complete report as soon as practical, validate its
impact, and coordinate remediation and disclosure. There is no paid bug bounty. Good-faith
research must avoid privacy violations, data destruction, service disruption, and access
beyond what is needed to demonstrate the issue.

## Supported version

Security fixes are applied to the current `main` branch. This portfolio project does not
maintain older release branches.

## Deployment responsibility

Deployers must terminate HTTPS at a trusted reverse proxy or platform, configure an exact
`CORS_ORIGINS` allowlist, keep secrets out of `VITE_*` variables, apply resource limits,
and keep Python, Node, container, and GitHub Action dependencies patched. See
`docs/SECURITY_AUDIT.md` and `docs/THREAT_MODEL.md` for the reviewed scope and residual
risks.
