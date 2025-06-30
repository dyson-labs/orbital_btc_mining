# -*- coding: utf-8 -*-
"""
Created on Sat Jun 28 02:46:36 2025

@author: elder
"""

import gspread
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ['https://www.googleapis.com/auth/spreadsheets']

def authenticate_gsheets():
    # The client_secret.json file downloaded from Google Cloud
    flow = InstalledAppFlow.from_client_secrets_file('client.json', SCOPES)
    creds = flow.run_local_server(port=8080)
    return creds

def open_sheet(sheet_url, creds):
    gc = gspread.authorize(creds)
    sh = gc.open_by_url(sheet_url)
    worksheet = sh.get_worksheet(0)  # First tab
    data = worksheet.get_all_records()
    return data

if __name__ == "__main__":
    creds = authenticate_gsheets()
    sheet_url = 'https://docs.google.com/spreadsheets/d/PASTE_YOUR_SHEET_ID_OR_URL_HERE'
    data = open_sheet(sheet_url, creds)
    print(data)
