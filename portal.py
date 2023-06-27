import requests
import os
from typing import Optional
from bs4 import BeautifulSoup
from urllib.parse import urlencode

SCHULPORTAL_URL = os.environ["SCHULPORTAL_URL"]

def getSoup(blob: str) -> BeautifulSoup:
    return BeautifulSoup(blob, 'html5lib')

class Portal:
    def __init__(self, username: str, password: str):
        self.url = SCHULPORTAL_URL
        self.username = username
        self.password = password
        self._session = requests.Session()

    @property
    def url(self) -> str:
        return self._url
    
    @url.setter
    def url(self, url: str):
        self._url = str(url)

    @property
    def username(self) -> str:
        return self._username
    
    @username.setter
    def username(self, username: str):
        self._username = str(username)

    @property
    def password(self) -> str:
        return self._password
    
    @password.setter
    def password(self, password: str):
        self._password = str(password)

    def list(self) -> list[dict[str:str]]:
        response = self._session.get(self.url)
        soup = getSoup(response.content)
        toDict = lambda x: {"school": str(x[0]).strip(), "city": str(x[1]).strip()}
        return [
            {**toDict(tuple(el.strings)), "data-id": el.get("data-id")}
            for el in soup.find_all("a", attrs={"class":"list-group-item"})
        ]

    def login(self, id: str):
        response = self._session.get(self.url, params={"i": str(id)})
        soup = getSoup(response.content)
        form = {
            el.get("name"): el.get("value")
            for el in soup.select('input[type="hidden"]')
        }
        form.update({
            "user": self.username,
            "passw": self.password,
            "sid": response.cookies.get_dict().get("sid"),
            #"saveLogin": "1",
            #"saveUsername": "",
        })
        
        response = self._session.post(
            self.url, 
            params={"i": str(id)}, 
            data=urlencode(form), 
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        print(response.content)
        print(response.status_code)
        print(form)

    def logout(self):
        """
        Logs out from the school portal.
        """
        self._session.get(self.url, params={"logout": "1"})