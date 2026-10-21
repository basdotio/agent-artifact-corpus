import type { SpreadsheetContext } from "./types";

export const createSpreadSheet = async (
  title: string,
  context: SpreadsheetContext
): Promise<{ id: String; link: String | undefined | null }> => {
  try {
    const spreadsheet = await context.sheets.spreadsheets.create({
      requestBody: { properties: { title } },
      fields: "spreadsheetId,properties,sheets,spreadsheetUrl",
    });
    if (!spreadsheet.data || !spreadsheet.data.spreadsheetId) {
      throw new Error(
        "Failed to create spreadsheet: No spreadsheet ID returned"
      );
    }
   
    const id = spreadsheet.data.spreadsheetId!;
    const link = spreadsheet.data.spreadsheetUrl;
    try {
      await context.drive.permissions.create({
        fileId: id,
        requestBody: {
          type: "user",
          role: "writer", // or 'reader', 'commenter'
          emailAddress: "process.env.EMAIL_ID",
        },
        sendNotificationEmail: true, // optional: have Google send them an email
        fields: "id",
      });
    } catch (permissionError) {
      console.log("Error granting permissions:", permissionError);
    }
    if (context.folderId) {
      try {
        const file = await context.drive.files.get({
          fileId: id,
          fields: "parents",
        });
        const prev = file.data.parents?.join(",") || "";
        await context.drive.files.update({
          fileId: id,
          addParents: context.folderId,
          removeParents: prev,
          fields: "id, parents",
        });
      } catch (folderError) {
        console.error("Error moving to folder:", folderError);
      }
    }

    return { id, link };
  } catch (error) {
    console.error("Error in createSpreadSheet:", error);
    throw error;
  }
};


export const listSheets = async (spreadsheetId: string, context: SpreadsheetContext) => {
    const meta = await context.sheets.spreadsheets.get({spreadsheetId});
    return (meta.data.sheets?.map(s => s.properties?.title) || []);

}

export const renameSheet = async(spreadsheetId: string, sheetTitle: string, newName: string, context: SpreadsheetContext) => {
  const meta = await context.sheets.spreadsheets.get({ spreadsheetId });
  const sheetObj = meta.data.sheets?.find(s => s.properties?.title === sheetTitle);
  if(!sheetObj) return "Cannot find the sheet with the specified name"

  const body = {requests: [{ updateSheetProperties: { properties: { sheetId: sheetObj.properties?.sheetId, title: newName }, fields: 'title'}}]};
  const result = await context.sheets.spreadsheets.batchUpdate({ spreadsheetId, requestBody: body })
  return result
}

export const createSheet = async(spreadsheetId: string, title: string, context: SpreadsheetContext) => {
  const body = {requests: [{ addSheet: { properties: { title }}}]};
  const result = await context.sheets.spreadsheets.batchUpdate({ spreadsheetId, requestBody: body });
  const props = result.data.replies![0]?.addSheet!.properties;
  return {sheetId: props?.sheetId, title: props?.title, index: props?.index, spreadsheetId}
}

export const spreadsheetInfo = async(spreadsheetId: string, context: SpreadsheetContext) => {
  const meta = await context.sheets.spreadsheets.get({spreadsheetId});
  const info = { title: meta.data.properties?.title, sheets: meta.data.sheets?.map(s => ({ title: s.properties?.title, sheetId: s.properties?.sheetId, gridProperties: s.properties?.gridProperties}))};
  return info;
}

export const listSpreadsheets = async(context: SpreadsheetContext) => {
  let query = "mimeType='application/vnd.google-apps.spreadsheet'";
  if(context.folderId)
    query += ` and '${context.folderId}' in parents`;
  const list = await context.drive.files.list({ q: query, spaces: 'drive', fields: 'files(id, name)', orderBy: 'modifiedTime desc'});
  return list.data.files?.map(f => ({ id: f.id, title: f.name}));
}

export const shareSpreadsheet = async(spreadsheetId: string, recipients: {email_address: string, role: string}[], context: SpreadsheetContext) => {
  const successes = [];
  const failures = []
  for(const rec of recipients){
    const { email_address, role } = rec;
    if(!email_address || !['reader','commenter','writer'].includes(role)){
      failures.push({ email_address, error: 'Invalid Entry'});
      continue;
    }
    try{
      const perm = await context.drive.permissions.create({ fileId: spreadsheetId, requestBody: { type: 'user', role, emailAddress: email_address}, sendNotificationEmail: true, fields: 'id'})
      successes.push({ email_address, role, permissionId: perm.data.id});
    }catch(e: any){
      failures.push({ email_address, error: e.message})
    }
  }
  return {successes, failures};
}

export const sheetData = async(spreadsheetId: string, sheet: string, range: any, context: SpreadsheetContext) => {
  const fullRange = range ? `${sheet}!${range}`: sheet;
  const result = await context.sheets.spreadsheets.values.get({ spreadsheetId, range: fullRange });
  return result.data.values || []
}

export const updateCells = async(spreadsheetId: string, sheet: string, range: any, data: string[][], context: SpreadsheetContext) => {
  const fullRange = range ? `${sheet}!${range}`: sheet;
  const result = await context.sheets.spreadsheets.values.update({
    spreadsheetId,
    range: fullRange,
    valueInputOption: 'USER_ENTERED',
    requestBody: { values: data }
  });
  return result
}

export const batchUpdate = async(spreadsheetId: string, sheet: string, ranges: any[][], context: SpreadsheetContext) => {
  const data = Object.entries(ranges).map(([r, values]) => ({ range: `${sheet}!${r}`, values}))
  const result = await context.sheets.spreadsheets.values.batchUpdate({
    spreadsheetId,
    requestBody: { valueInputOption: 'USER_ENTERED', data }
  })
  return result.data
}

export const addRows = async(spreadsheetId: string, sheet: string, count: number, startRow: number, context: SpreadsheetContext) => {
  const meta = await context.sheets.spreadsheets.get({ spreadsheetId });
  const sheetObj = meta.data.sheets?.find(s => s.properties?.title === sheet)
  if(!sheetObj) return "Sheet Not found"
  const sheetId = sheetObj.properties?.sheetId;

  const requestBody = {
    requests: [{
      insertDimension: {
        range: {sheetId, dimension: 'ROWS', startIndex: startRow || 0, endIndex: (startRow || 0) + count },
        inheritFromBefore: !!startRow
      }
    }]
  }
  const result = await context.sheets.spreadsheets.batchUpdate({ spreadsheetId, requestBody });
  return result.data
}

export const addColumns = async(spreadsheetId: string, sheet: string, count: number, startColumn: number, context: SpreadsheetContext) => {
  const meta = await context.sheets.spreadsheets.get({ spreadsheetId })
  const sheetObj = meta.data.sheets?.find(s => s.properties?.title === sheet)
  if(!sheetObj) return "Sheet not found"
  const sheetId = sheetObj.properties?.sheetId;
  const requestBody = {
    requests: [{
      insertDimension: {
        range: {sheetId, dimension: 'COLUMNS', startIndex: startColumn || 0, endIndex: (startColumn || 0) + count },
        inheritFromBefore: !!startColumn
      }
    }]
  }
  const result = await context.sheets.spreadsheets.batchUpdate({ spreadsheetId, requestBody })
  return result.data
}

export const copySheet = async(srcSpreadsheet: string, srcSheet: string, dstSpreadsheet: string, dstSheet: string, context: SpreadsheetContext) => {
  const srcMeta = await context.sheets.spreadsheets.get({ spreadsheetId: srcSpreadsheet });
  const sheetObj = srcMeta.data.sheets?.find(s => s.properties?.title === srcSheet)
  if(!sheetObj) return "Source sheet not found"

  const copyRes = await context.sheets.spreadsheets.sheets.copyTo({ spreadsheetId: srcSpreadsheet, sheetId: sheetObj.properties!.sheetId!, requestBody: { destinationSpreadsheetId: dstSpreadsheet}})
  const copyId = copyRes.data.sheetId;
  if(dstSheet && copyRes.data.title !== dstSheet){
    const renameBody = { requests: [{ updateSheetProperties: { properties: { sheetId: copyId, title: dstSheet}, fields: 'title'}}]}
    const renameRes = await context.sheets.spreadsheets.batchUpdate({ spreadsheetId: dstSpreadsheet, requestBody: renameBody })
    return {copy: copyRes.data, rename: renameRes.data}
  }
  return {copy: copyRes.data}
}
