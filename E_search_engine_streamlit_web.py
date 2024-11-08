import streamlit as st
from datetime import datetime
import requests
import re
import firebase_admin
from firebase_admin import credentials, storage

# Firebase initialization using Streamlit secrets
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

# Function to fetch file content from Firebase Storage
@st.cache_data
def fetch_file_content():
    url = "https://firebasestorage.googleapis.com/v0/b/aharonilabinventory.appspot.com/o/extracted_texts.txt?alt=media"
    response = requests.get(url)
    if response.status_code == 200:
        return response.text
    else:
        return f"Failed to fetch file: {response.status_code}"

# Function to save re-order request to Firebase
def reorder_item(part_number, description, requester_name):
    """Append the re-order request to Firebase Storage."""
    current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    re_order_text = f"Date and Time: {current_time}, Part Number: {part_number}, Description: {description}, Requester Name: {requester_name}\n"
    bucket = storage.bucket()
    blob = bucket.blob('to_be_ordered.txt')

    try:
        # Check if the file already exists
        if blob.exists():
            # Download existing content
            existing_content = blob.download_as_text()
            # Append the new reorder entry
            re_order_text = existing_content + re_order_text
            st.write("Appending to existing content.")
        else:
            st.write("Creating a new file for reorder requests.")

        # Upload the updated content
        blob.upload_from_string(re_order_text)
        st.success("Re-order request saved successfully.")
    except Exception as e:
        st.error(f"Failed to save re-order request: {e}")
        st.write("Detailed Error:", e)

# Streamlit Interface
st.title("Component Search and Reorder Tool")

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
        # Process and display search results as before
        # Omitted here for brevity
        st.write("Search Results (Example):")  # Replace with actual search results processing

# Reorder Missing Parts section
st.write("### Re-Order Missing Parts")
with st.form("manual_reorder_form"):
    part_number = st.text_input("Part Number")
    description = st.text_input("Description")
    requester_name = st.text_input("Requester Name")
    submit_reorder = st.form_submit_button("Submit Re-Order")
    if submit_reorder:
        if part_number and description and requester_name:
            reorder_item(part_number, description, requester_name)
        else:
            st.warning("Please fill in all fields before submitting.")
