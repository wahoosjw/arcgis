import datetime
import json
import requests
import pandas
import os
import smtplib
from email.message import EmailMessage
from email.utils import make_msgid
import mimetypes
from os.path import basename
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import COMMASPACE, formatdate
import ssl


#list of various occupancy_ values to ignore
OCCUPANCY_IGNORE_LIST = ['DOUBLE WIDE MOBILE HOME',
                         'SINGLE WIDE MOBILE HOME',
                         'TOWNHOUSE-CONDOMINUM',
                         'VACANT LOTS W/MOBILE HOME']

FIELDS_TO_KEEP = ['occupancy_',
                  'owner_name',
                  'owner_addr',
                  'owner_city',
                  'owner_stat',
                  'owner_zip',
                  'legal_desc',
                  'considerat',
                  'consider_1',
                  'FULLADDR',
                  'ZipCode']


#function to query the API:
def apiQuery(queryLink):
    response_API = requests.get(queryLink)
    print(response_API.status_code)
    return response_API.text

def parse_data(dataText):
    parsed_json = json.loads(dataText)
    return parsed_json

# #TODO: rename this function
# def filterTime(jsonObj):
#     filtered_elements = []
#     if isinstance(jsonObj, list):
#         for element in jsonObj:
#             filtered_elements.extend(filterTime(element))
#     if isinstance(jsonObj, dict):
#         for key, value in jsonObj.items():
#             if key == 'consider_1':
#                 if value is not None:
#                     if value > 0:
#                         print(value)
#                         if timeCut(value):
#                             filtered_elements.append(jsonObj)
#             elif isinstance(value, (list, dict)):
#                 filtered_elements.extend(filterTime(value))
#     return filtered_elements

#TODO: add additional filter function to filter to a date range on consider_1
def filterConsiderat(jsonObj, minValue, minValueLandOnly):
    filtered_elements = []
    vacFlag = False
    whiteList = False

    if isinstance(jsonObj, list):
        for element in jsonObj:
            filtered_elements.extend(filterConsiderat(element,minValue, minValueLandOnly))
    elif isinstance(jsonObj, dict):
        for key, value in jsonObj.items():
            if key == 'occupancy_':
                if value == 'VACANT LAND':
                    vacFlag = True
                elif value in OCCUPANCY_IGNORE_LIST:
                    break
            elif key == 'considerat':
                if value > 500000:
                    print(f'Considerat: {value}. Adding...')
                    filtered_elements.append(jsonObj)
                elif vacFlag and  value > 100000:
                    print(f'Occupancy was VACANT LAND. Considerat: {value}. Adding...')
                    filtered_elements.append(jsonObj)
            elif isinstance(value, (list, dict)):
                filtered_elements.extend(filterConsiderat(value, minValue, minValueLandOnly))        
    return filtered_elements

def narrowJSON(jsonObj, fieldsToKeep):
    if isinstance(jsonObj, list):
        return [narrowJSON(item,fieldsToKeep) for item in jsonObj]
    elif isinstance(jsonObj, dict):
        if jsonObj['consider_1']:
            jsonObj['consider_1'] = helperTime(jsonObj['consider_1'])
        return {keepField: narrowJSON(jsonObj[keepField], fieldsToKeep) for keepField in fieldsToKeep if keepField in jsonObj}
    else:
        return jsonObj

# def timeCut(time):
#     timestamp_milliseconds = time  # Milliseconds since the epoch
#     timestamp_seconds = timestamp_milliseconds / 1000
#     now = datetime.datetime.now()
#     then = datetime.datetime.now() - datetime.timedelta(days=90)
#     time = datetime.datetime.fromtimestamp(timestamp_seconds)
#     isAdd = (then < time < now)
#     if isAdd:
#         print(f'Time was : {time} adding: {isAdd}')
#     return (isAdd)

def helperTime(time):
    print(f'Time: {time}')
    timestamp_milliseconds = time  # Milliseconds since the epoch
    timestamp_seconds = timestamp_milliseconds / 1000
    dt = datetime.datetime.fromtimestamp(timestamp_seconds)
    stringDT = dt.strftime("%m/%d/%Y %H:%M:%S")
    return stringDT

#TODO: Function to format the data in a format able to be emailed (xml? excel?)
def prettify(myData, myFile):
    pandas.DataFrame(myData).to_excel(myFile)
    #sort by date column pd data frame
    #sort by amounts?
    #sort by occupancy?

#TODO: function to send an email alert every run:
def findDates():#YYYY-MM-DD
    nowDT = datetime.datetime.now()
    thenDT = nowDT - datetime.timedelta(days = 90)

    now = nowDT.strftime("%Y-%m-%d")
    then = thenDT.strftime("%Y-%m-%d")

    return [now, then]
def emailMom(momsEmail, directoryLoc, xlsxFile, csvFile, now, then):
    msg = MIMEMultipart()
    excelFile = os.path.join(directoryLoc, xlsxFile)
    commaFile = os.path.join(directoryLoc, csvFile)

    msg['Subject'] = f'Report for {then} to {now}, '
    msg['From'] = 'samuel.welch@me.com'
    msg['Date'] = formatdate(localtime=True)
    msg['To'] = momsEmail
    text = "Please see attachment. Verify with manual data for first few weeks. Thanks, Sam"
    msg.attach(MIMEText(text))
    fileArr = [excelFile, commaFile]
    for file in fileArr:
        with open(file, 'rb') as f:
            part = MIMEApplication(f.read(), Name=basename(file))
        part['Content-Disposition'] = 'attachment; filename="%s"' % basename(file)
        msg.attach(part)


    mailserver = smtplib.SMTP('smtp.mail.me.com', 587)
    mailserver.ehlo()
    mailserver.starttls()
    mailserver.ehlo()
    mailserver.login("samuel.welch@me.com", 'ququ-amra-qpan-wifv')
    mailserver.sendmail('samuel.welch@me.com', momsEmail, msg.as_string())
        #smtp_server.quit()


#make this a main
now, then = findDates()
#myData = apiQuery(f'https://services9.arcgis.com/AzdpqVmJ5GjGWCoI/arcgis/rest/services/FranklinCoVA_TaxParcels_View/FeatureServer/0/query?where=1%3D1&outFields=*&outSR=4326&f=json')
print(now  + " " + then)
myData = apiQuery(f'https://services9.arcgis.com/AzdpqVmJ5GjGWCoI/arcgis/rest/services/FranklinCoVA_TaxParcels_View/FeatureServer/0/query?where=consider_1%3E%27{then}%27%20and%20consider_1%3C%27{now}%27&outFields=*&outSR=4326&f=json')
print(f'https://services9.arcgis.com/AzdpqVmJ5GjGWCoI/arcgis/rest/services/FranklinCoVA_TaxParcels_View/FeatureServer/0/query?where=consider_1%3E%27{then}%27%20and%20consider_1%3C%27{now}%27&outFields=*&outSR=4326&f=json')
print(myData)

parsedData = parse_data(myData)
#filteredTime = filterTime(parsedData)
filteredData = filterConsiderat(parsedData, 500000, 100000)
narrowData = narrowJSON(filteredData, FIELDS_TO_KEEP)
f = "samTest.xlsx"
prettify(narrowData, f)


with open("samTest.txt", "w") as f:
    json.dump(narrowData, f)

emailMom('barry.welch@hey.com', 'C:\\Users\\wahoo\\Documents\\Programming', 'samTest.xlsx', 'samTest.txt', now, then)