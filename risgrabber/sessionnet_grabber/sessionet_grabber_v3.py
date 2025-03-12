import re
import requests
import os
import time
import random

from datetime import datetime
from ..base_grabber import BaseGrabber
from bs4 import BeautifulSoup
from typing import List, Tuple
from urllib.parse import urljoin


class SessionNetGrabberV3():
    def __init__(self, entry_point: str, base_directory: str):
        self.entry_point = entry_point
        self.base_directory = base_directory

    

    def get_year_range(self, entry_point: str) -> Tuple[int, int]:
        """Discovers the year range in which sessions in the parlament information system exists. It will therefor
           read the values from the year dropdown menu of the session.net calendar view with the years.

        Returns:
          An tuple with the minmal and the maximal year. As a default backup year it will return the current year for
          minimal and maximal year.
        """
        
        minimal_year = datetime.now().year
        maximal_year = datetime.now().year

        try:
            response = requests.get(entry_point)
            response.raise_for_status()           
            content = response.text
        except Exception:
            return minimal_year, maximal_year

        try:
            soup = BeautifulSoup(content, 'html.parser')

            link_elements = None
            
            if soup.find("div", {"class":"smcfiltermenuyear dropdown-menu dropdown-menu-right"}) is not None:
                div_element = soup.find("div", {"class":"smcfiltermenuyear dropdown-menu dropdown-menu-right"})

                if div_element is not None:
                    link_elements = div_element.find_all('a')
            
            elif soup.find("ul", {"class":"smcfiltermenuyear"}) is not None:
                ul_element = soup.find("ul", {"class":"smcfiltermenuyear"})

                if ul_element is not None:
                    link_elements = ul_element.find_all('a', {"class": "smce-a-u nav-link smcfiltermenuyear"})

            
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
    
        Raises:
          AssertError:                     If the method is called with the wrong layout version of SessionNet

          ValueError:                      If the start or end year has an invalid value
        """

        # Guard to avoid that this function is used by the wrong layout version
        assert self.__layout_version == "layout-6", "Method is not compatible with the discovered layout version of SessionNet"

        links: List[str] = []
        
        # Discover the start and end year
        start_year, end_year = self.__get_year_range_v6()

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
                    links.extend(self.__get_sessions_from_webpage_v6(url))
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
        """Gets the session with given url and saves the webpage (JSON) in a directory.
           Additionally saves all appendix files of the session in the directory
           and creates a JSON fille with meta informationen of the session.

        Args:
           url_to_session: A url to the session in the parlament information system.
    
        Raises:         
           BaseException: If the directory id can't be extracted from the given url.
                          If the webpage can't be downloaded.
                          It a appendix file can't be downloaded.
                          If the raw webpage (JSON) can't be saved
                          If the JSON file with the meta information of the session can't be saved.
        """
        
        # Guard to avoid that a empty url to a session is processed
        assert url_to_session != "", "No valid url was given to the method."


        # Extract the session number from the url as a unique id
        try:
            match = re.search(r'(?<=ksinr=)[0-9]+', url_to_session)
            directory_id = match.group()
        except Exception:
            raise BaseException("Es konnte aus der ID kein Verzeichnisname ermittelt werden!")

        
        # Sets the constants of the directory_path and file paths
        DIRECTORY_PATH = f'{self.base_directory}/rawdata/session_data/{directory_id}/'
        WEBPAGE_AGENDA_PATH = f'{DIRECTORY_PATH}session-agenda.html'
        WEBPAGE_INFO_PATH = f'{DIRECTORY_PATH}session-info.html'
        SESSION_DATA_FILE = f'{DIRECTORY_PATH}session.json'

        
        # Creates the directory for the content of the session
        try:
            os.makedirs(DIRECTORY_PATH, exist_ok=True)
        except Exception as exception:
            raise BaseException(self.identifier, f'Beim erstellen des Verzeichnises ist ein Fehler aufgetretten. Der Grund lautet: {exception}', url_to_session)  
        
        
        url_agenda_page = url_to_session
        url_info_page = urljoin(url_to_session, f'si0050.asp?__ksinr={directory_id}')
        
        
        MAXIMAL_DOWNLOAD_ATTEMPTS = 3
        content_agenda_page = None
        content_info_page = None
        
        # Try to download the session with topics webpage
        for attempts in range(MAXIMAL_DOWNLOAD_ATTEMPTS):
            try:
                response_agenda_page = requests.get(url_agenda_page)
                response_agenda_page.raise_for_status()
                content_agenda_page = response_agenda_page.text

                response_info_page = requests.get(url_info_page)
                response_info_page.raise_for_status()
                content_info_page = response_info_page.text
                           
                break
            
            except Exception:
                # Wait a calculated time until the next try
                time.sleep(MAXIMAL_DOWNLOAD_ATTEMPTS * 60)
            
        if content_agenda_page is None:
            raise BaseException(f"Die Webseite der Sitzung mit der URL {url_to_session} konnte nicht heruntergeladen werden!")

        if content_info_page is None:
            raise BaseException(f"Die Webseite der Sitzung mit der URL {url_to_session} konnte nicht heruntergeladen werden!")


        # Creates the data structure to save the source information
        data = {
                "source": {
                           "link": url_to_session,
                           "retrival date": str(datetime.now().timestamp())
                         },
                "documents": []
               }
        
        
        soup = BeautifulSoup(content_info_page, 'html.parser')
        
        table_element = soup.find("table", {"id": "smc_page_si0050_contenttable1"})
        
        link_elements = table_element.find_all("a", {"class": "smce-a-u"})
        
        file_links = []
        
        for link_element in link_elements:
            file_link = urljoin(self.entry_point, link_element["href"])
            file_links.append(file_link)
        
        # Remove the duplicated links
        file_links = list(set(file_links))
    

        for file_link in file_links:
            match = re.search(r'(?<=id=)[0-9]*', file_link) 
            document_id = match.group()

            filename, sha256_checksum = BaseGrabber.download_file(self, DIRECTORY_PATH, f'{file_link}', unique_identifier=document_id)

            # Adds the information of the file to the data object of the session
            data["documents"].append({"filename": filename, "sha256-checksum": sha256_checksum})


        # Saves the webpage, the infopage and the metadata file
        try:
            BaseGrabber.save_webpage(WEBPAGE_AGENDA_PATH, content_agenda_page)
            BaseGrabber.save_webpage(WEBPAGE_INFO_PATH, content_info_page)
            BaseGrabber.save_jsonfile(SESSION_DATA_FILE, data)
        
        except Exception:
            pass
    


    def get_all_proposals(self) -> List[str]:
        """Iterates through the saved raw data of the grabbed session webpages and
           collect all urls to a proposal in this files.
    
        Returns:
          An array with all discovered urls to the proposals.
        """
        
        BASE_SESSION_DIRECTORY = f'{self.base_directory}/rawdata/session_data/'

        proposal_links = []
    
        for directory in os.listdir(BASE_SESSION_DIRECTORY):
            # Pass the further processing if directory is a file
            if not os.path.isdir(f"{BASE_SESSION_DIRECTORY}/{directory}"):
                continue


            SESSION_AGENDA_PAGE_PATH = f'{BASE_SESSION_DIRECTORY}{directory}/session-agenda.html'
    
            # Guard if the webpage file does not exists
            if not os.path.isfile(SESSION_AGENDA_PAGE_PATH):
                continue
    
            with open(SESSION_AGENDA_PAGE_PATH, 'r') as handler:
                content = handler.read()

            soup = BeautifulSoup(content, 'html.parser')

            td_elements = soup.find_all("td", {"class": "smcrow1 smc_toph smc_toph1"})

            for td_element in td_elements:
                link_element = td_element.find("a", {"class": "smce-a-u smc-link-normal"})

                if link_element is None:
                    continue

                url_to_proposal = urljoin(self.entry_point, link_element["href"])
                proposal_links.append(url_to_proposal)

        
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
           AssertError:                     If no url was given as a parameter

           NoUniqueInternalProposalIDError: If the directory id can't be extracted from the given url.

           ProposalSavingError:             If the webpage can't be downloaded.
                                            If the proposal content can't be saved in a file
                                            If the meta data can't be saved in a json file
        """

        # Guard to avoid that a empty url to a proposal is processed
        assert url_to_proposal != "", "No valid url was given to the method."
        


        try:
            # Extract the proposal number from the url as a unique id
            match = re.search(r'(?<=kvonr=)[0-9]+', url_to_proposal) 
            directory_id = match.group()
            
        except Exception as exception:
            raise BaseException(self.identifier, f'Fehler beim Regex-Match aufgetreten. Der Grund ist {exception}')

            
    
        
        ## Sets the constants of the directory_path and file paths
        DIRECTORY_PATH = f'{self.base_directory}/rawdata/proposal_data/{directory_id}'
        WEBPAGE_PATH = f'{DIRECTORY_PATH}/proposal.html'
        PROPOSAL_DATA_FILE = f'{DIRECTORY_PATH}/proposal.json'

        
        # Creates the directory for the content of the proposal
        try:
             os.makedirs(DIRECTORY_PATH, exist_ok=True)
        except Exception as exception:
            raise BaseException(self.identifier, f'Beim erstellen des Verzeichnises ist ein Fehler aufgetretten. Der Grund lautet: {exception}', url_to_proposal)
        
    
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

        td_elements = soup.find_all("td", {"class":"smc_doc"})

        for td_element in td_elements:
            link_element = td_element.find("a")

            if link_element is None:
                continue

            file_link = urljoin(self.entry_point, link_element["href"])
            file_links.append(file_link)
        
        # Remove the duplicated links
        file_links = list(set(file_links))

        for file_link in file_links:
            match = re.search(r'(?<=id=)[0-9]+', file_link) 
            document_id = match.group()

            filename, sha256_checksum = BaseGrabber.download_file(self, DIRECTORY_PATH, f'{file_link}', unique_identifier=document_id)

            # Adds the information of the file to the data object of the session
            data["documents"].append({"filename": filename, "sha256-checksum": sha256_checksum})

        
        # Saves the webpage and the metadata file
        try:
            BaseGrabber.save_webpage(WEBPAGE_PATH, content)
            BaseGrabber.save_jsonfile(PROPOSAL_DATA_FILE, data)
        
        except Exception:
            pass
    




    def extract_file_links_from_session(self, content: str) -> List[str] | None:
        soup = BeautifulSoup(content, 'html.parser')
        
        table_element = soup.find("table", {"id": "smc_page_si0050_contenttable1"})

        if table_element is None:
            return None
        
        link_elements = table_element.find_all("a", {"class": "smce-a-u"})

        if link_elements is None:
            return None
        
        file_links = []
        
        for link_element in link_elements:
            # Guard if link element has no key href
            if "href" not in link_element:
                continue
            
            file_link = urljoin(self.entry_point, link_element["href"])
            file_links.append(file_link)
        
        # Remove the duplicated links
        file_links = list(set(file_links))

        return file_links



    def extract_proposal_links_from_session(self, content: str) -> List[str] | None:
        proposal_links = []
        
        # Initialize the parser for the webpage
        soup = BeautifulSoup(content, 'html.parser')

        td_elements = soup.find_all("td", class_=re.compile("smc_toph smc_toph1", re.I))

        for td_element in td_elements:
            link_element = td_element.find("a", {"class": "smce-a-u smc-link-normal"})

            if link_element is None:
                    continue

            url_to_proposal = urljoin(self.entry_point, link_element["href"])
            proposal_links.append(url_to_proposal)

        return proposal_links