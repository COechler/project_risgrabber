from ..base_grabber import BaseGrabber
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import WebElement
from typing import List

import time

class KommuneAktivGrabber(BaseGrabber):
    def __init__(self, identifier, entry_point):
        super().__init__(identifier, entry_point)



    def get_all_sessions(self) -> List[str]:
        try:
            options = webdriver.FirefoxOptions()
            options.add_argument("-headless")
            driver = webdriver.Firefox(options=options)

            # https://braunfels.ris.kommune-aktiv.de/kalender/de/rathaus/26/1_-_-_07.03.2016/calendar_search
            # Iteration durch den Kalendar, immter ersten Tag im Monat auswählen
            # Wenn sich erste Überschrift im Monat und Jahr nicht mehr ändert, dann den Anfang gefunden
            # Anschließende Iteration nach vorne über ">> >>  weiter  >>" Link bis der link nicht zur Verfügung steht

            # Forward iteration through the calendar sites
            #driver.execute_script(f"window.open('{self.entry_point}', '_self')")
            bob = "https://braunfels.ris.kommune-aktiv.de/kalender/de/rathaus/-/-/calendar_show"
            driver.execute_script(f"window.open('{bob}', '_self')")
            
            # Wartet bis alle elemente geladen sind
            time.sleep(20)

            next_page_link: WebElement = driver.find_element(By.LINK_TEXT, ">> >>  weiter  >>")
            
            print(next_page_link.text)

            #next_page_link.click()

            time.sleep(20)

            # Get all links in the session part of the webpage
            calendar_element: WebElement = driver.find_element(By.XPATH, '//div[@id="vk"]')
            session_elements: List[WebElement] = calendar_element.find_elements(By.XPATH, '//div[@class="floatleft"]')

            for session_element in session_elements:
                link_elements: List[WebElement] = session_element.find_elements(By.TAG_NAME, "a")

                if len(link_elements) < 1:
                    continue

                for link_element in link_elements:
                    print(link_element.text)

            # Glickt auf den nächsten Link
            #next_page_link: WebElement = driver.find_element(By.LINK_TEXT, ">> >>  weiter  >>")
            #next_page_link.click()

        except Exception:
            pass

        finally:
            if driver:
                driver.close()
    


    def download_session(self, url_to_session) -> None:
        return super().download_session(self, url_to_session) 
    


    def get_all_proposals(self) -> List[str]:
        return super().get_all_proposals(self) 
    

    # Beispiel: https://braunfels.ris.kommune-aktiv.de/seite/de/rathaus/25572/-/7_Aenderungssatzung_zur_Wasserversorgungssatzung_der_Stadt_Braunfels.html
    def download_proposal(self, url_to_proposal) -> None:
        return super().download_proposal(self, url_to_proposal) 