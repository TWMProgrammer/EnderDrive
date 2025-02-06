from flask import Flask, render_template, request, send_file, redirect, url_for
import os

app = Flask(__name__)

root_dir = '/home/louis/Desktop/EnderDrive/files'

current_dir_files = []

@app.route('/', methods=['GET', 'POST'])
def index():
    global current_dir_files

    if request.method == 'GET':
        # Get all files and directories in the root directory
        current_dir_files = []
        for file_name in os.listdir(root_dir):
            file_path = os.path.join(root_dir, file_name)
            if os.path.isfile(file_path):
                current_dir_files.append(file_name)
            elif os.path.isdir(file_path):
                current_dir_files.append(file_name)

    elif request.method == 'POST':
        file = request.files['file']
        filename = file.filename
        filepath = os.path.join(root_dir, filename)
        with open(filepath, 'wb') as f:
            for chunk in file.stream:
                f.write(chunk)

        # Add the uploaded file to the current directory files list
        if filepath not in current_dir_files:
            current_dir_files.append(filename)

    return render_template('index.html', files=current_dir_files)

@app.route('/<path:path>', methods=['GET', 'POST'])
def serve_file(path):
    global root_dir
    filepath = os.path.join(root_dir, path)
    global current_dir_files
    if request.method == 'GET':
        if os.path.exists(filepath):
            if os.path.isfile(filepath):
                #downloads the file
                return send_file(filepath, as_attachment=True)
            
            elif os.path.isdir(filepath):   
                # Get all files and directories in the current directory
                current_dir_files = []
                for file_name in os.listdir(filepath):
                    file_path = os.path.join(filepath, file_name)
                    if os.path.isfile(file_path):
                        current_dir_files.append(path+"/"+file_name)
                    elif os.path.isdir(file_path):
                        current_dir_files.append(path+"/"+file_name)
        
        else:
            return 'File not found', 404
        
    elif request.method == 'POST':
        file = request.files['file']
        filename = file.filename
        filepath = os.path.join(filepath, filename)
        with open(filepath, 'wb') as f:
            for chunk in file.stream:
                f.write(chunk)

        # Add the uploaded file to the current directory files list
        if filepath not in current_dir_files:
            current_dir_files.append(path+"/"+filename)

    return render_template('index.html', files=current_dir_files)

@app.route('/parent')
def go_back():
    global current_dir_files
    # Update the current directory files list to point to the parent directory
    current_dir_files = []
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(port=8000)