from base_grabber import BaseGrabber
from typing import List


class PortaUNARisGrabber(BaseGrabber):
    def __init__(self, identifier, entry_point):
        super().__init__(identifier, entry_point)
    


    def get_all_sessions(self) -> List[str]:
        return super().get_all_sessions()



    def download_session(self, url_to_session) -> None:
        return super().download_session(url_to_session)
    


    def get_all_proposals(self) -> List[str]:
        return super().get_all_proposals()
    


    def download_proposal(self, url_to_proposal) -> None:
        return super().download_proposal(url_to_proposal)