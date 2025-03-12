import os
import re
import requests
import time
from ..base_grabber import BaseGrabber
from bs4 import BeautifulSoup
from datetime import datetime
from typing import List

class AllrisGrabberV4():
    def __init__(self, entry_point: str, base_directory: str):
        self.entry_point = entry_point
        self.base_directory = base_directory



    def extract_session_links(self, content: str) -> List[str] | None:
        # Saves the list of urls to the sessions
        session_links_list = []
        
        soup = BeautifulSoup(content, 'html.parser')
        table_element = soup.find("table", {"id": "id2a"})
        
        if table_element is None:
            return None
    
        tbody_element = table_element.find("tbody")

        if tbody_element is None:
            return None
    
        tr_elements = tbody_element.find_all("tr")

        if tr_elements is None:
            return None
    
        for tr_element in tr_elements:
            td_elements = tr_element.find_all("td")
    
            if len(td_elements) != 4:
                continue
    
            a_element = td_elements[2].find("a")
    
            if not a_element:
                continue
    
            try:
                session_links_list.append(a_element["href"])
            except Exception:
                pass
    
        return session_links_list


    
    def download_session(self, url_to_session: str) -> None:

        assert url_to_session != "", "No url to a session webpage was given."

        # Extract the session number from the url as a unique id
        try:
            match = re.search(r'(?<=SILFDNR=)[0-9]*', url_to_session)
            directory_id = match.group()
            
        except Exception:
            raise BaseException("Es konnte aus der ID kein Verzeichnisname ermittelt werden!")


         # Sets the constants of the directory_path and file paths
        DIRECTORY_PATH = f'{self.base_directory}/rawdata/session_data/{directory_id}/'
        WEBPAGE_PATH = f'{DIRECTORY_PATH}session.html'
        SESSION_DATA_FILE = f'{DIRECTORY_PATH}session.json'
    
        # Creates the directory for the content of the session
        if not os.path.exists(DIRECTORY_PATH):
            os.makedirs(DIRECTORY_PATH)
        
        MAXIMAL_DOWNLOAD_ATTEMPTS = 3
        content = None
    
        # Try to download the session webpage
        for attempts in range(MAXIMAL_DOWNLOAD_ATTEMPTS):
            try:
                response = requests.get(url_to_session)

                if response.status_code != 200:
                    time.sleep(MAXIMAL_DOWNLOAD_ATTEMPTS * 60)
                    continue
                    
                content = response.text
                break
            except Exception:
                # Wait a calculated time until the next try
                time.sleep(MAXIMAL_DOWNLOAD_ATTEMPTS * 60)
    
        if content is None:
            raise BaseException(f"Die Webseite der Sitzung mit der URL {url_to_session} konnte nicht heruntergeladen werden!")
        

        # Creates the data structure to save the source information
        data = {
                "source": {
                           "link": url_to_session,
                           "retrival date": str(datetime.now().timestamp())
                         },
                "documents": []
               }
    

        file_links = []

        # Extract the file links from the session page
        soup = BeautifulSoup(content, 'html.parser')
        aside_element = soup.find("aside", {"id":"dokumenteHeaderPanel"})

        if aside_element is None:
            link_elements = []
        else:
            link_elements = aside_element.find_all("a",{"class":"js-simple-tooltip doclink pdf"})

        for link_element in link_elements:
            file_links.append(link_element["href"])

        # Downloads the extracted files of the session
        for file_link in file_links:
            filename, sha256_checksum = BaseGrabber.download_file(DIRECTORY_PATH, f'{file_link}')

            # Adds the information of the file to the data object of the session
            data["documents"].append({"filename": filename, "sha256-checksum": sha256_checksum})


        # Saves the webpage and the metadata file
        try:
            BaseGrabber.save_webpage(WEBPAGE_PATH, content)
            BaseGrabber.save_jsonfile(SESSION_DATA_FILE, data)
        
        except Exception:
            pass



    def get_all_proposals(self) -> List[str]:
        BASE_SESSION_DIRECTORY = f'{self.base_directory}/rawdata/session_data/'

        proposal_links = []
    
        for directory in os.listdir(BASE_SESSION_DIRECTORY):
            # Pass the further processing if directory is a file
            if not os.path.isdir(f"{BASE_SESSION_DIRECTORY}/{directory}"):
                continue

            SESSION_WEBPAGE_PATH = f'{BASE_SESSION_DIRECTORY}{directory}/session.html'
    
            # Guard if the webpage file does not exists
            if not os.path.isfile(SESSION_WEBPAGE_PATH):
                continue
    
            with open(SESSION_WEBPAGE_PATH, 'r') as handler:
                content = handler.read()

            soup = BeautifulSoup(content, 'html.parser')

            tr_elements = soup.find_all("tr", {"class":re.compile("(odd|even) (numodd|numeven).*")})

            for tr_element in tr_elements:
                td_element = tr_element.find("td", {"class":"tovonr"})

                if td_element is None:
                    continue

                link_elements = td_element.find_all("a")

                for link_element in link_elements:
                    if link_element.get_text() == "":
                        continue
                        
                    proposal_links.append(link_element["href"])


        # Filters the duplicates out of the url list
        proposal_links = list(set(proposal_links))

        return proposal_links


    
    def download_proposal(self, url_to_proposal) -> None:
         # Extract the proposal number from the url as a unique id
        match = re.search(r'(?<=VOLFDNR=)[0-9]*', url_to_proposal) 

        if match is None:
            raise BaseException("Download keine eindeutige ID in URL gefunden!")
        
        directory_id = match.group()
    
        
        ## Sets the constants of the directory_path and file paths
        DIRECTORY_PATH = f'{self.base_directory}/rawdata/proposal_data/{directory_id}'
        WEBPAGE_PATH = f'{DIRECTORY_PATH}/proposal.html'
        PROPOSAL_DATA_FILE = f'{DIRECTORY_PATH}/proposal.json'
        
        # Creates the directory for the content of the proposal
        if not os.path.exists(DIRECTORY_PATH):
            os.makedirs(DIRECTORY_PATH)
    
        MAXIMAL_DOWNLOAD_ATTEMPTS = 3
        content = None
    
        # Try to download the session webpage
        for attempts in range(MAXIMAL_DOWNLOAD_ATTEMPTS):
            try:
                response = requests.get(url_to_proposal)

                if response.status_code != 200:
                    time.sleep(MAXIMAL_DOWNLOAD_ATTEMPTS * 60)
                    continue
                    
                content = response.text
                break
            except Exception:
                # Wait a calculated time until the next try
                time.sleep(MAXIMAL_DOWNLOAD_ATTEMPTS * 60)
    
        if content is None:
            raise BaseException(f"Die Webseite des Antrags mit der URL {url_to_proposal} konnte nicht heruntergeladen werden!")
    
        
        # Creates the data structure to save the source information
        data = {
                "source": {
                           "link": url_to_proposal,
                           "retrival date": str(datetime.now())
                         }
               }
    
        data["documents"] = []

        file_links = []
        
        soup = BeautifulSoup(content, 'html.parser')
        aside_element = soup.find("aside", {"id":"dokumenteHeaderPanel"})

        if aside_element is None:
            link_elements = None
        else:
            link_elements = aside_element.find_all("a",{"class":"js-simple-tooltip doclink pdf"})

        if link_elements is None:
            link_elements = []

        for link_element in link_elements:
            if link_element.get_text() == "Sammeldokument":
                continue
                
            file_links.append(link_element["href"])

        
        # Downloads the extracted files of the session
        for file_link in file_links:
            filename, sha256_checksum = BaseException.download_file(DIRECTORY_PATH, f'{file_link}')

            # Adds the information of the file to the data object of the session
            data["documents"].append({"filename": filename, "sha256-checksum": sha256_checksum})


        # Saves the webpage and the metadata file
        try:
            BaseGrabber.save_webpage(WEBPAGE_PATH, content)
            BaseGrabber.save_jsonfile(PROPOSAL_DATA_FILE, data)
        
        except Exception:
            pass