class LoginFailed(Exception):
    """
    Exception raised on sign-in failure,
    """

class NotSignedIn(Exception):
    """
    Exception raised on premature requests.
    """

class NothingToReturn(Exception):
    """
    Exception raised when there is no content to return.
    """