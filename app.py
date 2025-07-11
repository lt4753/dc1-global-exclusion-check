# DEV DEV DEV DEV DEV
# DEV DEV DEV DEV DEV
# DEV DEV DEV DEV DEVdev

from flask import Flask, request, render_template, redirect, url_for, flash, session
import csv
import re
import os
# import pandas as pd
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

# NEW
def full_exclusion_file(input_exclusion_file):
    with open(input_exclusion_file, 'r', newline='') as full_exclusions_csv:
        reader = csv.DictReader(full_exclusions_csv)
        rows = list(reader)
        return rows

def get_outlook_file(outlook_filename):
    try:
        with open(outlook_filename, 'r', encoding='utf-8', errors='ignore') as outlook_file:
            return outlook_file.read(), None
    except Exception as e:
        return None, f"Error reading Outlook file: {e}"

def get_outlook_file_lines(outlook_filename):  #---------------------- TEST
    attend = []
    with open(outlook_filename, 'r', encoding='utf-8', errors='ignore') as outlook_file:
        reader = outlook_file.readlines()
        for att in reader:
            if 'ATTENDEE;' in att:
                attend.append("Attendee: " + str(att.split(":")[-1]))
    return attend


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
        full_csv_output = full_exclusion_file(excl_path)
        lines_from_ofile = get_outlook_file_lines(outlook_path) #---------------- TEST

        if error1 or error2:
            flash(error1 or error2)
            return redirect(request.url)

        matches = find_matches(content, exclusions)
        return render_template("results.html", matches=matches, content=content, exclusions=exclusions, full_csv_output=full_csv_output, lines_from_ofile=lines_from_ofile) 

    return render_template("index.html")

if __name__ == "__main__":
    app.run()
