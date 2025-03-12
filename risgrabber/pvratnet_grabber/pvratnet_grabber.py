import os
import requests
import time

from base_grabber import BaseGrabber
from bs4 import BeautifulSoup
from datetime import datetime
from typing import List

from urllib.parse import urljoin

from selenium import webdriver
from selenium.webdriver.common.action_chains import WebElement
from selenium.webdriver.common.by import By



class PVRatNetGrabber(BaseGrabber):
    def __init__(self, identifier, entry_point):
        super().__init__(identifier, entry_point)


    
    def get_all_sessions(self) -> List[str]:
        session_links: List[str] = []
        
        try:
            # Build the options for the web driver
            options = webdriver.FirefoxOptions()
            options.add_argument("-headless")
    
            # Creates the webdriver
            driver = webdriver.Firefox(options=options)
    
            # Set the value for the implicit wait
            driver.implicitly_wait(10)
    
            # Opens the startpage of the calendar
            driver.execute_script("window.open('" + self.entry_point + "','_self')")
            
    
            # Get the sessions from the start month of the calendar
            session_links.extend(self.__get_session_links(driver))    
        
            
            # Backward pass in the calendar
            empty_month_watchdog: int = 0
            
            while empty_month_watchdog <= 12:
                button_previous: WebElement = driver.find_element(By.XPATH, '//button[@title="Vorheriger Monat"]')
                button_previous.click()
    
                links: str = self.__get_session_links(driver)
        
                if len(links) == 0:
                    empty_month_watchdog += 1
                else:
                    empty_month_watchdog = 0
                    session_links.extend(links)
        
            
            # Returns to the beginning month of the calendar
            button_today: WebElement = driver.find_element(By.XPATH, '//button[@title="Dieser Monat"]')
            button_today.click()
        
        
            # Forward pass in the calendar
            empty_month_watchdog: int = 0
            
            while empty_month_watchdog <= 12:
                button_next: WebElement = driver.find_element(By.XPATH, '//button[@title="Nächster Monat"]')
                button_next.click()
                
                links: str = self.__get_session_links(driver)
        
                if len(links) == 0:
                    empty_month_watchdog += 1
                else:
                    empty_month_watchdog = 0
                    session_links.extend(links)
        
        
            # Filters the duplicates out of the url list
            session_links = list(set(session_links))
        
        except Exception as e:
            print(e)
    
        finally:
            if driver:
                driver.close()
                

            return session_links



    def __get_session_links(self, driver) -> List[str]:
        session_links: List[str] = []
        
        field_elements: List[WebElement] = driver.find_elements(By.CLASS_NAME, "fc-daygrid-day-events")
    
        for field_element in field_elements:
            link_elements: List[WebElement] = field_element.find_elements(By.TAG_NAME, "a")
    
            if not link_elements:
                continue
    
            for link_element in link_elements:
                session_links.append(link_element.get_attribute("href"))
    
        return session_links


    
    def download_session(self, url_to_session: str) -> None:
        """Gets the session with given url and saves the webpage (JSON) in a directory.
           Additionally saves all appendix files of the session in the directory
           and creates a JSON fille with meta informationen of the session.

        Args:
           url_to_session: A url to the session in the parlament information system.
        """

        assert url_to_session != "", "No url was given as a parameter"
        

        directory_id = url_to_session.split("/")[-1]

        # Sets the constants of the directory_path and file paths
        DIRECTORY_PATH = f'{self.base_directory}/rawdata/session_data/{directory_id}'
        WEBPAGE_PATH = f'{DIRECTORY_PATH}/session.html'
        SESSION_DATA_FILE = f'{DIRECTORY_PATH}/session.json'

        # Creates the directory to save the files of the session
        os.makedirs(DIRECTORY_PATH, exist_ok=True)
    
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
            raise BaseException(f"Die Webseite des Antrags mit der URL {url_to_session} konnte nicht heruntergeladen werden!")

        
        # Creates the data structure to save the source information
        data = {
                "source": {
                           "link": url_to_session,
                           "retrival date": str(datetime.now())
                         },
            
                "documents": []
               }
    

        file_links = []

        soup = BeautifulSoup(content, 'html.parser')

        link_announcement = soup.find("a", {"aria-label": "Aushang"})
        if link_announcement is not None:
            file_link = urljoin(self.entry_point, str(link_announcement["href"]))
            file_links.append(file_link)
        
        link_invitation = soup.find("a", {"aria-label": "Öffentliche Einladung"})
        if link_invitation is not None:
            file_link = urljoin(self.entry_point, str(link_invitation["href"]))
            file_links.append(file_link)
        
        link_protocol = soup.find("a", {"aria-label": "Öffentliches Protokoll"})
        if link_protocol is not None:
            file_link = urljoin(self.entry_point, str(link_protocol["href"]))
            file_links.append(file_link)


        for file_link in file_links:
            unique_id = file_link.split("/")[-1]
            filename, sha256_checksum = BaseGrabber.download_file(self, DIRECTORY_PATH, f'{file_link}',unique_id)

            # Adds the information of the file to the data object of the session
            data["documents"].append({"filename": filename, "sha256-checksum": sha256_checksum})


        # Saves the webpage and the metadata file
        try:
            super().save_webpage(WEBPAGE_PATH, content)
            super().save_jsonfile(SESSION_DATA_FILE, data)
        
        except Exception:
            pass


    
    def get_all_proposals(self) -> List[str]:
        BASE_SESSION_DIRECTORY = f'{self.base_directory}/rawdata/session_data/'

        proposal_links: List[str] = []
    
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

            main_div_element = soup.find("div", {"id": "agenda"})

            if main_div_element is None:
                return []

            meetingitem_div_elements = main_div_element.find_all("div", {"class": "meetingitem"})

            for meetingitem_div_element in meetingitem_div_elements:
                link_element = meetingitem_div_element.find("a", {"aria-label":"Vorlage"})

                if link_element is None:
                    continue
                
                url_to_proposal = urljoin(self.entry_point, link_element["href"])
                proposal_links.append(url_to_proposal)

         # Filters the duplicates out of the url list
        proposal_links = list(set(proposal_links))
        
        return proposal_links


    
    def download_proposal(self, url_to_proposal) -> None:
        # Guard to prevent an empty url to download
        assert url_to_proposal != "", "No linkt to a proposal was given as an argument"

        directory_id = url_to_proposal.split("/")[-1]
        
        # Sets the constants of the directory_path and file paths
        DIRECTORY_PATH = f'{self.base_directory}/rawdata/proposal_data/{directory_id}'
        WEBPAGE_PATH = f'{DIRECTORY_PATH}/proposal.html'
        PROPOSAL_DATA_FILE = f'{DIRECTORY_PATH}/proposal.json'

        # Creates the directory to save the files of the proposal
        os.makedirs(DIRECTORY_PATH, exist_ok=True)
    
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
    
        

        file_links = []

        soup = BeautifulSoup(content, 'html.parser')

        tr_elements = soup.find_all("tr", {"singleattachment"})

        

        for tr_element in tr_elements:
            link_element = tr_element.find("a")

            #if "href" in link_element.hasKeys()
            

            file_link = urljoin(self.entry_point, link_element["href"])
            file_links.append(file_link)

        for file_link in file_links:
            unique_id = file_link.split("/")[-1]
            filename, sha256_checksum = BaseGrabber.download_file(self, DIRECTORY_PATH, f'{file_link}',unique_id)

            # Adds the information of the file to the data object of the session
            data["documents"].append({"filename": filename, "sha256-checksum": sha256_checksum})

        # Saves the webpage and the metadata file
        try:
            super().save_webpage(WEBPAGE_PATH, content)
            super().save_jsonfile(PROPOSAL_DATA_FILE, data)
        
        except Exception:
            pass
        