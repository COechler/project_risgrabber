from base_grabber import BaseGrabber

class KommunaRisGrabber(BaseGrabber):
    def __init__(self, identifier, entry_point):
        super().__init__(identifier, entry_point)



    def get_all_sessions(self):
        raise NotImplementedError("Methode nicht implementiert!")
    


    def download_session(self, url_to_session):
        raise NotImplementedError("Methode nicht implementiert!")
    


    def get_all_proposals(self):
        raise NotImplementedError("Methode nicht implementiert!")
    


    def download_proposal(self, url_to_proposal):
        raise NotImplementedError("Methode nicht implementiert!")