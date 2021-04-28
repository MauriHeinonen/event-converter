"""
Created on 28.4.2021

@author: Mauri Heinonen

With this application, you can convert event data, which is made with MyVideoAnalyser or Dartfish.

If you use this application, and you like to convert the MyVideoAnalyser timeline to fit in Dartfish,
you have to export the timeline from MyVideoAnalyser in JSON format.

If you like to convert the Dartfish
timeline to fit in MyVideoAnalyser, you have to export the timeline from Dartfish in CSV format.

Then this application converts source file data to destination file format.

You can convert at the same time multiple files and after converting, you can download those files,
what you like to save to your computer.
"""

import streamlit as st
import pandas as pd
import numpy as np
import os
import json
import re
import base64
from random import randint
import SessionState

def add_progress(bar, p, step):
    p += step
    bar.progress(p)
    return p

def parseJSONFile(df):
    parsedFile = pd.DataFrame()

    i = 0
    for key, value in df.iterrows():
        for row in value['rows']:
            for highlights in row['highlights']:
                parsedFile.at[i, 'Name'] = row['name']
                parsedFile.at[i, 'Position'] = highlights['start'] * 1000
                parsedFile.at[i, 'Duration'] = (highlights['end'] - highlights['start']) * 1000
                for event in highlights['events']:
                    pref = event['name'].split(':')
                    if (len(pref) > 1):
                        pref_key = pref[0]
                        pref_value = pref[1]
                        # if ( pref_value.isdigit() ):
                        if (re.match('^[0-9\.]*$', pref_value) and (('x' in pref_key) or ('y' in pref_key))):
                            pref_value = float(pref_value)

                        if (pref_key in ['Open', 'Penetration', 'Result', 'SP'] and pref_key in parsedFile.columns):
                            if (not pd.isnull(parsedFile[pref_key].iloc[i])):
                                pref_value = pref_value + ":" + parsedFile.at[i, pref_key]

                        parsedFile.at[i, pref_key] = pref_value
                    else:
                        parsedFile.at[i, pref[0]] = True
                i += 1

    parsedFile = parsedFile.replace(np.nan, '', regex=True)
    parsedFile = parsedFile.rename(columns={'\u2028': 'NL'})

    home_team = np.unique(parsedFile['Home'])
    home_team = np.delete(home_team, np.where(home_team == ''))[0]
    away_team = np.unique(parsedFile['Away'])
    away_team = np.delete(away_team, np.where(away_team == ''))[0]

    conditions = [
        (parsedFile['Name'].str.contains(home_team)),
        (parsedFile['Name'].str.contains(away_team))
    ]

    values = [home_team, away_team]
    parsedFile['Team'] = np.select(conditions, values)
    parsedFile['action'] = parsedFile['Name'].str.replace('{} - '.format(home_team), '')
    parsedFile['action'] = parsedFile['action'].str.replace('{} - '.format(away_team), '')
    parsedFile = parsedFile.sort_values(by=['Position'])
    parsedFile.index = np.arange(0, len(parsedFile))

    return parsedFile

# Start streamlit software  -  Pages head info, like title which is showed in head
st.set_page_config(
    page_title='CONVERT EVENT FILES',
    page_icon='favicon.ico',
    layout='centered',
    initial_sidebar_state='collapsed'
)

st.markdown('<link rel="stylesheet" href="https://use.fontawesome.com/releases/v5.11.2/css/all.css">', unsafe_allow_html=True)

st.markdown("""
<style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    body { color: #224B90; background-color: black; }
    .header { text-align: center; text-transform: uppercase; letter-spacing: 1.5px; line-height: 2rem; font-size: 2rem; font-weight: 800; }
    .paragraph { margin-top: 2rem; margin-bottom: 2rem; }
    .stButton>button { margin: 1rem auto; border: 1px solid #224B90; height: 2rem; width: 20rem; background-color: white; color: #224B90; text-transform: uppercase; letter-spacing: 1px; font-size: 0.9rem; font-weight: 200; border-radius: 45px; box-shadow: 0px 8px 15px rgba(0, 0, 0, 0.1); transition: all 0.3s ease 0s; cursor: pointer; outline: none;}
    .download_link { text-decoration: none; margin: 1rem auto; color: #224B90; text-transform: uppercase; letter-spacing: 1px; font-size: 0.9rem; font-weight: 400; cursor: pointer; outline: none;}
</style>
""", unsafe_allow_html=True)

st.markdown("<div class='header'>Convert event data file between Dartfish and MyVideoAnalyser</div>", unsafe_allow_html=True)
st.markdown("<div class='paragraph'>With this app, you can convert the Dartfish CSV file to XML format, which works with MyVideoAnalyser. After that, you can import this converted XML file to MyVideoAnalyser.</div>", unsafe_allow_html=True)
col = st.beta_columns(2)

csv_state = SessionState.get(widget_key='')
xml_state = SessionState.get(widget_key='')
if col[0].button('clear converted CSV files'):
    csv_state.widget_key = str(randint(1000, 100000000))

if col[1].button('clear converted XML files'):
    xml_state.widget_key = str(randint(1000, 100000000))


if not csv_state.widget_key:
    csv_state.widget_key = str(randint(1000, 100000000))

if not xml_state.widget_key:
    xml_state.widget_key = str(randint(1000, 100000000))

csv_files = col[0].file_uploader("CONVERT DARTFISH CSV FILE TO MYVA XML-FILE:",  type="csv", accept_multiple_files=True, key=csv_state.widget_key)
json_files = col[1].file_uploader("CONVERT MYVA JSON FILE TO DARTFISH:",  type="json", accept_multiple_files=True, key=xml_state.widget_key)

# CONVERT DARTFISH FILE
if len(csv_files) > 0:
    percent = 0
    max_bar = 100
    number_of_files = len(csv_files) if len(csv_files) == 1 else len(csv_files) + 1
    bar_step = (100 / number_of_files) / 100

    csv_bar = col[0].progress(percent)
    for csv_file in csv_files:
        file_name = os.path.splitext(csv_file.name)[0].replace(" ", "_")  + "-converted.xml"

        dataframe = pd.read_csv(csv_file)
        dataframe = dataframe.replace(np.nan, '', regex=True)

        xml_file = '<?xml version="1.0" encoding="UTF-8"?><file><ALL_INSTANCES>'
        rows = dataframe['Name'].unique()

        for i, row in dataframe.iterrows():
            xml_file += f"<instance><ID>{i}</ID><code>{row['Name']}</code>"
            start = row['Position'] / 1000
            end = start + row['Duration'] / 1000
            xml_file += f"<start>{start}</start><end>{end}</end>"

            # Add events
            for column in dataframe.columns:
                if (column not in ['Name', 'Position','Duration']):
                    if row[column] != '':
                        xml_file += f"<label><text>{column}:{row[column]}</text></label>"
            xml_file += "</instance>"

        xml_file += "</ALL_INSTANCES><ROWS>"
        for row in dataframe['Name'].unique():
            xml_file += f"<row><code>{row}</code><R>65536</R><G>65536</G><B>65536</B></row>"

        xml_file += "</ROWS></file>"

        if len(xml_file) > 0:
            b64 = base64.b64encode(xml_file.encode()).decode()
            col[0].markdown(f'<a  class="download_link" href="data:file/xml;base64,{b64}" download={file_name}><i class="fas fa-file-download"></i> Download {file_name}</a>', unsafe_allow_html=True)

        add_progress(csv_bar, percent, bar_step)

    csv_bar.progress(100)


# Convert MyVA event file to CSV file
if len(json_files) > 0:
    p = 0
    number_of_json_files = len(json_files) if len(json_files) == 1 else len(json_files) + 1
    json_bar_step = (100 / number_of_json_files) / 100

    json_bar = col[1].progress(p)
    for json_file in json_files:
        fn = os.path.splitext(json_file.name)[0].replace(" ", "_") + "-converted.csv"
        df = parseJSONFile(pd.json_normalize(json.load(json_file)))
        file_columns = df.columns
        dartfish_file = df.to_csv(encoding='utf-8', header=True, index=False).encode()

        if len(dartfish_file) > 0:
            b64 = base64.b64encode(dartfish_file).decode()
            col[1].markdown(f'<a  class="download_link" href="data:file/csv;base64,{b64}" download={fn}><i class="fas fa-file-download"></i> Download {fn}</a>', unsafe_allow_html=True)

        add_progress(json_bar, p, json_bar_step)

    json_bar.progress(100)
