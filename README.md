# EnderDrive

Just a very basic implementation of a Google-Drive or HFS-like application written in python.

## Project Description

EnderDrive is a secure cloud storage solution that allows users to store, share, and access their files from anywhere with enterprise-grade security. It is designed to run on both Linux and Windows environments, providing a consistent experience across platforms.

## First-Time Setup

When you first run EnderDrive, you'll be guided through a setup wizard that helps you configure the system:

1. Create an administrator account
   - Choose a secure username and password
   - The admin account has unlimited storage and full system access

2. After setup is complete, you can:
   - Log in with your admin credentials
   - Create additional user accounts
   - Configure system settings

## Key Features

- **User Authentication & Authorization**

  - Secure user registration and login system
  - Role-based access control (Admin/User)
  - Session management and security

- **File Management**

  - Secure file browsing in personal space
  - File and folder upload/download capabilities
  - Bulk file operations
    - Multi-file selection and manipulation
    - Batch delete, move, and copy operations
    - Mass file sharing capabilities
    - Efficient handling of large file sets
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
- Gunicorn WSGI server (Linux)
- Waitress WSGI server (Windows)

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
  ghcr.io/twmprogrammer/enderdrive:main
```

## Quick Start with Docker Compose

```yaml
version: "3.8"

services:
  enderdrive:
    image: ghcr.io/twmprogrammer/enderdrive:main
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

- Development server: `run_debug.py` - Uses Flask's built-in development server
- Production server: `run_production.py` - Uses Gunicorn on Linux and Waitress on Windows

### System Requirements

- Python 3.9 or higher
- Dependencies listed in requirements.txt

### Running in Development Mode

```bash
python run_debug.py
```

### Running in Production Mode

```bash
python run_production.py
```

The production server automatically detects your operating system and uses:

- **Linux:** Gunicorn with 4 workers (configurable via WORKERS environment variable)
- **Windows:** Waitress WSGI server (included in requirements.txt)

You can configure the host and port using environment variables:

```bash
# Example: Custom host and port
HOST=0.0.0.0 PORT=8080 python run_production.py
```

## Project Structure

```txt
app/
├── controllers/     # Route handlers and business logic
│   ├── admin.py     # Admin dashboard functionality
│   ├── auth.py      # Authentication and user management
│   ├── file_manager.py # File operations and management
│   └── sharing.py   # File sharing functionality
├── models/          # Database models
│   ├── activity_log.py # User activity tracking
│   ├── file.py      # File metadata model
│   ├── folder.py    # Folder structure model
│   ├── role.py      # User roles and permissions
│   ├── shared_link.py # Sharing functionality
│   └── user.py      # User account management
├── static/          # Static assets (CSS, JS)
├── templates/       # Jinja2 HTML templates
└── utils/          # Utility functions and helpers
    ├── decorators.py # Access control decorators
    ├── filesystem.py # File system operations
    └── setup_wizard.py # First-time setup configuration
```

## Environment Variables

The application supports the following environment variables:

- `HOST`: The host address to bind to (default: 0.0.0.0 on Linux, 127.0.0.1 on Windows)
- `PORT`: The port to listen on (default: 5000)
- `WORKERS`: Number of worker processes for Gunicorn (default: 4)
- `FLASK_ENV`: Environment type (development/production)
- `FLASK_DEBUG`: Enable/disable debug mode
