# THIS IS THE DEV SCRIPT
# THIS IS THE DEV SCRIPT

from flask import Flask, request, render_template, redirect, url_for, flash, session
import csv
import re
import os
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = "your_secret_key"
UPLOAD_FOLDER = "uploads"
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def get_exclusions_from_file(input_exclusion_file, column_name):
    exclusion_list = []
    try:
        with open(input_exclusion_file, 'r', newline='') as exclusions_csv:
            reader = csv.DictReader(exclusions_csv)
            if column_name not in reader.fieldnames:
                return [], f"Error: '{column_name}' not found in file."
            for row in reader:
                exclusion_list.append(row[column_name])
    except Exception as e:
        return [], f"Error reading exclusion file: {e}"
    return exclusion_list, None

def get_outlook_file(outlook_filename):
    try:
        with open(outlook_filename, 'r', encoding='utf-8', errors='ignore') as outlook_file:
            return outlook_file.read(), None
    except Exception as e:
        return None, f"Error reading Outlook file: {e}"

def find_matches(content, exclusion_list):
    matches = []
    for keyword in exclusion_list:
        if re.search(re.escape(keyword), content, re.IGNORECASE):
            matches.append(keyword)
    return matches

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        exclusion_file = request.files["exclusions"]
        outlook_file = request.files["outlook"]

        if not exclusion_file or not outlook_file:
            flash("Both files are required.")
            return redirect(request.url)

        excl_path = os.path.join(app.config["UPLOAD_FOLDER"], secure_filename(exclusion_file.filename))
        outlook_path = os.path.join(app.config["UPLOAD_FOLDER"], secure_filename(outlook_file.filename))

        exclusion_file.save(excl_path)
        outlook_file.save(outlook_path)

        exclusions, error1 = get_exclusions_from_file(excl_path, "Value")
        content, error2 = get_outlook_file(outlook_path)

        if error1 or error2:
            flash(error1 or error2)
            return redirect(request.url)

        matches = find_matches(content, exclusions)
        return render_template("results.html", matches=matches, content=content, exclusions=exclusions)

    return render_template("index.html")

if __name__ == "__main__":
    app.run()
