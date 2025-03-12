import os
import requests
import time
from ..base_grabber import BaseGrabber
from bs4 import BeautifulSoup
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException
from typing import List


class RegisafeGrabber(BaseGrabber):
    def __init__(self, identifier, entry_point):
        super().__init__(identifier, entry_point)


    
    def get_all_sessions(self, **kwargs) -> List[str]:
        session_links = []

        try:
            options = webdriver.FirefoxOptions()
            options.add_argument("-headless")
            driver = webdriver.Firefox(options=options)
            
            driver.execute_script("window.open('" + self.entry_point + "','_self')")
            time.sleep(5)
            
            button_year = driver.find_element(By.XPATH, '//button[text()="Jahr"]')
            button_today = driver.find_element(By.XPATH, '//button[text()="Heute"]')
            button_left = driver.find_element(By.XPATH, '//button[@aria-label="Vorherige Seite"]')
            
            button_year.click()
            time.sleep(5)
            button_today.click()
            time.sleep(5)
            content = driver.page_source
            session_links.extend(self.__extract_session_links(content))
            
            while True:
                button_left.click()
                time.sleep(5)
                content = driver.page_source
            
                try:
                    driver.find_element(By.XPATH, '//span[text()="Keine Sitzungen an diesem Tag"]')
                    break
                except NoSuchElementException:
                    pass
            
                session_links.extend(self.__extract_session_links(content))
        
        except Exception:
            pass

        finally:
            if driver:
                driver.close()

        return session_links


    # TODO: Directory_ID muss eingefügt werden
    def download_proposal(self, url_to_proposal) -> None:
        directory_id = "42"

        
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
    


        soup = BeautifulSoup(content, 'html.parser')

        section_element = soup.find("section", {"id": "content"})

        assert section_element is None, "Can not find the necessary tag: section_element"

        ul_element = section_element.find("ul", {"class": "top-document-list"})

        assert ul_element is None, "Can not find the necessary tag: ul_element"

        button_elements = ul_element.find_all("button", {"class":"document-button"})

        for button_element in button_elements:
            print(button_element)

        

    def __extract_session_links(self, content):
        soup = BeautifulSoup(content, 'html.parser')
    
        link_elements = soup.find_all("a", {"class": "mbsc-event-list-item-link"})

        if not link_elements:
            raise ValueError("Keine Link-Elemente gefunden!")
    
        session_links = [link["href"] for link in link_elements if "href" in link.attrs]
    
        return session_links



    def get_all_proposals(self) -> List[str]:
        super().get_all_proposals(self)


    # https://huettenberg.ris-portal.de/web/ratsinformation/sitzungen?p_p_id=RisSitzung&p_p_lifecycle=0&p_p_state=normal&p_p_mode=view&_RisSitzung_mvcRenderCommandName=%2Ftop-detail&_RisSitzung_sitzungId=126046&_RisSitzung_topId=1347857
    def download_proposal(self, url_to_proposal) -> None:
        super().download_proposal(url_to_proposal)