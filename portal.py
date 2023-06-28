import os
import re
import random
from typing import Union, Optional
from bs4 import BeautifulSoup
from urllib.parse import urlencode
from aiohttp import ClientSession
from errors import LoginFailed, NotSignedIn, NothingToReturn

SCHULPORTAL_USERNAME = os.environ.get("SCHULPORTAL_USERNAME", "")
SCHULPORTAL_PASSWORD = os.environ.get("SCHULPORTAL_PASSWORD", "")
SCHULPORTAL_SCHOOL_ID = os.environ.get("SCHULPORTAL_SCHOOL_ID", "5114")

SCHULPORTAL_START_URL = os.environ["SCHULPORTAL_START_URL"]
SCHULPORTAL_LOGIN_URL = os.environ["SCHULPORTAL_LOGIN_URL"]
SCHULPORTAL_VERTRETUNGSPLAN_URL = os.environ["SCHULPORTAL_VERTRETUNGSPLAN_URL"]
SCHULPORTAL_MEINUNTERRICHT_URL = os.environ["SCHULPORTAL_MEINUNTERRICHT_URL"]
SCHULPORTAL_NACHRICHTEN_URL = os.environ["SCHULPORTAL_NACHRICHTEN_URL"]
SCHULPORTAL_AJAX_URL = os.environ["SCHULPORTAL_AJAX_URL"]

def getSoup(blob: Union[str, bytes]) -> BeautifulSoup:
    """
    Convert the given HTML blob into a BeautifulSoup object.

    Args:
        blob: The HTML content as a string or bytes.

    Returns:
        BeautifulSoup: A BeautifulSoup object representing the parsed HTML.
    """
    return BeautifulSoup(blob, 'html5lib')


def buildArgs(blob: str) -> list[str]:
    """
    Build a list of strings from the given blob by splitting it based on sentence boundaries.

    Args:
        blob: The input string to be split.

    Returns:
        list[str]: A list of strings obtained by splitting the input blob.
    """
    return list(
        filter(
            lambda x: x != '',
            re.compile("([^!.?]+[!.?])\s").split(" ".join(map(lambda x: str(x).strip(), blob.splitlines())))
        )
    )

class Portal:
    def __init__(self, username: str, password: str, *, session: Optional[ClientSession]=None):
        """
        Initialize a Portal object with the provided username, password, and session.

        Args:
            username: The username used for authentication.
            password: The password used for authentication.

        Keywargs:
            session: An optional aiohttp.ClientSession object to use for HTTP requests.
                     If not provided, a new session will be created.
        """
        self.username = username
        self.password = password
        self._session = session
        if self._session is None:
            self._session = ClientSession()
        self._loggedIn = False

    @property
    def username(self) -> str:
        """
        Get the username associated with the Portal object.

        Returns:
            str: The username.
        """
        return self._username

    @username.setter
    def username(self, username: str):
        """
        Set the username for the Portal object.

        Args:
            username: The username to be set.
        """
        self._username = str(username)

    @property
    def password(self) -> str:
        """
        Get the password associated with the Portal object.

        Returns:
            str: The password.
        """
        return self._password

    @password.setter
    def password(self, password: str):
        """
        Set the password for the Portal object.

        Args:
            password: The password to be set.
        """
        self._password = str(password)

    @property
    def loggedIn(self) -> bool:
        """
        Check if the Portal object is currently logged in.

        Returns:
            bool: True if logged in, False otherwise.
        """
        return self._loggedIn

    async def check_substitutes(self):
        """
        Check the substitutes (Vertretungsplan) on the portal.

        Raises:
            NotSignedIn: If the user is not signed in.
            NothingToReturn: If there are no substitutes to return.
            NotImplemented: If the method is not implemented yet.
        """
        if not self._loggedIn:
            raise NotSignedIn("Sign in first.")

        async with self._session.get(SCHULPORTAL_VERTRETUNGSPLAN_URL) as response:
            content = await response.text()
            soup = getSoup(content)
            alert = soup.select_one('div[role="alert"]')

            if alert is not None:
                raise NothingToReturn(*buildArgs(alert.getText()))

            # TODO: Implement
            raise NotImplemented(self.check_substitutes)

    async def get_undone_homework(self):
        """
        Retrieves a list of undone homework from a web portal.

        Raises:
            NotSignedIn: If the user is not signed in.

        Returns:
            A list of dictionaries representing undone homework tasks. Each dictionary contains the following keys:
                - "topic": The topic or title of the homework task.
                - "teacher": The name of the teacher associated with the homework task.
                - "date": The date of the homework task.
                - "content": The content or description of the homework task.
        """
        if not self._loggedIn:
            raise NotSignedIn("Sign in first.")

        async with self._session.get(SCHULPORTAL_MEINUNTERRICHT_URL) as response:
            content = await response.text()
            soup = getSoup(content)
            tasks = []
            for el in soup.find_all("tr", attrs={"class":"printable"}):
                if el.find(attrs={"class":"undone"}) is None:
                    continue
                subject = el.select_one('span[class="name"]')
                teacher = el.select_one('span.teacher > div.btn-group > button')
                topic = el.select_one('b[class="thema"]')
                date = el.select_one('span[class="datum"]')
                content = el.select_one('div.realHomework')
                task = {}
                if not subject is None:
                    task["topic"] = topic.extract().getText().strip()
                if not teacher is None:
                    task["teacher"] = teacher.extract().get("title", "").strip()
                if not topic is None:
                    task["topic"] = topic.extract().getText().strip()
                if not date is None:
                    task["date"] = date.extract().getText().strip()
                if not content is None:
                    task["content"] = content.extract().getText().strip()
                tasks.append(task)

            return tasks

    async def spoof_messages(self):
        if not self._loggedIn:
            raise NotSignedIn("Sign in first.")
        await self._session.get(SCHULPORTAL_NACHRICHTEN_URL)
        # requires RSA handshake and decrption:
        # GET ajax.php?f=rsaPublicKey
        # POST ajax.php?f=rsaHandshake&s={randint(0,2000)} {key:AES128 key self encrypted}
        async with self._session.post(
            SCHULPORTAL_NACHRICHTEN_URL,
            data=urlencode({
                "a": "headers",
                "getType": "visibleOnly",
                "last": "0"
            }),
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "X-Requested-With": "XMLHttpRequest"
            }
        ) as response:
            content = await response.text()
            print(content)


    async def list(self) -> list[dict[str, str]]:
        """
        Get a list of schools from the portal.

        Returns:
            list[dict[str:str]]: A list of dictionaries representing the schools, where each dictionary
            contains the keys 'school', 'city', and 'data-id'.
        """
        async with self._session.get(SCHULPORTAL_START_URL) as response:
            content = await response.text()
            soup = getSoup(content)
            toDict = lambda x: {"school": str(x[0]).strip(), "city": str(x[1]).strip()}
            return [
                {**toDict(tuple(el.strings)), "data-id": el.get("data-id")}
                for el in soup.find_all("a", attrs={"class": "list-group-item"})
            ]

    async def login(self, id: str):
        """
        Log in to the portal with the provided ID.

        Args:
            id: The ID of the portal to log in to.

        Raises:
            LoginFailed: If the login process fails.
        """
        async with self._session.get(SCHULPORTAL_LOGIN_URL, params={"i": str(id)}) as response:
            content = await response.text()
            soup = getSoup(content)
            form = {
                el.get("name"): el.get("value")
                for el in soup.select('input[type="hidden"]')
            }
            form.update({
                "user2": self.username,
                "user": f"{id}.{self.username}",
                "password": self.password,
            })

            await self._session.post(
                SCHULPORTAL_LOGIN_URL,
                params={"i": str(id)},
                data=urlencode(form),
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )

        async with self._session.get(SCHULPORTAL_START_URL, params={"i": str(id)}) as response:
            content = await response.text()
            soup = getSoup(content)
            errForm = soup.select_one('div[id="errorForm"]')

            if errForm is not None:
                [el.extract() for el in errForm.find_all("a")]
                raise LoginFailed(*buildArgs(errForm.getText()))

        self._loggedIn = True

    async def logout(self):
        """
        Log out from the portal.
        """
        await self._session.get(SCHULPORTAL_START_URL, params={"logout": "1"})
        self._loggedIn = False

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self._session.close()


async def main():
    """
    Main function to run the portal interaction flow.
    """
    async with Portal(SCHULPORTAL_USERNAME, SCHULPORTAL_PASSWORD) as portal:
        schools = await portal.list()
        print(next(filter(lambda x: x["data-id"] == SCHULPORTAL_SCHOOL_ID, schools)))
        await portal.login(SCHULPORTAL_SCHOOL_ID)
        try:
            await portal.check_substitutes()
        except NothingToReturn as ex:
            print(*ex.args)
        tasks = await portal.get_undone_homework()
        print(tasks)

        await portal.spoof_messages()
        await portal.logout()
