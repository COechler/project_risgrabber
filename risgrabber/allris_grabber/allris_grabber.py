import re
import time
from bs4 import BeautifulSoup
from base_grabber import BaseGrabber
from typing import List

from .allris_grabber_v3 import AllrisGrabberV3
from .allris_grabber_v4 import AllrisGrabberV4

from selenium import webdriver



class AllrisGrabber(BaseGrabber):
    def __init__(self, identifier, entry_point) -> None:
        super().__init__(identifier, entry_point)
        
        # Discover the version of the allris system
        self.__allris_version = self.__get_allris_version()

        # Selects the suitable for the layout version of SessionNet
        match self.__allris_version:
            case "layout-3":
                self.grabber = AllrisGrabberV3(self.entry_point, self.base_directory)
            case "layout-6":
                self.grabber = AllrisGrabberV4(self.entry_point, self.base_directory)
            case _:
                self.grabber = BaseGrabber(self.identifier, self.entry_point)

    
    
    def __get_allris_version(self) -> str | None:
        driver = None
        
        try:
            options = webdriver.FirefoxOptions()
            options.add_argument("-headless")
            driver = webdriver.Firefox(options=options)
                
            driver.execute_script(f"window.open('{self.entry_point}', '_self')")

            #WebDriverWait(driver, 60).until(EC.presence_of_element_located((By.TAG_NAME, 'body')))

    
            time.sleep(10)
        
            content = driver.page_source
        
            soup = BeautifulSoup(content, 'html.parser')
            meta_tag_elements =soup.find_all("meta")
    
            if not meta_tag_elements:
                raise ValueError("Interner Fehler: Konnte keine Meta-Tags finden!")
        
            for meta_element in meta_tag_elements:
                content = meta_element["content"]
                match = re.search(r'(?<=Version )[0-9]*(?=.)', content)
    
                # Guard if no version was found in this meta tag
                if match is None:
                    continue
    
                version = match.group()
                return f'v{version}'
    
            return None
    
        except Exception:
            return None
    
        finally:
            if driver:
                driver.close()

    
    
    def get_all_sessions(self) -> List[str]:
        return self.grabber.get_all_sessions()



    def download_session(self, url_to_session) -> None:
        self.grabber.download_session(url_to_session)
    


    def get_all_proposals(self) -> List[str]:
        return self.grabber.get_all_proposals()
    


    def download_proposal(self, url_to_proposal) -> None:
        self.grabber.download_proposal(url_to_proposal)