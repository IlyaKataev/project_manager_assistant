import gspread
import logging
import os

from google.oauth2.service_account import Credentials
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

load_dotenv()


class GSheetsClient:
    def __init__(self):
        scope = [
            'https://www.googleapis.com/auth/spreadsheets',
            'https://www.googleapis.com/auth/drive.file',
            'https://www.googleapis.com/auth/drive'
        ]

        credentials_file = os.getenv('CREDENTIALS_FILE')

        try:
            credentials = Credentials.from_service_account_file(credentials_file, scopes=scope)
            self.gc = gspread.authorize(credentials)
            logger.info("Google Sheets client inited successfully")
        except Exception as e:
            logger.error(f"Failed to init Google Sheets client: {str(e)}", exc_info=True)
            raise

    def get_sheet_data(self, spreadsheet_id, sheet_name='Лист1'):
        try:
            sheet = self.gc.open_by_key(spreadsheet_id).worksheet(sheet_name)
            return sheet.get()
        except Exception as e:
            logger.error(f"Failed to get sheet data for {spreadsheet_id}: {str(e)}")
            return None

    def update_sheet_data(self, spreadsheet_id, sheet_name, data):
        try:
            sheet = self.gc.open_by_key(spreadsheet_id).worksheet(sheet_name)
            sheet.update(data)
            logger.info(f"Updated sheet {spreadsheet_id} with {len(data)} rows")
            return True
        except Exception as e:
            logger.error(f"Failed to update sheet {spreadsheet_id}: {str(e)}")
            return False

    def update_cell(self, spreadsheet_id, sheet_name, row, col, value):
        try:
            sheet = self.gc.open_by_key(spreadsheet_id).worksheet(sheet_name)
            sheet.update_cell(row, col, value)
            logger.info(f"Updated cell ({row},{col}) in sheet {spreadsheet_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to update cell in sheet {spreadsheet_id}: {str(e)}")
            return False