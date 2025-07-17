from flask import Flask, request, render_template, redirect, url_for, flash, session
import csv
import re
import os
import json
import email
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
                if reader[line].startswith('ATTENDEE;') and reader[line].strip().endswith('.com'):
                    additional_ics_info.append("Attendee: " + str(reader[line].split('mailto:')[-1]).strip())
                if reader[line].startswith('ATTENDEE;') and reader[line + 1].startswith(' '):
                    two_line_attendee = reader[line].strip() + reader[line + 1].lstrip()
                    additional_ics_info.append("Attendee: " + two_line_attendee.split('mailto:')[-1].strip())
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
        with open(outlook_filename, 'rb') as outlook_file:
            reader = email.message_from_binary_file(outlook_file) 

            sender = reader['From'].split('<')[-1].strip('>')
            additional_eml_info.append(f'From: {sender}')

            to_raw = reader['To']
            to_single_line = re.sub(r'\r?\n[ \t]+', '', to_raw).split(',')
            to_list = ''
            for recip in to_single_line:
                to_list += recip
            fixed_to_list = re.split('[<|>]', to_list)
            for to in fixed_to_list:
                if '@' in to:
                    additional_eml_info.append(f'To: {to}')

            cc_raw = reader['Cc']
            cc_single_line = re.sub(r'\r?\n[ \t]+', '', cc_raw).split(',')
            cc_list = ''
            for recip in cc_single_line:
                cc_list += recip
            fixed_cc_list = re.split('[<|>]', cc_list)
            for cc in fixed_cc_list:
                if '@' in cc:
                    additional_eml_info.append(f'Cc: {cc}')

            subject = reader['Subject']
            additional_eml_info.append(f'Subject: {subject}')

            messageid = reader['Message-ID']
            additional_eml_info.append(f'Message-ID: {messageid}')

            return additional_eml_info
        
    return []
        

def get_json_file_lines(outlook_filename):
    additional_json_info = []
    if outlook_filename.endswith('.json'):
        with open(outlook_filename, 'r', encoding='utf-8', errors='ignore') as outlook_file:

            raw_json = outlook_file.read()
            cleaned_json = re.sub(r'"body"\s*:\s*\{.*?\},?', '', raw_json, flags=re.DOTALL)
            data = json.loads(cleaned_json)
            messages = data.get("value", [])

            for email in messages:
                id = email.get('id')
                subject = email.get('subject')
                sender = email.get('sender', {}).get('emailAddress', {})
                sender_address = sender.get('address', 'N/A')
                to_recipients = email.get('toRecipients', [])
                to_addresses = sorted({recipient.get('emailAddress', {}).get('address', 'N/A') for recipient in to_recipients})
                cc_recipients = email.get('ccRecipients', [])
                cc_addresses = sorted({recipient.get('emailAddress', {}).get('address', 'N/A') for recipient in cc_recipients})
                additional_json_info.append("ID: " + id +
                    "\nSubject: " + subject +
                    "\nSender: " + sender_address +
                    "\nRecipients: " + str(to_addresses).lstrip('[').strip(']') +
                    "\nCc'ed: " + str(cc_addresses).lstrip('[').strip(']') +
                    "\n" +
                    "\n"
                    )
                
            return additional_json_info
        
    return[]


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
        lines_from_json = get_json_file_lines(outlook_path)

        if error1 or error2:
            flash(error1 or error2)
            return redirect(request.url)

        matches = find_matches(content, exclusions)
        return render_template("results.html", 
                               matches=matches, 
                               content=content, 
                               exclusions=exclusions, 
                               full_csv_output=full_csv_output, 
                               lines_from_ics=lines_from_ics, 
                               lines_from_eml=lines_from_eml,
                               lines_from_json = lines_from_json
                               ) 

    return render_template("index.html")


if __name__ == "__main__":
    app.run()

    # test test test