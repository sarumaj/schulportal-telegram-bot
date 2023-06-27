import os
from portal import Portal

USERNAME = os.environ["SCHULPORTAL_USERNAME"]
PASSWORD = os.environ["SCHULPORTAL_PASSWORD"]

def main():
    portal = Portal(USERNAME, PASSWORD)
    portal.login("5114")
    portal.logout()

if __name__ == '__main__':
    main()