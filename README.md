# EnderDrive

Just a very basic implementation of a Google-Drive or HFS-like application written in python. It is designed to run on Linux and Windows.

## Project Description

EnderDrive is a secure cloud storage solution that allows users to store, share, and access their files from anywhere with enterprise-grade security. It is designed to run on both Linux and Windows environments, providing a consistent experience across platforms.

## Key Features

- **User Authentication & Authorization**

  - Secure user registration and login system
  - Role-based access control (Admin/User)
  - Session management and security

- **File Management**

  - Secure file browsing in personal space
  - File and folder upload/download capabilities
  - Bulk file operations
  - File type detection and validation
  - Hierarchical folder structure

- **Sharing Capabilities**

  - Generate secure sharing links for files/folders
  - Access control for shared resources
  - Bulk download support for shared items

- **Administration**
  - Comprehensive admin dashboard
  - User management interface
  - System monitoring and control

## Security Features

- Secure authentication system
- Protected file storage
- Encrypted sharing links
- Role-based access control
- Session security
- Input validation and sanitization

## Technology Stack

### Backend

- Python Flask Web Framework
- SQLAlchemy ORM for database management
- Flask-SQLAlchemy for database integration
- Werkzeug for security utilities

### Frontend

- Bootstrap CSS Framework for responsive design
- Jinja2 Templating Engine

### Storage & Security

- SQLite database for data persistence
- File system storage with security measures
- python-magic for file type validation

## Docker Setup

### Container Configuration

- Image: ghcr.io/twm420k/enderdrive:main
- Exposed Port: 5000

### Volume Mounts

- `/app/uploads` - For persistent file storage
- `/app/instance` - For database and instance-specific data

## Quick Start with Docker

```bash
docker run -d \
  -p 5000:5000 \
  -v enderdrive_instance:/app/instance \
  -v enderdrive_uploads:/app/uploads \
  ghcr.io/twm420k/enderdrive:main
```

## Quick Start with Docker Compose

```yaml
version: "3.8"

services:
  enderdrive:
    image: ghcr.io/twm420k/enderdrive:main
    container_name: enderdrive
    ports:
      - "5000:5000"
    volumes:
      - enderdrive_uploads:/app/uploads
      - enderdrive_instance:/app/instance
    restart: unless-stopped
    networks:
      - enderdrive_network

networks:
  enderdrive_network:
    driver: bridge

volumes:
  enderdrive_uploads:
    driver: local
  enderdrive_instance:
    driver: local
```

## Development

The application includes separate configurations for development and production environments:

- Development server: `run_debug.py`
- Production server: `run_production.py`

**Note:** While Waitress is not included in the base requirements, the code includes support for running on Windows using Waitress. To use Waitress on Windows, simply install it using:

```bash
pip install waitress
```

## Project Structure

```txt
app/
├── controllers/     # Route handlers and business logic
├── models/          # Database models
├── static/          # Static assets (CSS, JS)
├── templates/       # Jinja2 HTML templates
└── utils/           # Utility functions and helpers
```
