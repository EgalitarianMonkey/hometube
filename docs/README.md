# 📚 HomeTube Documentation

Welcome to the HomeTube documentation! This guide helps you install, use, and contribute to HomeTube.

## 🚀 Quick Start

| Goal                        | Documentation                           |
| --------------------------- | --------------------------------------- |
| **Install & run HomeTube**  | [Installation Guide](installation.md)  |
| **Download videos**         | [Usage Guide](usage.md)                 |
| **Deploy with Docker**      | [Docker Guide](docker.md)               |
| **Contribute code**         | [Contributing Guide](contributing.md)  |

## 📖 User Documentation

### For Users

- **[Installation Guide](installation.md)** - Set up HomeTube (Docker or local)
- **[Usage Guide](usage.md)** - Learn all features and download strategies
- **[Supported Platforms](supported-platforms.md)** - 1800+ video sources supported

### For Deployment

- **[Docker Guide](docker.md)** - Container configuration and volumes
- **[Deployment Guide](deployment.md)** - Production deployment, reverse proxy, security

## 🛠️ Developer Documentation

### For Contributors

- **[Contributing Guide](contributing.md)** - Development setup, testing, and workflow

### Architecture Reference

- **[Generic File Naming](architecture/generic-file-naming.md)** - Temporary file system and download resilience
- **[Intelligent Caching](architecture/intelligent-caching.md)** - URL info caching and resume support
- **[yt-dlp Version Management](architecture/ytdlp-version-management.md)** - Automated updates tracking

### Testing Reference

- **[Testing Guide](testing.md)** - Test framework and guidelines

## 📋 Documentation Structure

```text
docs/
├── README.md                   # This index
├── installation.md             # Setup instructions (Docker + local)
├── usage.md                    # User guide and features
├── docker.md                   # Container configuration
├── deployment.md               # Production deployment
├── supported-platforms.md      # Supported video sources
├── contributing.md             # Development setup & workflow
├── testing.md                  # Testing framework
├── architecture/               # Technical documentation
│   ├── generic-file-naming.md  # File naming system
│   ├── intelligent-caching.md  # Caching system
│   └── ytdlp-version-management.md  # Version tracking
├── examples/                   # Configuration examples
│   └── nginx/                  # Nginx configuration
├── icons/                      # Favicon
└── images/                     # Screenshots
```

## 🔗 Quick Links

- **[Main README](../README.md)** - Project overview
- **[GitHub Repository](https://github.com/EgalitarianMonkey/hometube)**
- **[GitHub Issues](https://github.com/EgalitarianMonkey/hometube/issues)**
- **[GitHub Discussions](https://github.com/EgalitarianMonkey/hometube/discussions)**

---

Happy downloading! 🎬
