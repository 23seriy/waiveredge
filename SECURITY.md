# Security Policy

## Reporting a Vulnerability

If you discover a security vulnerability in WaiverEdge, please report it
responsibly:

1. **Email:** [23seriy@gmail.com](mailto:23seriy@gmail.com)
2. **Do not** open a public issue for security vulnerabilities.

You can expect an initial response within 48 hours. We'll work with you to
understand the issue and coordinate a fix before any public disclosure.

## Scope

- Backend API (`backend/`)
- Frontend application (`frontend/`)
- Deployment configurations (`k8s/`, `render.yaml`, `docker-compose.yml`)

## Best Practices for Contributors

- Never commit secrets, API keys, or credentials — use environment variables.
- The `.env` file is gitignored; use `.env.example` as a template.
- Report any accidentally committed secrets immediately.
