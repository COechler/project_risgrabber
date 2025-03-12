# Import of the required python modules
import json
import os
import random
import requests
import time

from base_grabber import BaseGrabber

from datetime import datetime
from typing import List
from urllib.parse import urlparse

class OparlGrabber(BaseGrabber):
    def __init__(self, identifier, entry_point):
        super().__init__(identifier, entry_point)


    
    def get_all_sessions(self, **kwargs) -> List[str]:
        """Iterates through the parlament information system to get all urls
           to the sessions.
    
        Returns:
          An array with all discovered urls to the sessions,.
    
        Raises:
          
        """

        # Gets the url to the body page
        response = requests.get(self.entry_point)
        response.raise_for_status() 
        data = response.json()

        # Guard, if the necessary key does not exist
        if "body" not in data:
            raise ValueError('Es konnte nicht die benötigte URL zur "body"-Seite gefunden werden.')

        # Gets the url to the meeting page
        response = requests.get(data["body"])
        response.raise_for_status() 
        data = response.json()

        if len(data["data"]) == 0:
            raise ValueError('Es konnte nicht die benötigte URL zur "meeting"-Seite gefunden werden.')
        elif len(data["data"]) > 1:
            raise NotImplementedError('Funktonalität für mehrere Meeting-Seiten nicht implementiert')

        # Guard, if the necessary key does not exist
        if 'meeting' not in data["data"][0]:
            raise ValueError('Es konnte nicht die benötigte URL zur "meeting"-Seite gefunden werden.')

        # Sets the meeting page to the current url
        current_url = data["data"][0]["meeting"]

        urls_to_session = []

        while True:
            response = requests.get(current_url)
            response.raise_for_status() 

            data = response.json()

            for meeting in data["data"]:
                urls_to_session.append(meeting["id"])
    
            if "next" in data["links"].keys():
                current_url = data["links"]["next"]
            else:
                break

            # Waits a random time to prevent DDOS protection is triggered
            waiting_time = random.uniform(5, 20)
            time.sleep(waiting_time)

        return urls_to_session


    
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

        # Extract the unique name of the directory from the given url
        try:
            directory_id = urlparse(url_to_session).path.split("/")[-1]
        except Exception:
            raise BaseException(f'Es konnte keine eindeutige ID als Ordnername für die URL "{url_to_session}" ermittelt werden')

        
         # Sets the constants of the directory_path and file paths
        DIRECTORY_PATH = os.path.join(self.base_directory, 'rawdata', 'session_data', directory_id)
        WEBPAGE_PATH = os.path.join(DIRECTORY_PATH, 'session-raw.json')
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
                response.raise_for_status()      
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

        session_data = json.loads(content)

        file_links = []

        # Adds the result protocol of the session to the files to download
        if "resultsProtocol" in session_data.keys():
            file_links.append(session_data["resultsProtocol"]["downloadUrl"])


        # Iterate through the discovered links to the appendix of the session
        for link in file_links:
            # Trys to download the given file link and create an entry for the JSON file with the meta information 
            try:
                filename, sha256_checksum = BaseGrabber.download_file(self, DIRECTORY_PATH, link)
                data["documents"].append({"filename": filename, "sha256-checksum": sha256_checksum})
            except Exception:
                raise BaseException(f"Die zur Sitzung mit der URL {url_to_session} gehörende Datei mit der url {link} konnte nicht runtergeladen werden!")

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
        
        BASE_SESSION_DIRECTORY = f'{self.base_directory}rawdata/session_data/'

        links = []
        
        for directory in os.listdir(BASE_SESSION_DIRECTORY):
            # Guard for checking that the path is not a path to a file
            if not os.path.isdir(f"{BASE_SESSION_DIRECTORY}/{directory}"):
                continue

            # Creates the path to the file with raw information of the session
            SESSION_FILE_PATH = f'{BASE_SESSION_DIRECTORY}{directory}/session-raw.json'

            # Guard for checking of the exisiting of the file with the raw informaton of the session
            if not os.path.exists(SESSION_FILE_PATH):
                continue

            # Reads the content of the file with the raw information of the session
            with open(SESSION_FILE_PATH, "r") as handler:
                content = json.load(handler)

            if "agendaItem" in content.keys():

                # Iterate through the items of the agenda
                for item in content["agendaItem"]:
                    # Guard for checking of the required id field
                    if "id" not in item.keys():
                        continue

                    links.append(item["id"])

        # Filters the duplicates out of the list
        links = list(set(links))

        return links


    
    def download_proposal(self, url_to_proposal) -> None:
        """Gets the proposal with given url and saves the webpage (JSON) in a directory.
           Additionally saves all appendix files of the proposal in the directory
           and creates a JSON fille with meta informationen of the proposal.
    
        Args:
           url_to_proposal: A url to the proposal in the parlament information system.
    
        Raises:
           BaseException: If the directory id can't be extracted from the given url.
                          If the webpage (JSON) can't be downloaded.
                          It a appendix file can't be downloaded.
                          If the raw webpage (JSON) can't be saved
                          If the JSON file with the meta information of the proposal can't be saved.
        """

        # Extract the unique name of the directory from the given url
        try:
            directory_id = urlparse(url_to_proposal).path.split("/")[-1]
        except Exception:
            raise BaseException(f'Es konnte keine eindeutige ID als Ordnername für die URL "{url_to_proposal}" ermittelt werden')

        # Creates constants with the pathes to the directory and the files
        DIRECTORY_PATH = f'{self.base_directory}/rawdata/proposal_data/{directory_id}'
        WEBPAGE_PATH = f'{DIRECTORY_PATH}/proposal-raw.json'
        PROPOSAL_DATA_FILE = f'{DIRECTORY_PATH}/proposal.json'
        

        # Creates the directory for the content of the proposal
        try:
             os.makedirs(DIRECTORY_PATH, exist_ok=True)
        except Exception as exception:
            raise BaseException(self.identifier, f'Beim erstellen des Verzeichnises ist ein Fehler aufgetretten. Der Grund lautet: {exception}', url_to_proposal)  
        

        MAXIMAL_DOWNLOAD_ATTEMPTS = 3
        content = None

        # Try to download the proposal webpage
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
            raise BaseException(f"Die Webseite der Vorlage mit der URL {url_to_proposal} konnte nicht heruntergeladen werden!")

        
        # Creates the data structure to save the source information
        data = {
                "source": {
                           "link": url_to_proposal,
                           "retrival date": str(datetime.now().timestamp())
                         },
                "documents": []
               }


        proposal_data = json.loads(content)

        file_links = []

        # Checks that the required keys are in the data of the JSON file
        if "auxiliaryFile" in proposal_data.keys():
            for file in proposal_data["auxiliaryFile"]:
                # Guard to check that the json file information has the required key
                if "downloadUrl" not in file.keys():
                    continue

                file_links.append(file["downloadUrl"])

        # Iterate through the discovered links to the appendix of the propsal
        for link in file_links:
            # Trys to download the given file link and create an entry for the JSON file with the meta information 
            try:
                filename, sha256_checksum = BaseGrabber.download_file(self, DIRECTORY_PATH, link)
                data["documents"].append({"filename": filename, "sha256-checksum": sha256_checksum})
            except Exception:
                raise BaseException(f"Die zur Vorlage mit der URL {url_to_proposal} gehörende Datei mit der url {link} konnte nicht runtergeladen werden!")

        
        # Saves the webpage and the metadata file
        try:
            super().save_webpage(WEBPAGE_PATH, content)
            super().save_jsonfile(PROPOSAL_DATA_FILE, data)
        
        except Exception:
            pass