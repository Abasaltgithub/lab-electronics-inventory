import streamlit as st
import requests
import re

# Cache data to avoid repeated downloading


@st.cache_data
def fetch_file_content_from_url(url):
    """Fetches content from a file URL, caches the result."""
    response = requests.get(url)
    if response.status_code == 200:
        return response.text
    else:
        return f"Failed to fetch file: {response.status_code}"

# Function to check if a line is a description


def is_description(line):
    """
    Identifies if a line is likely a component description based on common patterns.
    """
    description_patterns = [
        r'\bDESC\b', r'\bPart Description\b', r'\bCIC\b', r'\bESC\b', r'\bSC\b', r'\bCAP\b', r'\bRES\b',
        r'\bIC\b', r'\bLED\b', r'\bDIODE\b', r'\bMOSFET\b', r'\bREF DES\b', r'\bTEST POINT\b',
        r'\bSCHOTTKY\b', r'\bARRAY\b', r'\bREG LINEAR\b', r'\bPOS ADJ\b',
        # New patterns for optical elements
        r'\bLENS\b', r'\bCHROMA\b', r'\bASPHERE\b', r'\bPRISM\b', r'\bOPTICS\b',
    ]
    description_regex = re.compile(
        '|'.join(description_patterns), re.IGNORECASE)
    return bool(description_regex.search(line))

# Helper function to search within blocks of text


def search_in_blocks(blocks, search_patterns, search_by_name, location):
    """Searches for part numbers and descriptions in blocks of text."""
    results = []

    for block in blocks:
        if not block.strip():
            continue

        # If we're searching by name, include all blocks; otherwise, check patterns
        if search_by_name or all(pattern.search(block) for pattern in search_patterns):
            # Extract part number
            part_number_match = re.search(
                r'(?:Lot #|P/N|N):\s*([A-Za-z0-9\-\/# ]+)', block, re.IGNORECASE)

            # Try to find description
            desc_match = re.search(r'DESC:\s*(.*)', block, re.IGNORECASE)
            if not desc_match:
                block_lines = block.splitlines()
                for i, line in enumerate(block_lines):
                    if is_description(line):
                        desc_match = line.strip()
                        # If description is "CHROMA", append the next two lines if available
                        if "CHROMA" in desc_match.upper() and i + 2 < len(block_lines):
                            desc_match += " " + \
                                block_lines[i + 1].strip() + \
                                block_lines[i + 2].strip()
                        break

            # If part number is not found, use "P/N not detected"
            part_number = part_number_match.group(
                1) if part_number_match else "P/N not detected"
            value = desc_match if isinstance(
                desc_match, str) else "Description not available"

            # Append result with location
            results.append({"Part Number": part_number,
                           "Description": value, "Location": location})

    return results

# Main function to search files


def search_file(part_number_query, value_query):
    urls = {
        'workshop': 'https://firebasestorage.googleapis.com/v0/b/aharonilabinventory.appspot.com/o/extracted_texts_Workshop.txt?alt=media&token=8e13dd3c-3c8a-4bdd-80ac-c33d6aae6d39',
        'federico': 'https://firebasestorage.googleapis.com/v0/b/aharonilabinventory.appspot.com/o/extracted_texts_Federico.txt?alt=media&token=134d8ab3-afe3-4920-92ab-6051efdd0cf7',
        'federico_printer_room': 'https://firebasestorage.googleapis.com/v0/b/aharonilabinventory.appspot.com/o/extracted_texts_Federico_printer_room.txt?alt=media&token=9609fca0-02fa-450c-b980-e47a5012b316',
        'marcel': 'https://firebasestorage.googleapis.com/v0/b/aharonilabinventory.appspot.com/o/extracted_texts_Marcel.txt?alt=media&token=c6e8decd-ec31-4d87-a4d7-b62dca6b7ca4',
        'hemal': 'https://firebasestorage.googleapis.com/v0/b/aharonilabinventory.appspot.com/o/extracted_texts_Hemal.txt?alt=media&token=b55bd4bc-a545-4c7b-9eb8-ab8afd99c3a6',
        'abasalt': 'https://firebasestorage.googleapis.com/v0/b/aharonilabinventory.appspot.com/o/extracted_texts_Abasalt.txt?alt=media&token=0c2d0e64-a0cb-4108-b87f-c97d7d858447',
    }

    # Prepare search patterns
    search_patterns = []
    if part_number_query:
        search_patterns.append(re.compile(
            rf'{re.escape(part_number_query)}(-ND)?', re.IGNORECASE))
    if value_query:
        search_patterns.append(re.compile(
            rf'\b{re.escape(value_query)}\b', re.IGNORECASE))

    # Determine if searching by name
    search_by_name = value_query.lower() in urls

    if search_by_name:
        url_to_search = {value_query.lower(): urls[value_query.lower()]}
    else:
        url_to_search = urls

    results = []

    # Search all files or the specific file
    for name, url in url_to_search.items():
        file_content = fetch_file_content_from_url(url)
        if not file_content.startswith("Failed to fetch"):
            blocks = file_content.split("Image:")
            results.extend(search_in_blocks(
                blocks, search_patterns, search_by_name, name.capitalize()))

    return results


# Streamlit Web App Interface
st.title("Component Search Tool")

# Input fields
part_number_query = st.text_input("Enter part number:")
value_query = st.text_input("Enter component name/value:")

# Trigger search
if st.button("Search"):
    if part_number_query or value_query:
        results = search_file(part_number_query, value_query)

        # Display results
        if results:
            st.write(f"Search completed. Found {len(results)} items.")
            st.table(results)  # Display as a table for better readability
        else:
            st.write("No matches found.")
    else:
        st.write("Please enter a part number or component name to search.")
