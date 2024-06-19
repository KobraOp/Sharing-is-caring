from pyngrok import ngrok, conf
from flask import Flask, render_template, request, redirect, url_for, flash, send_file, after_this_request
from pymongo import MongoClient, errors
import gridfs
import threading
import os
import io
from bson import ObjectId
from tkinter import *
import webbrowser
import logging

# Setup logging
logging.basicConfig(level=logging.DEBUG)

# To setup MongoDB Atlas
# Step 1: Go to MongoDB Atlas webpage
# Step 2: Create your account and after that create a new cluster and select the free version of it
# Step 3: Get the credentials from it of Connection String, Database Name, Collection Name

#Set your credentials from the mongo atlas 
connection_string = "Your Connection string"
db_name = ""  # Database name
collection_name = ""  # Collection name

app = Flask(__name__)
app.secret_key = 'supersecretkey'

client = MongoClient(connection_string)
db = client[db_name]  # Access the specified database
fs = gridfs.GridFS(db, collection=collection_name)  # Use the specified collection for GridFS

@app.route("/")
def home():
    return render_template("sender.html")

@app.route("/receive")
def receive():
    image_files = db[collection_name + '.files'].find()
    return render_template("receiver.html", image_files=image_files)

@app.route("/upload", methods=["POST"])
def upload():
    try:
        if "file" not in request.files:
            flash("No file part")
            return redirect(request.url)
        
        file = request.files["file"]
        
        if file.filename == "":
            flash("No selected file")
            return redirect(request.url)
        
        if file:
            file_id = fs.put(file, filename=file.filename)
            flash("File successfully uploaded")
            return redirect(url_for("home"))
    except Exception as e:
        flash(f"An error occurred during upload: {str(e)}")
        app.logger.error(f"Error uploading file: {str(e)}")
    
    return redirect(url_for("home"))

@app.route("/download/<file_id>")
def download(file_id):
    try:
        logging.info(f"Starting download for file_id: {file_id}")

        file = fs.get(ObjectId(file_id))

        @after_this_request
        def remove_file(response):
            fs.delete(file._id)
            logging.info(f"Deleted file with file_id: {file_id} from GridFS")
            return response

        file_content = file.read()
        return send_file(io.BytesIO(file_content),
                         download_name=file.filename,
                         as_attachment=True)
    
    except gridfs.errors.NoFile:
        flash(f"File with ID {file_id} not found in GridFS")
    
    except Exception as e:
        flash(f"An error occurred during download: {str(e)}")
        app.logger.error(f"Error downloading file: {str(e)}")
    
    return redirect(url_for("receive"))

@app.route("/download")
def download_all():
    try:
        logging.info("Starting download_all function")
        files = list(fs.find())

        if not files:
            flash("No files to download")
            return redirect(url_for("receive"))

        @after_this_request
        def remove_files(response):
            for file in files:
                fs.delete(file._id)
                logging.info(f"Deleted {file.filename} from GridFS")
            return response
        file_content = [file.read() for file in files]
        return send_file(io.BytesIO(file_content[0]),
                         download_name=files[0].filename,
                         as_attachment=True)
    
    except Exception as e:
        flash(f"An error occurred during download: {str(e)}")
        app.logger.error(f"Error downloading files: {str(e)}")
    
    return redirect(url_for("receive"))

def db_connect():
    try:
        client.admin.command('ping')
        return True
    except errors.ServerSelectionTimeoutError as e:
        print(f"Error connecting to MongoDB: {e}")
        return False

public_url = None

def start_ngrok():
    global public_url
    try:
        conf.get_default().auth_token = "2YGeeEGoHJXyR29piuZBdvbd6m8_4EEq3HDakGUKfzRMpQrdR"
        public_url = ngrok.connect(addr=8000, proto="http", hostname="amazing-magpie-remarkably.ngrok-free.app")
        print(f"ngrok tunnel is running at {public_url}")
        if db_connect():
            return True
        else:
            return False
    except Exception as e:
        print(f"Error starting ngrok: {e}")
        return False

def run_flask():
    app.run(port=8000)

def boot_server(start_button, stop_button, status_label, prompt_label, next_button):
    if start_ngrok():
        start_button.config(state=DISABLED)
        stop_button.config(state=NORMAL)
        status_label.config(text="Server started successfully!", fg="green")
        threading.Thread(target=run_flask).start()
        prompt_label.config(text="Server and MongoDB connected. Click 'Next' to continue.", fg="green")
        next_button.config(state=NORMAL)
    else:
        status_label.config(text="Failed to start server or connect to MongoDB.", fg="red")

def stop_server(start_button, stop_button, status_label, prompt_label, next_button):
    try:
        ngrok.disconnect(public_url)
        ngrok.kill()
        status_label.config(text="Server stopped.", fg="red")
        start_button.config(state=NORMAL)
        stop_button.config(state=DISABLED)
        next_button.config(state=DISABLED)
        prompt_label.config(text="")
    except Exception as e:
        status_label.config(text=f"Error stopping server: {e}", fg="red")

def on_start_button_click():
    status_label.config(text="Starting server...", fg="blue")
    threading.Thread(target=boot_server, args=(start_button, stop_button, status_label, prompt_label, next_button)).start()

def on_stop_button_click():
    status_label.config(text="Stopping server...", fg="blue")
    threading.Thread(target=stop_server, args=(start_button, stop_button, status_label, prompt_label, next_button)).start()

def on_next_button_click():
    global public_url
    if public_url:
        webbrowser.open(public_url.public_url)
    else:
        prompt_label.config(text="Public URL not found.", fg="red")

if __name__ == "__main__":
    root = Tk()
    root.title("Sender Server")
    root.geometry("400x300")

    Label(root, text="Hello User..", fg="red", font=(None, 20)).pack(pady=10)
    status_label = Label(root, text="", font=(None, 12))
    status_label.pack(pady=5)
    start_button = Button(root, text="Start", command=on_start_button_click)
    start_button.pack(pady=5)
    stop_button = Button(root, text="Stop", command=on_stop_button_click, state=DISABLED)
    stop_button.pack(pady=5)
    next_button = Button(root, text="Next", state=DISABLED, command=on_next_button_click)
    next_button.pack(pady=5)
    prompt_label = Label(root, text="", font=(None, 12))
    prompt_label.pack(pady=10)

    root.mainloop()
