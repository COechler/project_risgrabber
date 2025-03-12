# Imports the necessary modules
import random
import re
import requests
import os
import time
from datetime import datetime
from typing import List, Tuple
from ..base_grabber import BaseGrabber
from bs4 import BeautifulSoup
from urllib.parse import urljoin


class SessionNetGrabberV6():
    def __init__(self, entry_point: str, base_directory: str):
        self.entry_point = entry_point
        self.base_directory = base_directory
    


    def get_year_range(self) -> Tuple[int, int]:
        """Discovers the year range in which sessions in the parlament information system exists. It will therefor
           read the values from the year dropdown menu of the session.net calendar view with the years.

        Returns:
          An tuple with the minmal and the maximal year. As a default backup year it will return the current year for
          minimal and maximal year.
        """
        
        minimal_year: int = datetime.now().year
        maximal_year: int = datetime.now().year

        try:
            response = requests.get(self.entry_point)
            response.raise_for_status()           
            content = response.text
        except Exception:
            return minimal_year, maximal_year

        try:
            soup = BeautifulSoup(content, 'html.parser')

        
            div_element = soup.find("div", {"class":"smcfiltermenuyear dropdown-menu dropdown-menu-right"})

            if div_element is None:
                return minimal_year, maximal_year

           
            link_elements = div_element.find_all('a')
            
            if link_elements is None:
                return minimal_year, maximal_year
        
            for link_element in link_elements:
                try:
                    value = int(link_element.get_text())
                    minimal_year = min(minimal_year, value)
                    maximal_year = max(maximal_year, value)
                except Exception:
                    continue
        except Exception:
            pass

        return minimal_year, maximal_year



    def get_all_sessions(self, **kwargs) -> List[str]:
        """Iterates through the parlament information system to get all urls
           to the sessions.
    
        Returns:
          An list with all discovered urls to the sessions.
        """

        links: List[str] = []
        
        # Discover the start and end year
        start_year, end_year = self.get_year_range()

        # Guard checks that the discovered start date is valid
        if start_year is None or start_year < 0:
            raise ValueError("Das Startjahr hat einen ungültigen Wert!")

        # Guard checks that the discovered end date is valid
        if end_year is None or end_year < 0:
            raise ValueError("Das Endjahr hat einen ungültigen Wert!")


        # Iterate through the years and month pages
        for year in range(start_year, end_year + 1):
            
            for month in range(1,13):
                # Build the url string
                url = f'{self.entry_point}?__cjahr={year}&__cmonat={month}&__canz=1&__cselect=0'

                try:
                    links.extend(self.extract_sessions_from_webpage(url))

                except Exception:
                    pass

                finally:
                    # Waits a random time to prevent DDOS protection is triggered
                    waiting_time = random.uniform(5, 20)
                    time.sleep(waiting_time)


        # Filters the duplicates out of the url list
        links = list(set(links))

        return links



    def download_session(self, url_to_session) -> None:
        """Gets the session with given url and saves the webpage in a directory.
           Additionally saves all appendix files of the session in the directory
           and creates a JSON fille with meta informationen of the session.

        Args:
           url_to_session: A url to the session in the parlament information system.
    
        Raises:
           AssertError:                     If no url was given as a parameter

           BaseException:                   If the directory id can't be extracted from the given url.

           BaseException:                   If the directory for the session can not be created
                                            If the webpage can't be downloaded.
                                            If the session content can't be saved in a file
                                            If the meta data can't be saved in a json file

           BaseException:                   If the extraction of the file links don't work in the extracting method
           
           BaseException:                   If a appendix file can't be downloaded.
        """

        # Guard to avoid that a empty url to a session is processed
        assert url_to_session != "", "No valid url was given to the method."


        
        # Extract the session number from the url as a unique id
        try:
            match = re.search(r'(?<=ksinr=)[0-9]+', url_to_session)
            directory_id = match.group()            
        except Exception as exception:
            raise BaseException(f'Fehler beim Regex-Match aufgetreten. Der Grund ist {exception}')

        
        # Sets the constants of the directory_path and file paths
        DIRECTORY_PATH = os.path.join(self.base_directory, 'rawdata', 'session_data', directory_id)
        WEBPAGE_PATH = os.path.join(DIRECTORY_PATH, 'session.html')
        SESSION_DATA_FILE = os.path.join(DIRECTORY_PATH, 'session.json')

        
        # Creates the directory for the content of the session
        try:
            os.makedirs(DIRECTORY_PATH, exist_ok=True)
        except Exception as exception:
            raise BaseException(f'Beim erstellen des Verzeichnises ist ein Fehler aufgetretten. Der Grund lautet: {exception}', url_to_session)             

        
        MAXIMAL_DOWNLOAD_ATTEMPTS = 3
    
        # Try to download the session webpage
        for attempts in range(MAXIMAL_DOWNLOAD_ATTEMPTS):
            try:
                response = requests.get(url_to_session)
                response.raise_for_status()           
                content = response.text
                break
            except Exception:
                # Wait a calculated time until the next try
                time.sleep(MAXIMAL_DOWNLOAD_ATTEMPTS * 60)
    
        if not content:
            raise BaseException("Sitzungs-Inhalt konnte nicht heruntergeladen werden.", url_to_session)
        

        # Creates the data structure to save the source information
        data = {
                "source": {
                           "link": url_to_session,
                           "retrival date": str(datetime.now().timestamp())
                         },
                "documents": []
               }

        
        # Trys to extract all links from the downloaded content of the session
        try:
            file_links = self.extract_file_links_from_session(content)
        except Exception as e:
            print(e)
            file_links = []


        # Iterates through the discovered links to download them
        for file_link in file_links:
            try:
                match = re.search(r'(?<=id=)[0-9]+', file_link)

                if match is None:
                    continue
                
                document_id = match.group()

                filename, sha256_checksum = BaseGrabber.download_file(DIRECTORY_PATH, f'{file_link}', unique_identifier=document_id)

                # Adds the information of the file to the data object of the session
                data["documents"].append({"filename": filename, "sha256-checksum": sha256_checksum})
            
            except Exception as e:
                print(e)
                print("Konnte Datei nicht runterladen")
                continue

            

        # Saves the webpage and the metadata file
        try:
            BaseGrabber.save_webpage(WEBPAGE_PATH, content)
            BaseGrabber.save_jsonfile(SESSION_DATA_FILE, data)
        
        except Exception as e:
            print(e)
            print("Konnte Datei nicht speichern")
            pass
    


    def get_all_proposals(self) -> List[str]:
        """Iterates through the saved raw data of the grabbed session webpages and
           collect all urls to a proposal in this files.
    
        Returns:
          An array with all discovered urls to the proposals.
        """
        
        BASE_SESSION_DIRECTORY = os.path.join(self.base_directory, 'rawdata', 'session_data')

        proposal_links = []
    
        for directory in os.listdir(BASE_SESSION_DIRECTORY):
            # Creates the full path to the directory with the data files of the session
            path_of_session_directory = os.path.join(BASE_SESSION_DIRECTORY, directory)
            
            # Pass the further processing if directory is a file
            if not os.path.isdir(path_of_session_directory):
                continue

            path_to_session_webpage = os.path.join(path_of_session_directory, "session.html")

    
            # Guard if the webpage file does not exists
            if not os.path.isfile(path_to_session_webpage):
                continue

            # Opens the webpage and reads the content of the file
            with open(path_to_session_webpage, 'r', encoding='utf-8') as handler:
                content = handler.read()

            proposals_of_webpage = self.extract_proposal_links_from_session(content)
            proposal_links.extend(proposals_of_webpage)

        
        # Filters the duplicates out of the url list
        proposal_links = list(set(proposal_links))
        
        return proposal_links
    


    def download_proposal(self, url_to_proposal) -> None:
        """Gets the proposal with given url and saves the webpage in a directory.
           Additionally saves all appendix files of the proposal in the directory
           and creates a JSON fille with meta informationen of the proposal.
    
        Args:
           url_to_proposal: A url to the proposal in the parlament information system.

        Raises:
           ValueError:                      If no url was given as a parameter

           NoUniqueInternalProposalIDError: If the directory id can't be extracted from the given url.

           ProposalSavingError:             If the webpage can't be downloaded.
                                            If the proposal content can't be saved in a file
                                            If the meta data can't be saved in a json file
        """

         # Guard to avoid that a empty url to a proposal is processed
        assert url_to_proposal != "", "No valid url was given to the method."
        
         # Extract the proposal number from the url as a unique id
        try:
            match = re.search(r'(?<=kvonr=)[0-9]+', url_to_proposal)            
            directory_id = match.group()
        except Exception as exception:
            print(exception)
    
        
        # Sets the constants of the directory_path and file paths
        DIRECTORY_PATH = f'{self.base_directory}/rawdata/proposal_data/{directory_id}'
        WEBPAGE_PATH = f'{DIRECTORY_PATH}/proposal.html'
        PROPOSAL_DATA_FILE = f'{DIRECTORY_PATH}/proposal.json'

        
        # Creates the directory for the content of the proposal
        try:
             os.makedirs(DIRECTORY_PATH, exist_ok=True)
        except Exception as exception:
            raise BaseException(self.identifier, f'Beim erstellen des Verzeichnises ist ein Fehler aufgetretten. Der Grund lautet: {exception}', url_to_proposal)
        
    
        MAXIMAL_DOWNLOAD_ATTEMPTS = 3
    
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

        if not content:
            raise BaseException("Der Inhalt der Vorlage konnte nicht heruntergeladen werden.", url_to_proposal)
    
        
        # Creates the data structure to save the source information
        data = {
                "source": {
                           "link": url_to_proposal,
                           "retrival date": str(datetime.now())
                         },
                 "documents": []
               }

        file_links = self.extract_file_links_from_proposal(content)

        for file_link in file_links:
            try:
                match = re.search(r'(?<=id=)[0-9]*', file_link) 

                if match is None:
                    continue
                
                document_id = match.group()

                filename, sha256_checksum = BaseGrabber.download_file(DIRECTORY_PATH, f'{file_link}', unique_identifier=document_id)
            except Exception:
                continue

            # Adds the information of the file to the data object of the session
            data["documents"].append({"filename": filename, "sha256-checksum": sha256_checksum})

        # Saves the webpage and the metadata file
        try:
            BaseGrabber.save_webpage(WEBPAGE_PATH, content)
            BaseGrabber.save_jsonfile(PROPOSAL_DATA_FILE, data)
        
        except Exception:
            pass



    
    def extract_sessions_from_webpage(self, url :str) -> List[str]:
        # Guard to avoid that a empty url to a session overview is processed
        assert url != "", "No valid url was given to the method."
  

        MAXIMAL_DOWNLOAD_ATTEMPTS = 3
            
        # Try to download the session webpage
        for attempts in range(MAXIMAL_DOWNLOAD_ATTEMPTS):
            try:
                response = requests.get(url)
                response.raise_for_status()                    
                content = response.text
            except Exception:
                    # Wait a calculated time until the next try
                    time.sleep(MAXIMAL_DOWNLOAD_ATTEMPTS * 60)
            
        if not content:
            raise BaseException('Der Inhalt der Sitzungsübernicht konnte nicht heruntergeladen werden.')
           
        soup = BeautifulSoup(content, 'html.parser')
        
        links_to_sessions: List[str] = []

        
        for tr_element in soup.find_all('tr'):
            div_element = tr_element.find('div', {"class": "smc-el-h"})
                        
            if div_element is None:
                continue
             
            link_element = div_element.find('a', {"class": "smce-a-u smc-link-normal smc_doc smc_datatype_si"})
                
            if link_element is None:
                continue
                
            url_to_session = urljoin(self.entry_point, link_element["href"])
            links_to_sessions.append(url_to_session)
        

        return links_to_sessions



    def extract_file_links_from_session(self, content: str) -> List[str] | None:
        # Guard to prevent that a empty content is processed
        assert content != "", "The content should not be empty."

        soup = BeautifulSoup(content, 'html.parser')

        div_element = soup.find('div',{"class": "smc-dg-c-1-10 smc-documents smc-pr-n row"})

        if div_element is None:
            return None

        link_elements = div_element.find_all("a", {"class": "smce-a-u smc-link-normal smc_datatype_do smc-t-r991"})
        

        if link_elements is None:
            return None
        
        file_links: List[str] = []

        for link_element in link_elements:
            
            # Guard if link element has no key href
            if "href" not in link_element.attrs.keys():
                continue

    
            file_link = urljoin(self.entry_point, link_element["href"])
            file_links.append(file_link)
        
        # Remove the duplicated links
        file_links = list(set(file_links))

        return file_links



    def extract_proposal_links_from_session(self, content: str) -> List[str] | None:
        proposal_links: List[str] = []
        
        # Initialize the parser for the webpage
        soup = BeautifulSoup(content, 'html.parser')

        tr_element_list = soup.find_all('tr', {"class": "smc-t-r-l"})

        if tr_element_list is None:
            return None

        for tr_element in tr_element_list:
            try:
                if tr_element is None:
                    continue
                    
                link_element = tr_element.find('a',{"class": "smce-a-u smc-link-procedure smc_doc smc_field_voname smcnowrap smc_datatype_vo"})
                    
                if link_element is None:
                    continue
                    
                url_to_proposal = urljoin(self.entry_point, link_element["href"])
            
                proposal_links.append(url_to_proposal)
        
            
            except Exception as e:
                print(e)

        return proposal_links
    


    def extract_file_links_from_proposal(self, content: str) -> List[str] | None:
        # Guard to prevent that a empty content is processed
        assert content != "", "The content should not be empty."

        soup = BeautifulSoup(content, 'html.parser')

        div_element = soup.find('div',{"class": "smc-dg-c-1-10 smc-documents smc-pr-n row"})

        if div_element is None:
            return None

        link_elements = div_element.find_all("a", {"class": "smce-a-u smc-link-normal smc_datatype_do smc-t-r991"})
        

        if link_elements is None:
            return None
        
        file_links: List[str] = []

        for link_element in link_elements:
            
            # Guard if link element has no key href
            if "href" not in link_element.attrs.keys():
                continue

    
            file_link = urljoin(self.entry_point, link_element["href"])
            file_links.append(file_link)
        
        # Remove the duplicated links
        file_links = list(set(file_links))

        return file_links
