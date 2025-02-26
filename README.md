# EnderDrive

Just a very basic implementation of a Google-Drive or HFS-like application written in python.
It is designed to run on Linux and Windows.

## Project Description

EnderDrive is a secure cloud storage solution that allows users to store, share, and access their files from anywhere with enterprise-grade security.

## Features

- User Registration and Login
- Secure File Browsing in Personal Space
- File and Folder Upload
- Admin User Management
- Share Files/Folders with Generated Links
- Bulk Downloads
- File Type Detection
  
## To-do

- Writeup

## Technology Stack

- Python Flask Web Framework
- SQLAlchemy ORM
- Bootstrap CSS Framework
- Jinja2 Templating

## Dependencies

    Flask==2.3.1
    gunicorn==23.0.0
    Flask-SQLAlchemy==3.1.1
    greenlet==3.1.1
    itsdangerous==2.2.0
    Jinja2==3.1.5
    MarkupSafe==3.0.2
    SQLAlchemy==2.0.38
    typing_extensions==4.12.2
    Werkzeug==3.1.3
    python-magic==0.4.27

## Docker Setup

- Image: twm420k/enderdrive
- Inner port: 5000
- Volumes:
  - `./uploads:/app/uploads`
  - `./instance:/app/instance`

## Docker Run

    docker run -d -p 5000:5000 -v enderdrive_instance:/app/instance -v enderdrive_uploads:/app/uploads twm420k/enderdrive
