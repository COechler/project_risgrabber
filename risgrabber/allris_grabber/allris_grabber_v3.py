import os
import random
import re
import requests
import time
from ..base_grabber import BaseGrabber
from bs4 import BeautifulSoup
from datetime import datetime
from typing import List, Tuple
from urllib.parse import urljoin

#https://ksd.rostock.de/bi/vo020?VOLFDNR=1028154&refresh=false
class AllrisGrabberV3():
    def __init__(self, entry_point: str, base_directory: str):
        self.entry_point = entry_point
        self.base_directory = base_directory
    
    def __get_year_range(self, url: str | None = None, mode=None) -> Tuple[int, int]:
        if url is None:
            url = self.entry_point
        
        minimal_year = datetime.now().year
        maximal_year = datetime.now().year
        
        response = requests.get(url)
        response.raise_for_status()           
        content = response.text
    
        soup = BeautifulSoup(content, 'html.parser')
    
        table_element_first = soup.find("table", {"class": "risdeco"})
    
        if not table_element_first:
            raise ValueError("Erstes Tabellen-Element konnte nicht gefunden werden!")
    
        table_element_second = table_element_first.find_all("table")
    
        if not table_element_second:
            raise ValueError("Die weiteren Tabellen-Element konnte nicht gefunden werden!")
    
        tr_elements = table_element_second[1].find_all("tr")
    
        if not tr_elements:
            raise ValueError("Es konnten keine Tabellen-Reihen gefunden werden!")
    
        td_elements = tr_elements[0].find_all("td")
    
        previous_url = None
        next_url = None
    
        for td_element in td_elements[1:8]:
            
            field_text = td_element.get_text().strip()
    
            if field_text == "<<":
                a_element = td_element.find("a")
                previous_url = urljoin(self.entry_point, a_element["href"])
            elif field_text == ">>":
                a_element = td_element.find("a")
                next_url = urljoin(self.entry_point, a_element["href"])
            elif field_text == "":
                continue
            else:
                minimal_year = min(minimal_year, int(field_text))
                maximal_year = max(maximal_year, int(field_text))
    
        if previous_url and (mode is None or mode == "prev"):
            min_year, max_year = self.__get_year_range_v3(previous_url, "prev")
            minimal_year = min(minimal_year, min_year)
            maximal_year = max(maximal_year, max_year)
    
        if next_url and (mode is None or mode == "next"):
            min_year, max_year = self.__get_year_range_v3(next_url, "next")
            minimal_year = min(minimal_year, min_year)
            maximal_year = max(maximal_year, max_year)
    
        return minimal_year, maximal_year
    
    
    
    def extract_session_links(self,url: str) -> List[str]:
        # Saves the list of urls to the sessions
        session_links_list = []
        
        response = requests.get(url)
        response.raise_for_status()           
        content = response.text
        
        soup = BeautifulSoup(content, 'html.parser')
        tr_elements = soup.find_all("tr", class_=re.compile("(zl11|zl12)", re.I))
    
        for tr_element in tr_elements:
            
            td_elements = tr_element.find_all("td")
    
            if not td_elements:
                continue
    
            if len(td_elements) != 8:
                continue
    
            a_element = td_elements[5].find("a")
    
            if a_element:
                # Build the complete url string
                url_to_session = urljoin(self.entry_point, a_element["href"])
                
                # Saves the url string in the list
                session_links_list.append(url_to_session)
    
        return session_links_list
    
    
    
    def get_all_sessions(self) -> List[str]:
        # Gets the start and end year
        start_year, end_year = self.__get_year_range()

        print(start_year)
        print(end_year)
    
        # Saves the links of the session pages
        links_of_session_pages = []
    
        for year in range(start_year, end_year + 1):
            for month in range(1,13):
                # Build the url string of the calendar pages
                url = f'{self.entry_point}?MM={month}&YY={year}'
    
                try:
                    # Extracts the links to the session from the calendar page
                    links_of_session_pages.extend(self.__extract_session_links_v3(url))
                except Exception:
                    print("Fehler passiert!")
    
                finally:
                    # Waits a random time to prevent DDOS protection is triggered
                    waiting_time = random.uniform(5, 20)
                    time.sleep(waiting_time)
                
        
        # Filters the duplicates out of the url list
        links_of_session_pages = list(set(links_of_session_pages))
        
        return links_of_session_pages
    
    
    
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
            filename, sha256_checksum = super().download_file(DIRECTORY_PATH, f'{file_link}')

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
        # Guard to prevent processing of a empty url
        assert url_to_proposal != "", "Es wurde keine URL der Vorlage angegeben."

         # Extract the proposal number from the url as a unique id
        match = re.search(r'(?<=VOLFDNR=)[0-9]*', url_to_proposal) 

        if match is None:
            raise BaseException("Beim Download der Vorlage konnte keine eindeutige ID aus der URL extrahiert werden.")
        
        directory_id = match.group()
    
        
        # Sets the constants of the directory_path and file paths
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
                response.raise_for_status()
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
                         },
                "documents": []
               }
    

        file_links: List[str] = []
        
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

        
        aside_element = soup.find("aside", {"id":"anlagenHeaderPanel"})

        if aside_element is None:
            link_elements = None
        else:
            link_elements = aside_element.find_all("a",{"class":"js-simple-tooltip attlink pdf"})

        if link_elements is None:
            link_elements = []

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
            BaseGrabber.save_jsonfile(PROPOSAL_DATA_FILE, data)
        
        except Exception:
            pass