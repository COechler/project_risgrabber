# Import of the required python modules
import hashlib as hash
import os
import re
import json
import requests
from typing import Any, List, Tuple
from urllib.parse import unquote


class BaseGrabber():
    def __init__(self, identifier: str, entry_point: str):        
        # Guard to prevent an empty identifier
        if not identifier:
            raise ValueError("Es wurde kein Identifier angegeben!")

        # Guard to prevent an empty entry_point
        if not entry_point:
            raise ValueError("Es wurde keine Start-URL zum Ratsinformationssystem angegeben!")
        
        self.identifier: str = identifier
        self.base_directory = f'data/{identifier}'
        self.entry_point: str = entry_point

        # Creates the directory for the grabber content
        os.makedirs(self.base_directory, exist_ok=True)

    
    def get_all_sessions(self, , **kwargs) -> List[str]:
        raise NotImplementedError("Methode zum Erstellen einer Liste mit allen Sitzungen wurde nicht implementiert!")

    
    def download_session(self, url_to_session: str) -> None:
        raise NotImplementedError("Methode zum Speichern der Sitzung mit allen Anhängen wurde nicht implementiert!")

    
    def get_all_proposals(self) -> List[str]:
        raise NotImplementedError("Methode zum Erstellen einer Liste mit allen Vorlagen wurde nicht implementiert!")


    def download_proposal(self, url_to_proposal: str) -> None:
        raise NotImplementedError("Methode zum Speichern der Vorlage mit allen Anhängen wurde nicht implementiert!")

    

    @staticmethod
    def get_sha256_checksum(filepath: str) -> str:
        """Calculates the checksum of a given file.

        Args:
           filepath: A filepath to a file on the file system.
    
        Raises:
           BaseException:         If there is no file path.
           FileNotFoundException: If 
                        
        """
        BLOCKSIZE = 65536
    
        sha = hash.sha256()
    
        with open(filepath, 'rb') as handler:
            file_buffer = handler.read(BLOCKSIZE)
            
            while len(file_buffer) > 0:
                sha.update(file_buffer)
                file_buffer = handler.read(BLOCKSIZE)
            
        return sha.hexdigest()

    

    @staticmethod
    def download_file(download_directory: str, url_to_file: str, unique_identifier: str | None = None)-> Tuple[str, str]:
        """Download a file from a URL and save it to the specified directory.
    
        Args:
            download_directory: The directory to save the downloaded file.
            url_to_file:        The URL of the file to download.
            unique_identifier:  A unique identifier to prepend to the filename (optional).

        Returns:
            A tuple containing the filename and its SHA-256 checksum.
    
        Raises:
            Exception: If the file could not be downloaded.
        """
        
        response = requests.get(url_to_file)

        if response.status_code != 200:
            print("Fehler")

        content_disposition = response.headers.get("Content-Disposition")
        
        if content_disposition:
            match = re.search(r'filename="(.*)"', content_disposition)
        else:
            match = None

        if match is not None:
            filename = match.group(1)
            filename = unquote(filename)
        else:
            filename = unique_identifier
            unique_identifier = None

        if unique_identifier is not None:
            filename = f'{unique_identifier}_{filename}'

        filepath = f'{download_directory}/{filename}'

        with open(filepath, "wb") as handler:
            handler.write(response.content)

        sha256_checksum = BaseGrabber.get_sha256_checksum(filepath)
    
        return filename, sha256_checksum

    
    def get_identifier(self):
        return self.identifier


    @staticmethod
    def save_webpage(filepath: str, data: str) -> None:
        with open(filepath, 'w') as file:
                file.write(data)
    

    @staticmethod
    def save_jsonfile(filepath: str, data: Any) -> None:
        with open(filepath, 'w', encoding='utf-8') as file:
                json.dump(data, file, ensure_ascii=False, indent=4)