import requests, os, time, csv, sys
import BundestagsAPy
import pandas as pd
import xmltodict

from practicepreach.params import *

PARTIES_LIST = ["AfD", "SPD", "CDU/CSU", "BÜNDNIS 90/DIE GRÜNEN", "Die Linke"]
BASE = "https://search.dip.bundestag.de/api/v1"

def fetch_and_parse_xml(url: str) -> dict:
    """
    Fetch XML from URL and parse it into a dictionary using xmltodict.
    Args:
        url: URL of the XML file
    Returns:
        Dictionary representation of the XML
    """
    print(f"Fetching XML from {url}...")
    response = requests.get(url)
    response.raise_for_status()

    print("Parsing XML with xmltodict...")
    xml_dict = xmltodict.parse(response.content)

    return xml_dict

def get_speeches_by_fraktion(xml_data: dict, fraktion: str) -> list:
    """
    Retrieve all speeches by speakers from a specific party (fraktion).
    Args:
        xml_data: The parsed XML dictionary
        fraktion: The party name (e.g., "AfD", "SPD", "CDU/CSU", "BÜNDNIS 90/DIE GRÜNEN", "Die Linke")
    Returns:
        List of speech dictionaries from speakers of the specified party
    """
    speeches = []

    def find_speeches_recursive(obj):
        """Recursively find all rede (speech) elements."""
        if isinstance(obj, dict):
            # Check if this is a rede element
            if '@id' in obj and obj.get('@id', '').startswith('ID'):
                # This looks like a speech element
                # Check if it has a speaker with the matching fraktion
                if 'p' in obj:
                    paragraphs = obj['p'] if isinstance(obj['p'], list) else [obj['p']]
                    for para in paragraphs:
                        if isinstance(para, dict) and 'redner' in para:
                            redner = para['redner']
                            if isinstance(redner, dict) and 'name' in redner:
                                name_info = redner['name']
                                if isinstance(name_info, dict) and name_info.get('fraktion') == fraktion:
                                    speeches.append(obj)
                                    break

            # Recursively search all values
            for value in obj.values():
                find_speeches_recursive(value)

        elif isinstance(obj, list):
            for item in obj:
                find_speeches_recursive(item)

    find_speeches_recursive(xml_data)
    return speeches


def extract_speech_text(speech_dict: dict) -> str:
    """
    Extract ONLY the actual speech text content (#text fields) from paragraphs.
    Excludes speaker info, XML structure markers, and metadata.
    This is what gets embedded - metadata is stored separately for filtering.
    Args:
        speech_dict: Dictionary containing speech data
    Returns:
        String containing only the speech text content (no metadata)
    """
    # Only extract #text from paragraphs, excluding speaker introductions
    text_parts = []

    if 'p' in speech_dict:
        paragraphs = speech_dict['p'] if isinstance(speech_dict['p'], list) else [speech_dict['p']]

        for para in paragraphs:
            if isinstance(para, dict):
                # Skip paragraphs that contain speaker info (redner key)
                if 'redner' in para:
                    continue

                # Only extract #text content
                if '#text' in para:
                    text = para['#text'].strip()
                    # Filter out empty text and XML class markers
                    if text and len(text) > 0:
                        text_parts.append(text)

    # Join all text parts with spaces
    return ' '.join(text_parts)


def get_speaker_info(speech_dict: dict) -> dict:
    """
    Extract speaker information from a speech.

    Args:
        speech_dict: Dictionary containing speech data

    Returns:
        Dictionary with speaker information (name, fraktion, etc.)
    """
    if 'p' in speech_dict:
        paragraphs = speech_dict['p'] if isinstance(speech_dict['p'], list) else [speech_dict['p']]
        for para in paragraphs:
            if isinstance(para, dict) and 'redner' in para:
                redner = para['redner']
                if isinstance(redner, dict) and 'name' in redner:
                    name_info = redner['name']
                    return {
                        'titel': name_info.get('titel', ''),
                        'vorname': name_info.get('vorname', ''),
                        'nachname': name_info.get('nachname', ''),
                        'fraktion': name_info.get('fraktion', '')
                    }
    return {}

def get_speeches():
    client = BundestagsAPy.Client(BUNDESTAG_API_KEY)

    protocols = client.bt_plenarprotokoll(
        start_date="2025-01-01",
        end_date="2025-12-01",
        max_results=False
    )

    df = pd.DataFrame({
        'date': pd.Series(dtype='object'),
        'id': pd.Series(dtype='object'),
        'party': pd.Series(dtype='object'),
        'text': pd.Series(dtype='object')
    })

    all_urls = pd.read_csv(SPEECHES_URLS).iloc[:,0]

    for url in all_urls:
        xml_data = fetch_and_parse_xml(url)
        data = xml_data["dbtplenarprotokoll"]["@sitzung-datum"]

        for party in PARTIES_LIST:
            sp_list = get_speeches_by_fraktion(xml_data, party)

            for speech in sp_list:
                text = extract_speech_text(speech)
                speaker_info = get_speaker_info(speech)
                df = pd.concat([df, pd.DataFrame([{
                    'date': data,
                    'id': speech.get('@id', ''),
                    'party': speaker_info.get('fraktion', ''),
                    'text': text
                }])], ignore_index=True)

    df.to_csv(SPEECHES_CSV)

def url_collector(wahlperiode=20, start_num=1, stop_num=214, start_id=866350):

    wierd_id = start_id
    num = start_num
    in_order = True
    url_list = []

    while True:

        if num > stop_num:
            break

        url = f"https://www.bundestag.de/resource/blob/{wierd_id}/{wahlperiode:02d}{num:03d}.xml"
        plus_one_url = f"https://www.bundestag.de/resource/blob/{wierd_id}/{wahlperiode:02d}{num+1:03d}.xml"

        response = requests.get(url)
        if response.status_code == 200:
            url_list.append(url)
            print(f"Adding {url}")
            if in_order:
                num += 1
            else:
                in_order = True
                num += 2
        elif in_order:
            response = requests.get(plus_one_url)
            if response.status_code == 200:
                url_list.append(plus_one_url)
                print(f"Adding {plus_one_url}")
                in_order = False

        wierd_id += 1

    return url_list

if __name__ == "__main__":
    if len(sys.argv) > 1:
        if sys.argv[1] == "speeches":
            print("Getting speeches...")
            get_speeches()
        elif sys.argv[1] == "collect":
            print("Collecting urls...")
            url_list = url_collector()
            with open('speaches_test.csv', 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(url_list)
