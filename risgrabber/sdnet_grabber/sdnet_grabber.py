# Import of the required python modules
import os
import requests
import time
import re
from base_grabber import BaseGrabber

from bs4 import BeautifulSoup
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select
from selenium.webdriver.support.ui import WebDriverWait
from typing import List
from typing import Tuple

from selenium.webdriver.common.action_chains import WebElement



class SDNetGrabber(BaseGrabber):
    def __init__(self, identifier, entry_point):
        super().__init__(identifier, entry_point)


    
    def get_all_sessions(self, **kwargs) -> List[str]:
        """Iterates through the parlament information system to get all urls
           to the sessions.
    
        Returns:
          An list with all discovered urls to the sessions.
        """
        
        session_links: List[str] = []
        
        # Discover the start and end year
        start_year, end_year = self.__get_year_range()

        try:
            options = webdriver.FirefoxOptions()
            options.add_argument("-headless")
            driver = webdriver.Firefox(options=options)
            driver.execute_script("window.open('" + self.entry_point + "','_self')")

            WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.XPATH, '//button[text()="Jahresliste"]'))).click()
          
            time.sleep(10)
    
    
            # Iterate through the years and month pages
            for year in range(start_year, end_year + 1):
                year_selection = Select(driver.find_element(By.ID, "sstfc-button-year"))
                year_selection.select_by_visible_text(str(year))
                time.sleep(10)
                content = driver.page_source
                session_links.extend(self.__extract_session_links(content))
    
                break
        
        except Exception:
            pass

        finally:
            if driver:
                driver.quit()

        # Filters the duplicates out of the url list
        session_links = list(set(session_links))

        return session_links


    
    def download_session(self, url_to_session: str) -> None:
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
        
        match = re.search(r'(?<=\?__=)([a-zA-Z0-9])*', url_to_session)

        # Guard if the name cannot generated
        if match is None:
            raise BaseException(f"Es konnte aus der URL {url_to_session} der Sitzung kein Name extrahiert werden!")
        
        directory_id = match.group()

        DIRECTORY_PATH = os.path.join(self.base_directory, 'rawdata', 'session_data', directory_id)
        WEBPAGE_PATH = os.path.join(DIRECTORY_PATH, 'session.html')
        SESSION_DATA_FILE = os.path.join(DIRECTORY_PATH, 'session.json')
        
    
        # Creates the directory for the content of the session
        try:
            os.makedirs(DIRECTORY_PATH, exist_ok=True)
        except Exception as exception:
            raise BaseException(self.identifier, f'Beim erstellen des Verzeichnises ist ein Fehler aufgetretten. Der Grund lautet: {exception}', url_to_session)  

        
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
    
        links = self.__extract_session_file_links(content)
    
        for link in links:
            filename, sha256_checksum = super().download_file(DIRECTORY_PATH, link)
            data["documents"].append({"filename": filename, "sha256-checksum": sha256_checksum})

        # Saves the webpage and the metadata file
        try:
            super().save_webpage(WEBPAGE_PATH, content)
            super().save_jsonfile(SESSION_DATA_FILE, data)
        
        except Exception:
            pass


    
    def get_all_proposals(self) -> List[str]:
        """Iterates through the saved raw data of the grabbed session webpages and
           collect all urls to a proposal in this files.
    
        Returns:
          An array with all discovered urls to the proposals.
        """
        
        BASE_SESSION_DIRECTORY = f'{self.base_directory}/rawdata/session_data/'
    
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
    
            result = soup.find_all("table", {"id": "table0"})
    
            
            agenda_items = result[0].find_all("tr", class_=re.compile("top-oeff-data", re.I))
    
            for agenda_item in agenda_items:
                unique_proposal_id_element = agenda_item.find("td", {"class": "column-nummer"})
    
                # Guard if the required element has not been found
                if unique_proposal_id_element is None:
                    continue
    
                unique_proposal_id = unique_proposal_id_element.getText()
                unique_proposal_id = unique_proposal_id.strip()
    
                # Guard if the agenda item does not belong to a proposal
                if unique_proposal_id == "":
                    continue
    
                td_element = agenda_item.find("td", {"class": "column-dokumente"})
    
                link_elements = td_element.find_all("a")
    
                for link_element in link_elements:
                    span_element = link_element.find("span", class_=re.compile("vorgang-link", re.I))
                    
                    if span_element is None:
                        continue
                

    
    def download_proposal(self, url_to_proposal) -> None:
        match = re.search(r'(?<=\?__=)([a-zA-Z0-9])*', url_to_proposal)

        if match is None:
            raise BaseException("Konnte keine Verzeichnis Nummer aus der angegeben URL extrahieren.")
        
        directory_id = match.group()
        
        DIRECTORY_PATH = f'{self.base_directory}rawdata/proposal_data/{directory_id}/'
        WEBPAGE_PATH = f'{DIRECTORY_PATH}proposal.html'
        PROPOSAL_DATA_FILE = f'{DIRECTORY_PATH}proposal.json'

        
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
                           "retrival date": str(datetime.now().timestamp())
                         },
                "documents": []
               }
    
        links = self.__extract_proposal_file_links(content)
    
        for link in links:
            filename, sha256_checksum = BaseGrabber.download_file(self, DIRECTORY_PATH, link)
            data["documents"].append({"filename": filename, "sha256-checksum": sha256_checksum})        


        # Saves the webpage and the metadata file
        try:
            super().save_webpage(WEBPAGE_PATH, content)
            super().save_jsonfile(PROPOSAL_DATA_FILE, data)
        
        except Exception:
            pass

    
    
    def __extract_session_file_links(self, content: str) -> List[str]:
        links: List[str] = []
        
        soup = BeautifulSoup(content, 'html.parser')
    
        result = soup.find_all("div", {"class": "tops"})
    
        # Guard to check if the necessary element has been found
        if result is None:
            raise BaseException('Das notwenige HTML-Element "div" konnte nicht gefunden werden!')
    
        # Guard to check if only one element has been found
        if len(result) > 1:
            raise BaseException('Das notwenige HTML-Element "div" wurde zu oft gefunden!')
    
        for table_row in result[0].find_all("tr"):
            headline_element = table_row.find("th", {"scope": "row"})
    
            if headline_element is None:
                continue
    
            headline = headline_element.getText()
    
            if headline not in ["Einladung:","Niederschriften:"]:
                continue
    
            for link_element in table_row.find_all("a"):
                links.append(link_element['href'])
        
        return links


    
    def __extract_proposal_file_links(self, content: str) -> List[str]:
        links: List[str] = []
        
        soup = BeautifulSoup(content, 'html.parser')
    
        table_element = soup.find("table", {"class": "table-details"})
    
        if table_element is None:
            raise BaseException('Das notwenige HTML-Element "table" konnte nicht gefunden werden!')
    
        row_elements = table_element.find_all("tr")
    
        if row_elements is None:
            raise BaseException('Es konnte kein notwendiges HTML-Element "tr" gefunden werden!')
    
        for row_element in row_elements:
            headline_element = row_element.find("th", {"scope": "row"})
    
            if headline_element is None:
                continue
    
            headline = headline_element.getText()
    
            if headline != "Dokument:":
                continue
    
            for link_element in row_element.find_all("a"):
                links.append(link_element['href'])
    
        return links



    def __get_year_range(self) -> Tuple[int, int]:
        """Discovers the year range in which sessions in the parlament information system exists.

        Returns:
          An tuple with the minmal and the maximal year. As a default backup year it will return the current year for
          minimal and maximal year.
        """
        
        minimal_year = datetime.now().year
        maximal_year = datetime.now().year

        driver = None
        
        try:
            options = webdriver.FirefoxOptions()
            options.add_argument("-headless")
            driver = webdriver.Firefox(options=options)
            driver.execute_script("window.open('" + self.entry_point + "','_self')")

            WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "sstfc-button-year")))
            
            element_dropdown_year: WebElement = driver.find_element(By.ID, "sstfc-button-year")
                
                
            if element_dropdown_year is None:
                return minimal_year, maximal_year
                    
            select_selement = str(element_dropdown_year.get_attribute('innerHTML'))
        
            soup = BeautifulSoup(select_selement, 'html.parser')
            option_elements = soup.find_all("option")
        
            if len(option_elements) < 1:
                return minimal_year, maximal_year

            years = [int(option.get_text()) for option in option_elements]
            minimal_year = min(years)
            maximal_year = max(years)
               
        except Exception:
            pass
            
        finally:
            if driver is not None:
                driver.quit()
    
        return minimal_year, maximal_year



    def __extract_session_links(self, content: str) -> List[str]:
        session_links: List[str] = []
        
        soup = BeautifulSoup(content, 'html.parser')
    
        tr_elements = soup.find_all("tr", {"class": "sstfc-list-item sstfc-has-url"})
    
        for tr_element in tr_elements:
            link_element = tr_element.find("a")
    
            if link_element is None:
                continue

            
            session_links.append(link_element["href"])
    
        return session_links