import streamlit as st
import requests
import re

# Function to fetch file content from a URL


def fetch_file_content_from_url(url):
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
        r'\bDESC\b',
        r'\bPart Description\b',
        r'\bCIC\b',
        r'\bESC\b',
        r'\bSC\b',
        r'\bCAP\b',
        r'\bRES\b',
        r'\bIC\b',
        r'\bLED\b',
        r'\bDIODE\b',
        r'\bMOSFET\b',
        r'\bREF DES\b',
        r'\bTEST POINT\b',
        r'\bSCHOTTKY\b',
        r'\bARRAY\b',
        r'\bREG LINEAR\b',
        r'\bPOS ADJ\b',
        r'\bLENS\b',
        r'\bCHROMA\b',
        r'\bASPHERE\b',
        r'\bPRISM\b',
        r'\bOPTICS\b',
    ]
    description_regex = re.compile(
        '|'.join(description_patterns), re.IGNORECASE)
    return bool(description_regex.search(line))

# Helper function to search within blocks of text


def search_in_blocks(blocks, search_patterns, search_by_name, location):
    results = []

    for block in blocks:
        if not block.strip():
            continue

        # If we're searching by name, include all blocks, else apply patterns
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
            if not part_number_match:
                part_number = f"P/N not detected"
            else:
                part_number = part_number_match.group(1)

            value = desc_match if isinstance(desc_match, str) else (
                desc_match.group(1) if desc_match else "Description not available")

            # Append result with location (instead of image name)
            results.append({"part_number": part_number,
                           "value": value, "location": location})

    return results

# Main function to search files


def search_file(part_number_query, value_query):
    urls = {
        'workshop': 'https://firebasestorage.googleapis.com/v0/b/aharonilabinventory.appspot.com/o/extracted_texts_Workshop.txt?alt=media&token=4c67ff8b-f207-4fec-b585-c007518bb976',
        'federico': 'https://firebasestorage.googleapis.com/v0/b/aharonilabinventory.appspot.com/o/extracted_texts_Federico.txt?alt=media&token=ee37dbb4-44c8-4a82-8ceb-7c9ce8859688',
        'marcel': 'https://firebasestorage.googleapis.com/v0/b/aharonilabinventory.appspot.com/o/extracted_texts_Marcel.txt?alt=media&token=0e9da0d2-8f8f-451d-9108-4e2283634894'
    }

    # Prepare search patterns
    search_patterns = []
    if part_number_query:
        search_patterns.append(re.compile(
            rf'{re.escape(part_number_query)}(-ND)?', re.IGNORECASE))
    if value_query:
        search_patterns.append(re.compile(
            rf'\b{re.escape(value_query)}\b', re.IGNORECASE))

    # If searching by name (e.g., "marcel"), restrict to that file
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
            for result in results:
                st.write(
                    f"**Part Number**: {result['part_number']} | **Description**: {result['value']} | **Location**: {result['location']}")
        else:
            st.write("No matches found.")
    else:
        st.write("Please enter a part number or component name to search.")
