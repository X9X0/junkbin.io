# Junkbin.io

![Version](https://img.shields.io/badge/version-0.9.0-05d9e8?style=flat-square&labelColor=0a0a0f)
![Status](https://img.shields.io/badge/status-beta-f72585?style=flat-square&labelColor=0a0a0f)
![Stack](https://img.shields.io/badge/stack-Django%20%2B%20React-44cf6c?style=flat-square&labelColor=0a0a0f)

> "NO USER SERVICEABLE PARTS INSIDE" - We respectfully disagree.

A community-driven database for documenting electronic components found in consumer electronics. Transform e-waste into a searchable salvage ground for repair and DIY projects.

## 🎯 Mission

Help people repair their devices by cataloging which consumer products contain specific electronic components. Turn landfill-bound electronics into a valuable parts database.

## ✨ Features

- **Product Database**: Document make, model, revision, and region
- **Component Catalog**: Cross-reference ICs, FETs, passives, and modules
- **Visual Documentation**: High-res PCB photos with component locations
- **Smart Search**: Find products containing specific parts
- **Community Moderation**: Report inaccuracies, build reputation
- **Dual Submission Levels**: Basic (major components) or Advanced (everything)

## 🚀 Quick Start

### Prerequisites

- Docker & Docker Compose
- Git
- Linux server (Ubuntu 22.04+, Fedora 39+, Arch, or Debian 12+)
- Domain name (for SSL)

### Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/junkbin.io.git
cd junkbin.io

# Run deployment script
chmod +x deployment/junkbin-deploy.sh
sudo ./deployment/junkbin-deploy.sh

# Follow the prompts for:
# - Domain name
# - Email for SSL certificates
# - Admin credentials
```

### Manual Development Setup

```bash
# Backend
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver

# Frontend
cd frontend
npm install
npm run dev
```

## 📖 Documentation

- [Roadmap](docs/ROADMAP.md) - Project roadmap with feature breakdown
- [Project Structure](docs/PROJECT_STRUCTURE.md) - Codebase layout and conventions

## 🎨 Tech Stack

### Backend
- Django 5.x + Django REST Framework
- PostgreSQL 15+
- Redis 7+
- Celery

### Frontend
- React 19 with Vite 7.3
- TypeScript
- Tailwind CSS
- React Query

### Infrastructure
- Docker & Docker Compose
- Nginx
- Let's Encrypt SSL

## 🤝 Contributing

We welcome contributions! Areas we need help with:

- ⬜ Component database population
- ⬜ PCB photography
- ⬜ Code contributions
- ⬜ Documentation
- ⬜ UI/UX design
- ⬜ Testing

## 📜 License

- **Code**: MIT License
- **User Content**: Creative Commons BY-SA 4.0

See [LICENSE](LICENSE) for details.

## 🔒 Security

Found a security issue? Please email security@junkbin.io instead of creating a public issue.

## 🌟 Acknowledgments

- Inspired by Wikipedia's collaborative model
- Built for the right-to-repair community
- Dedicated to reducing e-waste

## 📞 Contact

- **Website**: https://junkbin.io
- **Email**: admin@junkbin.io

---

*"They tried to hide the parts. We're bringing them to light."*
