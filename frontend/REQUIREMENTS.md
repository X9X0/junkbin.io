# Frontend Requirements

## Node.js

**Required Version:** Node.js 22.x LTS (22.22.0+) or Node.js 20.19+

Vite 7.x requires Node.js 20.19+ or 22.12+. This project uses Node.js 22 LTS.

### Version Management

This project uses [nvm](https://github.com/nvm-sh/nvm) for Node.js version management.

```bash
# Install nvm (if not already installed)
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.1/install.sh | bash

# Reload shell
source ~/.bashrc  # or ~/.zshrc

# Install and use the correct Node version
cd frontend
nvm install    # Reads .nvmrc and installs Node 22
nvm use        # Switches to Node 22
```

### .nvmrc

The `.nvmrc` file in this directory specifies the required Node.js major version:

```
22
```

## Package Manager

npm (bundled with Node.js)

## Key Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| vite | ^7.2.4 | Build tool and dev server |
| react | ^19.x | UI framework |
| typescript | ^5.x | Type checking |
| tailwindcss | ^3.x | CSS framework |
| @tanstack/react-query | ^5.x | Data fetching |
| react-router-dom | ^7.x | Client-side routing |
| axios | ^1.x | HTTP client |
| lucide-react | ^0.x | Icon library |

## Installation

```bash
cd frontend

# Ensure correct Node version
nvm use

# Install dependencies
npm install

# Development server
npm run dev -- --host 0.0.0.0 --port 3000

# Production build
npm run build
```

## Common Issues

### "crypto.hash is not a function"

This error occurs when using Node.js < 20.19 with Vite 7.x. Upgrade to Node.js 22:

```bash
nvm install 22
nvm use 22
```

### Vite version warning

If you see "Vite requires Node.js version 20.19+ or 22.12+", ensure you're using the correct Node version via nvm.
