# EnderDrive

Just a very basic implementation of a Google-Drive or HFS-like application written in python.
It is designed to run on Linux and Windows.

Features:

    -Registration
    -Login
    -File browsing in our own space
    -Upload files
    -Admin user management fixing
    -Upload folders functionality

To-do:
    -Share files or folders functionality with random generated links

For docker:
    Image: twm420k/enderdrive
    Inner port: 5000
    Volumes:
        - /app/instance
        - /app/uploads
