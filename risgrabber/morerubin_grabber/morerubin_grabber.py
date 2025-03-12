from ..base_grabber import BaseGrabber


from typing import List
from selenium import webdriver
from selenium.webdriver.common.action_chains import WebElement
from selenium.webdriver.common.by import By
import time
import random
import re



class MoreRubinGrabber(BaseGrabber):
    def __init__(self, identifier, entry_point):
        super().__init__(identifier, entry_point)


    # https://badcamberg.gremien.info/calendar.php?month=2024-09
    # https://vg-wittlich.gremien.info/calendar.php <--- Verbandsgemeinde
    def get_all_sessions(self) -> List[str]:
        session_links = []
    
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
        session_links.extend(self.__extract_links_from_calendar(driver))
    
        
        # Backward pass in the calendar
        empty_month_watchdog = 0
        
        while empty_month_watchdog <= 12:
            button_previous = driver.find_element(By.XPATH, '//button[@accessiblity-label="Einen Monat zurück"]')
            button_previous.click()
                    
            links = self.__extract_links_from_calendar(driver)
            
            if len(links) == 0:
                empty_month_watchdog += 1
            else:
                empty_month_watchdog = 0
                session_links.extend(links)
    
            # Waits a random time to prevent DDOS protection is triggered
            waiting_time = random.uniform(5, 20)
            time.sleep(waiting_time)
    
        
        # Opens the startpage of the calendar
        driver.execute_script("window.open('" + self.entry_point + "','_self')")
        time.sleep(10)
    
        
        # Forward pass in the calendar
        empty_month_watchdog = 0
                
        while empty_month_watchdog <= 12:
            button_next = driver.find_element(By.XPATH, '//button[@accessiblity-label="Einen Monat weiter"]')
            button_next.click()
                    
            links = self.__extract_links_from_calendar(driver)
            
            if len(links) == 0:
                empty_month_watchdog += 1
            else:
                empty_month_watchdog = 0
                session_links.extend(links)
    
            # Waits a random time to prevent DDOS protection is triggered
            waiting_time = random.uniform(5, 20)
            time.sleep(waiting_time)
    
    
        # Filters the duplicates out of the url list
        session_links = list(set(session_links))
        
        return session_links


    
    def __extract_links_from_calendar(self,driver: webdriver) -> List[str]:
        links = []
        
        #month = (driver.find_element(By.XPATH, '//div[@class="calendar-page-readable-interval"]')).text
    
        div_elements = driver.find_elements(By.XPATH, '//div[@class="calendar-page-day-meeting-wrapper"]')
    
        for div_element in div_elements:
            a_element = div_element.find_element(By.TAG_NAME, "a")
    
            link = a_element.get_attribute("href")
            links.append(link)
    
        return links


    
    def download_session(self, url_to_session) -> None:
        # Testbeispiel: https://badcamberg.gremien.info/meeting.php?id=2025-PB-162
        raise NotImplementedError("Methode nicht implementiert!")



    def get_all_proposals(self):
        # https://vg-wittlich.gremien.info/meeting.php?id=2025-GR09-65
        raise NotImplementedError("Methode nicht implementiert!")



    def download_proposal(self, url_to_proposal) -> None:

        assert url_to_proposal != "", "No url to a proposal was given"

        # Extract the name of the directory out of the url
        try:
            match = re.search(r"(?<=vid=)[0-9]+", url_to_proposal)
            directory_id = match.group()
        except Exception:
            pass


        try:
            # Build the options for the web driver
            options = webdriver.FirefoxOptions()
            options.add_argument("-headless")
            
            # Creates the webdriver
            driver = webdriver.Firefox(options=options)
            
            # Set the value for the implicit wait
            driver.implicitly_wait(10)
            
            # Opens the startpage of the calendar
            driver.execute_script("window.open('" + url_to_proposal + "','_self')")

            import time
            time.sleep(10)
            # print(driver.page_source)

            propopsal_file_button = driver.find_element(By.XPATH,"//button[.//div[text()='Vorlage (487 kB)']]")
            #print(propopsal_file_button.text)
            propopsal_file_button.click()

            time.sleep(10)

            print(driver.page_source)

            # yyy = driver.find_element(By.CLASS_NAME, "file-viewer-modal-wrapper ")
            
            
            #search_text = "Vorlage (487 kB)"
            #proposal_file_button: WebElement = driver.find_element(By.XPATH, f"//div[contains(text(), '{search_text}')]")
            #print(proposal_file_button.text)
            #print(proposal_file_button)
            #import re
            #text_to_find = r"Vorlage"
            #import re
            #text_to_find = r"Vorlage (487 kB)"
            #proposal_file_button: WebElement = driver.find_element(By.XPATH, f"//div[contains(text(), '{text_to_find}')]")
            #print(proposal_file_button.text)
            # div: file-viewer-modal-wrapper global-file-viewer-modal ?

            #file_attachments: List[WebElement] = driver.find_elements(By.CLASS_NAME, "submission-attachments")
            #print(len(file_attachments))

            #for element in file_attachments:
            #    print(element.text)
            #    break
        
        except Exception as e:
            print(e)

        finally:
            if driver:
                driver.close()