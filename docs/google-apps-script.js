function doPost(e) {
  const API_KEY = 'meteoro';
  const spreadsheet = SpreadsheetApp.getActiveSpreadsheet();
  const sheet = spreadsheet.getSheetByName('Registros') || spreadsheet.insertSheet('Registros');
  const data = JSON.parse(e.postData.contents);

  if (data.apiKey !== API_KEY) {
    return ContentService
      .createTextOutput(JSON.stringify({ ok: false, error: 'unauthorized' }))
      .setMimeType(ContentService.MimeType.JSON);
  }

  sheet.appendRow([
    new Date(),
    data.dataHora || '',
    data.tipo || '',
    data.alerta || '',
    JSON.stringify(data.dados || {})
  ]);

  return ContentService
    .createTextOutput(JSON.stringify({ ok: true }))
    .setMimeType(ContentService.MimeType.JSON);
}
