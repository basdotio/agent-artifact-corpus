import {google, sheets_v4, drive_v3} from 'googleapis'
export interface SpreadsheetContext {
  sheets: sheets_v4.Sheets;
  drive: drive_v3.Drive;
  folderId?: string;
}