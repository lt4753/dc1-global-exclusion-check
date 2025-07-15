# DEV DEV DEV DEV DEV

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

def get_ics_file_lines(outlook_filename):
    additional_ics_info = []
    if outlook_filename.endswith('.ics'):
        with open(outlook_filename, 'r', encoding='utf-8', errors='ignore') as outlook_file:
            reader = outlook_file.readlines()
            for line in range(len(reader)):
                # NEED TO ADJUST LOGIC FOR ATTENDEES SPANNING TO A SECOND LINE
                if reader[line].startswith('ATTENDEE;'):
                    additional_ics_info.append("Attendee: " + str(reader[line].split('mailto:')[-1]).strip())
                if reader[line].startswith('UID:'):
                    uid_single_line = reader[line]
                    if reader[line + 1].startswith(' '):
                        uid_multi_line = reader[line].strip() + reader[line + 1].lstrip()
                        additional_ics_info.append(uid_multi_line.replace('UID:', 'UID: '))
                    else: additional_ics_info.append(uid_single_line.replace('UID:', 'UID: '))
                if reader[line].startswith('ORGANIZER;'):
                    additional_ics_info.append("Organizer: " + str(reader[line].split('mailto:')[-1]).strip())
            return sorted(additional_ics_info, reverse=True)
    return []

def get_eml_file_lines(outlook_filename):
    additional_eml_info = []
    if outlook_filename.endswith('.eml'):
        with open(outlook_filename, 'r', encoding='utf-8', errors='ignore') as outlook_file:
            reader = outlook_file.readlines()
            for line in range(len(reader)):
                if reader[line].startswith('From:'):
                    additional_eml_info.append("Sender: " + str(reader[line].split('<')[-1].replace('>', '').strip()))
                if reader[line].startswith('Message-ID:'):
                    message_id1 = reader[line].replace(': <', ': ')
                    message_id2 = ''
                    message_id = ''
                    if reader[line + 1].startswith(' '):
                        message_id2 = reader[line + 1].replace('<', '')
                        message_id = message_id1 + message_id2
                        additional_eml_info.append(message_id.replace('>', '').strip())
                    additional_eml_info.append(message_id1.replace('>', '').strip())
                # NEED TO SOLVE LOGIC FOR EXTAR LINES PAST THE FIRST TWO
                # NEED TO SOLVE FOR EXTRA POSSIBLE EXTAR SPACE IN TO HEADER SPANNING TWO LINES
                if reader[line].startswith('To:'):
                    eml_to_single_line = re.split('[<|>]', reader[line])
                    eml_to = reader[line]
                    if reader[line + 1].startswith(' '):
                        eml_to_next_line = reader[line + 1]
                        eml_to += eml_to_next_line
                        clean_eml_to_multiline = re.split('[<|>]', eml_to)
                        for recipient in clean_eml_to_multiline:
                            if '@' in recipient:
                                additional_eml_info.append(f'To: {recipient}'.strip(' '))
                    else:
                        for recipient in eml_to_single_line:
                            if '@' in recipient:
                                additional_eml_info.append(f'To: {recipient}'.strip('>'))
                # ADDING LOGIC FOR CC
                # WILL NEED TO APPLY 3+ LINE LOGIC TO THIS SECTION
                if reader[line].startswith('Cc:'):
                    eml_cc_single_line = re.split('[<|>]', reader[line])
                    eml_cc = reader[line]
                    if reader[line + 1].startswith(' '):
                        eml_cc_next_line = reader[line + 1]
                        eml_cc += eml_to_next_line
                        clean_eml_cc_multiline = re.split('[<|>]', eml_cc)
                        for recipient in clean_eml_cc_multiline:
                            if '@' in recipient:
                                additional_eml_info.append(f'Cc: {recipient}'.strip(' '))
                    else:
                        for recipient in eml_cc_single_line:
                            if '@' in recipient:
                                additional_eml_info.append(f'Cc: {recipient}'.strip('>'))
            return additional_eml_info
    return []
                
            

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
        lines_from_ics = get_ics_file_lines(outlook_path)
        lines_from_eml = get_eml_file_lines(outlook_path)

        if error1 or error2:
            flash(error1 or error2)
            return redirect(request.url)

        matches = find_matches(content, exclusions)
        return render_template("results.html", matches=matches, content=content, exclusions=exclusions, full_csv_output=full_csv_output, lines_from_ics=lines_from_ics, lines_from_eml=lines_from_eml) 

    return render_template("index.html")

if __name__ == "__main__":
    app.run()
