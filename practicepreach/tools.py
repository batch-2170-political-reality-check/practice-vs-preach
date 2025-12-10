import requests, os, time, csv, sys
import BundestagsAPy
import pandas as pd
import xmltodict
import xml.etree.ElementTree as ET
import time
from practicepreach.rag import Rag

from practicepreach.params import *
from practicepreach.constants import *

require_env("SPEECHES_XML_DIR")
SPEECHES_XML_DIR = os.environ.get("SPEECHES_XML_DIR")

BASE = "https://search.dip.bundestag.de/api/v1"

def process_bundestag_xml(url: str, df: pd.DataFrame):
    """
    Process speeches xml file and store data to pandas DataFrame
    """
    tree = ET.parse(url)
    root = tree.getroot()

    a_date = root.attrib['sitzung-datum']

    # path: <dbtplenarprotokoll>/<sitzungsverlauf>/<tagesordnungspunkt>/<rede>
    for punkt in root.findall("./sitzungsverlauf/tagesordnungspunkt"):
        for rede in punkt.findall("./rede"):
            rede_id = rede.get("id")  # e.g. "ID214400100"

            fraktion = rede.find(".//p[@klasse='redner']//fraktion")
            if fraktion is not None:
                main_text = rede.findall(".//p[@klasse='J_1']")[0].text

                df.loc[len(df)] = {'type':'speech', \
                        'date': a_date, \
                        'id':rede_id, \
                        'party':fraktion.text, \
                        'text':main_text}

                for node in rede.findall(".//p[@klasse='J']"):
                    df.loc[len(df)] = {'type':'speech', \
                          'date': a_date, \
                          'id':rede_id, \
                          'party':fraktion.text, \
                          'text':node.text}

def fetch_and_parse_xml(url: str, store_it_to: str = None) -> dict:
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
    if store_it_to is not None:
        os.makedirs(store_it_to, exist_ok=True)
        filename = url.split("/")[-1]
        filepath = os.path.join(store_it_to, filename)
        print(f"Storing XML to {filepath}...")
        with open(filepath, "wb") as f:
            f.write(response.content)
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

def get_speeches(speeches_urls: str, speeches_csv: str):

    df = pd.DataFrame({
        'type': pd.Series(dtype='object'),
        'date': pd.Series(dtype='object'),
        'id': pd.Series(dtype='object'),
        'party': pd.Series(dtype='object'),
        'text': pd.Series(dtype='object')
    })

    all_urls = pd.read_csv(urls).iloc[:,0]

    for url in all_urls:
        xml_data = fetch_and_parse_xml(speeches_urls, SPEECHES_XML_DIR)
        data = xml_data["dbtplenarprotokoll"]["@sitzung-datum"]

        for party in PARTIES_LIST:
            sp_list = get_speeches_by_fraktion(xml_data, party)

            for speech in sp_list:
                text = extract_speech_text(speech)
                speaker_info = get_speaker_info(speech)
                df = pd.concat([df, pd.DataFrame([{
                    'type':'speech',
                    'date': data,
                    'id': speech.get('@id', ''),
                    'party': speaker_info.get('fraktion', ''),
                    'text': text
                }])], ignore_index=True)

    df.to_csv(speeches_csv)

if __name__ == "__main__":
    if len(sys.argv) > 2 and (os.path.isfile(sys.argv[2]) or os.path.isdir(sys.argv[2])):
        if sys.argv[1] == "speeches":
            print("Getting speeches...")
            get_speeches(sys.argv[2], sys.argv[3])
        elif sys.argv[1] == "vectorize":
            file_to_process = sys.argv[2]
            print(f"Vectorizing {file_to_process}...")
            time.sleep(2)
            rag = Rag()
            print(f'{rag.get_num_of_vectors()} vectors currently in the vector store.')
            time.sleep(2)
            num_of_chunks = rag.add_to_vector_store(data_source=file_to_process)
            print(f"Embedded {num_of_chunks} chunks into the vector store.")
            print(f'{rag.get_num_of_vectors()} vectors currently in the vector store.')
        elif sys.argv[1] == "xml":
            dir_to_process = sys.argv[2]
            save_to_cvs = sys.argv[3]

            entries = os.listdir(dir_to_process)
            files = [os.path.join(dir_to_process, f) \
                    for f in entries if os.path.isfile(os.path.join(dir_to_process, f))]
            df = pd.DataFrame(columns = ['date','id','party','text'])
            for file in files:
                print(f'Processing {file}')
                process_bundestag_xml(file, df)
            df.to_csv(save_to_cvs)
