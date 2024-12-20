import streamlit as st
import firebase_admin
from firebase_admin import credentials, storage
from datetime import datetime
import requests
import re

# Firebase initialization using secrets
if not firebase_admin._apps:
    cred = credentials.Certificate({
        "type": st.secrets["firebase"]["type"],
        "project_id": st.secrets["firebase"]["project_id"],
        "private_key_id": st.secrets["firebase"]["private_key_id"],
        "private_key": st.secrets["firebase"]["private_key"].replace("\\n", "\n"),
        "client_email": st.secrets["firebase"]["client_email"],
        "client_id": st.secrets["firebase"]["client_id"],
        "auth_uri": st.secrets["firebase"]["auth_uri"],
        "token_uri": st.secrets["firebase"]["token_uri"],
        "auth_provider_x509_cert_url": st.secrets["firebase"]["auth_provider_x509_cert_url"],
        "client_x509_cert_url": st.secrets["firebase"]["client_x509_cert_url"]
    })
    firebase_admin.initialize_app(cred, {
        'storageBucket': 'aharonilabinventory.appspot.com'
    })

# Function to fetch file content from a single URL
@st.cache_data  # Cache the result to avoid refetching unnecessarily
def fetch_file_content():
    url = "https://firebasestorage.googleapis.com/v0/b/aharonilabinventory.appspot.com/o/extracted_texts.txt?alt=media"
    response = requests.get(url)
    if response.status_code == 200:
        return response.text
    else:
        return f"Failed to fetch file: {response.status_code}"

# Function to check if a line is a description
def is_description(line):
    description_patterns = [
        r'\bDESC\b', r'\bPart Description\b', r'\bCIC\b', r'\bESC\b',
        r'\bSC\b', r'\bCAP\b', r'\bRES\b', r'\bIC\b', r'\bLED\b',
        r'\bDIODE\b', r'\bMOSFET\b', r'\bREF DES\b', r'\bTEST POINT\b',
        r'\bSCHOTTKY\b', r'\bARRAY\b', r'\bREG LINEAR\b', r'\bPOS ADJ\b',
        r'\bLENS\b', r'\bCHROMA\b', r'\bASPHERE\b', r'\bPRISM\b', r'\bOPTICS\b',
    ]
    description_regex = re.compile('|'.join(description_patterns), re.IGNORECASE)
    return bool(description_regex.search(line))

# Function to search file content
def search_in_blocks(blocks, part_number_query, value_query, footprint_query):
    search_results = []

    search_patterns = []
    if part_number_query:
        search_patterns.append(re.compile(rf'{re.escape(part_number_query)}(-ND)?', re.IGNORECASE))

    if value_query:
        value_query_cleaned = value_query.replace(" ", "")
        value_query_pattern = ""
        for i in range(len(value_query_cleaned) - 1):
            value_query_pattern += value_query_cleaned[i]
            if (value_query_cleaned[i].isdigit() and value_query_cleaned[i + 1].isalpha()) or \
                    (value_query_cleaned[i].isalpha() and value_query_cleaned[i + 1].isdigit()):
                value_query_pattern += r"\s*"
        value_query_pattern += value_query_cleaned[-1]
        search_patterns.append(re.compile(fr'\b{value_query_pattern}\b', re.IGNORECASE))

    if footprint_query:
        search_patterns.append(re.compile(rf'\b{re.escape(footprint_query)}\b', re.IGNORECASE))

    for block in blocks:
        if not block.strip():
            continue
        if all(pattern.search(block) for pattern in search_patterns):
            part_number_match = re.search(r'(?:Lot #|P/N|N):\s*([A-Za-z0-9\-\/# ]+)', block, re.IGNORECASE)
            desc_match = re.search(r'DESC:\s*(.*)', block, re.IGNORECASE)
            if not desc_match:
                block_lines = block.splitlines()
                for i, line in enumerate(block_lines):
                    if is_description(line):
                        desc_match = line.strip()
                        if "CHROMA" in desc_match.upper() and i + 2 < len(block_lines):
                            desc_match += " " + block_lines[i + 1].strip() + block_lines[i + 2].strip()
                        break
            location_match = re.search(r'Location:\s*(.*)', block, re.IGNORECASE)
            location = location_match.group(1) if location_match else "Location not available"
            part_number = part_number_match.group(1) if part_number_match else "P/N not detected"
            value = desc_match.group(1) if isinstance(desc_match, re.Match) else desc_match or "Description not available"
            search_results.append((part_number, value, location))
    return search_results

# Function to save re-order request to Firebase
def reorder_item(part_number, description, requester_name):
    """Append the re-order request to Firebase Storage."""
    current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    re_order_text = f"Date and Time: {current_time}, Part Number: {part_number}, Description: {description}, Requester Name: {requester_name}\n"
    bucket = storage.bucket()
    blob = bucket.blob('to_be_ordered.txt')

    try:
        if blob.exists():
            existing_content = blob.download_as_text()
            re_order_text = existing_content + re_order_text
        blob.upload_from_string(re_order_text)
        st.success("Re-order request saved successfully.")
    except Exception as e:
        st.error(f"Failed to save re-order request: {e}")

# Streamlit Interface
st.title("Component Search Tool")

# Inputs for search
part_number_query = st.text_input("Enter Part Number")
value_query = st.text_input("Enter Component Name / Value")
footprint_query = st.text_input("Enter Footprint")

# Search button
if st.button("Search"):
    file_content = fetch_file_content()
    if file_content.startswith("Failed to fetch file"):
        st.error(file_content)
    else:
        blocks = file_content.split("Image:")
        results = search_in_blocks(blocks, part_number_query, value_query, footprint_query)
        if results:
            st.write("### Search Results")
            for index, (part_number, value, location) in enumerate(results):
                st.write(f"- **Part Number:** {part_number}, **Description:** {value}, **Location:** {location}")
                # Ensure unique key by appending index to the part_number
                if st.button(f"Re-Order '{part_number}'", key=f"{part_number}_{index}"):
                    with st.form(f"reorder_form_{part_number}_{index}"):
                        requester_name = st.text_input("Requester Name", key=f"requester_{part_number}_{index}")
                        submit_reorder = st.form_submit_button("Submit Re-Order")
                        if submit_reorder:
                            reorder_item(part_number, value, requester_name)
        else:
            st.warning("No items found matching the search criteria.")
            if st.button("Re-Order Manually"):
                with st.form("manual_reorder_form"):
                    part_number = st.text_input("Part Number")
                    description = st.text_input("Description")
                    requester_name = st.text_input("Requester Name")
                    submit_reorder = st.form_submit_button("Submit Re-Order")
                    if submit_reorder:
                        reorder_item(part_number, description, requester_name)
