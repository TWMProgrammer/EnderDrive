# EnderDrive

Just a very basic implementation of a Google-Drive or HFS-like application written in python.
It is designed to run on Linux and Windows.

Features:

    - Registration
    - Login
    - File browsing in our own space
    - Upload files
    - Admin user management
    - Upload folders functionality
    - Share files or folders functionality with random generated links

To-do:

    - General search utilising database for faster searching

For docker:

    Image: twm420k/enderdrive
    Inner port: 5000
    Volumes:
        - /app/instance
        - /app/uploads

Run:

    docker run -d -p 5000:5000 -v enderdrive_instance:/app/instance -v enderdrive_uploads:/app/uploads twm420k/enderdrive
