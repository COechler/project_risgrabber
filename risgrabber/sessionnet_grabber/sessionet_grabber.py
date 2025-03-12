# Imports the necessary modules
import re
import requests
from ..base_grabber import BaseGrabber
from .sessionet_grabber_v3 import SessionNetGrabberV3
from .sessionet_grabber_v6 import SessionNetGrabberV6
from bs4 import BeautifulSoup
from typing import List


class SessionNetGrabber(BaseGrabber):
    def __init__(self, identifier: str, entry_point: str):
        super().__init__(identifier, entry_point)

        # Saves the discoverd layout version of SessionNet
        self.__layout_version: str | None = self.__get_layout_version()

        # Selects the suitable for the layout version of SessionNet
        match self.__layout_version:
            case "layout-3":
                self.grabber = SessionNetGrabberV3(self.entry_point, self.base_directory)
            case "layout-6":
                self.grabber = SessionNetGrabberV6(self.entry_point, self.base_directory)
            case _:
                self.grabber = BaseGrabber(self.identifier, self.entry_point)



    def __get_layout_version(self) -> str | None:
        """ Discover the layout version of the session.net instance.

        Returns:
          A string with the layout name
        """
        response = requests.get(self.entry_point)
        response.raise_for_status()
        content = response.text
    
        soup = BeautifulSoup(content, 'html.parser')
    
        meta_tags = soup.find_all("meta")

        # Guard if no metatags are found
        if not meta_tags:
            raise ValueError('Es konnten keine benötigten meta tags gefunden werden')
    
        for meta_tag in meta_tags:
            # Guard to stop the procressing of the meta data if not content attribute exists
            if "content" not in meta_tag.attrs:
                continue
    
            content = meta_tag["content"]
    
            match = re.search(r'(?<=\(Layout )[0-9](?=\))', content)
        
            # Guard if no layout information was found in this meta tag
            if match is None:
                continue
        
            try:
                version = match.group()
                return f'layout-{version}'
            except Exception:
                return None



    def get_all_sessions(self, **kwargs) -> List[str]:
        return self.grabber.get_all_sessions(kwargs)



    def download_session(self, url_to_session) -> None:
        self.grabber.download_session(url_to_session)
    


    def get_all_proposals(self) -> List[str]:
        return self.grabber.get_all_proposals()
    


    def download_proposal(self, url_to_proposal) -> None:
        self.grabber.download_proposal(url_to_proposal)