from fastapi import FastAPI, Path, Query
import pandas as pd
import os
from typing import Union
from datetime import datetime
pd.options.mode.chained_assignment = None  # default='warn'
data_file = "dati_presenze_politici.parquet"
data_file_url = "https://github.com/g0v-it/agcom/raw/main/data/"
data = None
localstorage = False
if os.path.exists(data_file):
    data = pd.read_parquet(data_file)
    localstorage = True
else:
    data = pd.read_parquet(data_file_url + data_file)

checkitaliandate = '(?:(?:(?:0[1-9]|1\d|2[0-8])\/(?:0[1-9]|1[0-2])|(?:29|30)\/(?:0[13-9]|1[0-2])|31\/(?:0[13578]|1[02]))\/[1-9]\d{3}|29\/02(?:\/[1-9]\d(?:0[48]|[2468][048]|[13579][26])|(?:[2468][048]|[13579][26])00))'
checkcategoryinformation = '^(speech|both|news)$'
from_day = data.DATA.min().strftime('%d/%m/%Y')
to_day = data.DATA.max().strftime('%d/%m/%Y')

data.rename(columns={'CANALE': 'channel', 'PROGRAMMA': 'program', 'DATA':'day', 
                     'COGNOME':'lastname','NOME':'name',
                     'MICRO_CATEGORIA':'affiliation',
                     'ARGOMENTO': 'topic', 'DURATA': 'minutes_of_information',
                     'TIPO_TEMPO':'category_information'}, inplace=True)

description = """
## AGCOM - elementary data of the italian television monitoring

This API provides the possibility to query the elementary televised monitoring data provided by [AGCOM](https://www.agcom.it/) - Italian authority for guarantees in communications - of political interventions (data as news or as word)

The data can be found in XML format at [https://www.agcom.it/dati-elementari-di-monitoraggio-televisivo](https://www.agcom.it/dati-elementari-di-monitoraggio-televisivo)

Period:<br/>
from **%s** to **%s**


The license under which the data is released by AGCOM is CC-BY-SA-NC

![](https://www.agcom.it/documents/10179/4502194/Logo+Creative+common/2e1fe5a2-4324-4965-b8af-76403bb42b15?t=1618583317352)


A project of [Copernicani Association](https://copernicani.it) and [napo](https://twitter.com/napo)
<br/> 
<p style="background-color: green;">
<img src="https://copernicani.it/wp-content/uploads/2020/10/logo-in-bianco.png" width="250px"/>
</p>
""" % (from_day, to_day)

app = FastAPI(
    docs_url="/", redoc_url=None,
    title="AGCOM - dati elementari di monitoraggio televisivo",
    description=description,
    version="0.6.0",
    contact={
        "name": "napo",
        "url": "https://twitter.com/napo"
    }, 
    license_info={
        "name": "data under cc-by-nc-sa",
        "url": "https://creativecommons.org/licenses/by-nc-sa/4.0/"
    },
)


data_collective_subjects = data[data.name == "Soggetto Collettivo"]
data_politicians = data[data.name != "Soggettivo Collettivo"]
data_politicians = data_politicians[data_politicians.name !=
                                    "Soggetto Collettivo"]
data_politicians['name_lastname'] = data_politicians['name'] + \
    " " + data_politicians['lastname']

politicians_columns = data_politicians.columns
exclude_politicians_columns = ['name', 'lastname', 'name_lastname']
selected_politicians_columns = list(
    set(politicians_columns).difference(set(exclude_politicians_columns)))

def getdfinterval(startday,endday, df):
    if (startday == from_day):
        startday = df.day.min().strftime('%d/%m/%Y')

    if (endday == to_day):
        endday = df.day.max().strftime('%d/%m/%Y')
    
    startday = datetime.strptime(startday, '%d/%m/%Y')
    endday = datetime.strptime(endday, '%d/%m/%Y')
    
    # if (startday > endday):
    #     invday = startday
    #     startday = endday 
    #     endday = invday 
    
    if (endday == startday):
        df = df[(df.day == startday)]
    else:
        df = df[(df.day >= startday) & (df.day <= endday)]

    try:
        startday = startday.strftime('%d/%m/%Y')
        endday = endday.strftime('%d/%m/%Y')
    except Exception as e:
        pass
    return(startday,endday,df)

def changeParolaNotizia(x):
    if x == "Notizia":
        x = "news"
    if x == "Parola":
        x = "speech"
    return(x)

def checkParolaNotizia(df):
    if "news" in df.columns:
        df['news'] = df['news'].astype('int')
    else:
        df['news'] = 0
    if "speech" in df.columns:
        df['speech'] = df['speech'].astype('int')
    else:
        df['speech'] = 0
    return(df)

def dfpivottable(df, indexvalue, columnsvalue, aggvalues="minutes_of_information"):
    rdata = df.pivot_table(index=indexvalue, columns=columnsvalue,values=aggvalues, aggfunc=sum).reset_index()
    rdata = rdata.fillna(0)
    if "Notizia" in rdata.columns:
        rdata['Notizia'] = rdata['Notizia'].astype('int')
    else:
        rdata['Notizia'] = 0
    if "Parola" in rdata.columns:
        rdata['Parola'] = rdata['Parola'].astype('int')
    else:
        rdata['Parola'] = 0
    rdata.rename(columns={'Notizia': 'news', 'Parola': 'speech'}, inplace=True)
    rdata['total'] = rdata['news'] + rdata['speech']
    return(rdata)


@app.get("/status")
async def get():
    """
    Return information about the data storage
    """
    message = {}
    message['local_storage'] = localstorage
    return {"message":message}

@app.get("/period") #, tags=["period"])
async def get():
    """
    returns information on the time window of the available data<br/>
    The time unit is the day (format DD/MM/YYYY)
    """
    period = {}
    period['from'] = from_day
    period['to'] = to_day
    return {"period": period}

@app.get("/politicians")
async def get(startday: Union[str, None] = Query(default=from_day, description="start day of the time window", min_length=10, max_length=10, regex=checkitaliandate), endday: Union[str, None] = Query(default=to_day, description="end day of the time window", min_length=10, max_length=10, regex=checkitaliandate), filter: Union[str, None] = Query(default='both', regex=checkcategoryinformation)):
    """
    returns the list of the politicians with information on the minutes of "speech" and "news" in a given time window<br/>
    The time unit is the day (format DD/MM/YYYY)   
    """
    ndata = data_politicians
    if filter == 'speech':
        ndata = data_politicians[data_politicians.category_information == 'Parola']
    if filter == 'news':
        ndata = data_politicians[data_politicians.category_information == 'Notizia']

    startday, endday, ndata=getdfinterval(startday, endday, ndata)

    senddata_politicians = {}
    senddata_politicians['from'] = startday
    senddata_politicians['to'] = endday

    ndata = ndata.pivot_table(index="name_lastname", columns="category_information",
                              values="minutes_of_information", aggfunc=sum).reset_index()
    ndata = ndata.fillna(0)
    if "Notizia" in ndata.columns:
        ndata['Notizia'] = ndata['Notizia'].astype('int')
    else:
        ndata['Notizia'] = 0
    if "Parola" in ndata.columns:
        ndata['Parola'] = ndata['Parola'].astype('int')
    else:
        ndata['Parola'] = 0
    ndata.rename(columns={'Notizia': 'news', 'Parola': 'speech'}, inplace=True)
    ndata['total'] = ndata['news'] + ndata['speech']
    senddata_politicians['politicians'] = ndata.sort_values(["total", "name_lastname"], ascending=[
        False, True]).to_dict('records')
    return {"data": senddata_politicians}


@app.get("/politicians/list")
async def get(startday: Union[str, None] = Query(default=from_day, description="start day of the time window", min_length=10, max_length=10, regex=checkitaliandate), 
              endday: Union[str, None]=Query(default=to_day, description="end day of the time window", min_length=10, max_length=10, regex=checkitaliandate),
            filter: Union[str, None] = Query(default='both', regex=checkcategoryinformation)):
    """
    returns the list of the politicians in a given time window<br/>
    The time unit is the day (format DD/MM/YYYY)    
    """
    ndata = data_politicians
    if filter == 'speech':
        ndata = data_politicians[data_politicians.category_information == 'Parola']
    if filter == 'news':
        ndata = data_politicians[data_politicians.category_information == 'Notizia']

    startday, endday, ndata=getdfinterval(
        startday, endday, ndata)
    ndata = ndata.sort_values(["lastname", "name"])
    senddata = {}
    senddata['from'] = startday
    senddata['to'] = endday
    senddata['politicians'] = list(ndata.name_lastname.unique())
    return {"data": senddata}

@app.get("/politician/{name_lastname}")
async def get(name_lastname: str = Path(description="name and lastname of the politician"), 
              startday: Union[str, None] = Query(default=from_day, description="start day of the time window", min_length=10, max_length=10, regex=checkitaliandate), 
              endday: Union[str, None]=Query(default=to_day, description="end day of the time window", min_length=10, max_length=10, regex=checkitaliandate),
                filter: Union[str, None] = Query(default='both', regex=checkcategoryinformation)):
    """
    returns all the data of a single politician in a given time window<br/>
    The time unit is the day (format DD/MM/YYYY)  
    """
    ndata = data_politicians
    if filter == 'speech':
        ndata = data_politicians[data_politicians.category_information == 'Parola']
    if filter == 'news':
        ndata = data_politicians[data_politicians.category_information == 'Notizia']

    name_lastname = name_lastname.title()
    politician_data = {}
    affiliations = "not present"
    politician = ndata[ndata['name_lastname'].str.title(
    ) == name_lastname]
    if politician.shape[0] > 0:
        startday, endday, politician = getdfinterval(
            startday, endday, politician)
        affiliations = list(politician.affiliation.unique())
        politician.day = politician.day.apply(lambda x: x.strftime('%d/%m/%Y'))
        politician_data['politician'] = name_lastname
        politician_data['affiliations'] = affiliations
        politician_data['from'] = startday
        politician_data['to'] = endday
        politician.category_information = politician.category_information.apply(
            lambda x: changeParolaNotizia(x))
        raw_data = politician[selected_politicians_columns].to_dict('records')
        politician_data['television_presence'] = raw_data
    return {"data": politician_data}


@app.get("/politician/{name_lastname}/stats")
async def get(name_lastname: str = Path(description="name and lastname of the politician"), 
              startday: Union[str, None] = Query(default=from_day, description="start day of the time window", min_length=10, max_length=10, regex=checkitaliandate), 
              endday: Union[str, None]=Query(default=to_day, description="end day of the time window", min_length=10, max_length=10, regex=checkitaliandate),
            filter: Union[str, None] = Query(default='both', regex=checkcategoryinformation)):
    """
    returns statical data of a single politician in a given time window<br/>
    The time unit is the day (format DD/MM/YYYY)<br/><br/>
    Statistics collected:
    - affiliations with which the politician presented himself
    - total minutes of speech
    - total minutes of news
    - total minutes of presence
    - average daily minutes
    - total days of presence
    - distribution of minutes by topics
    - distribution of minutes by television channel
    - distribution of minutes for television programs
    """
    ndata = data_politicians
    if filter == 'speech':
        ndata = data_politicians[data_politicians.category_information == 'Parola']
    if filter == 'news':
        ndata = data_politicians[data_politicians.category_information == 'Notizia']

    name_lastname = name_lastname.title()
    affiliations = "not present"
    presence = ""
    time_topics = ""
    time_channels = ""
    time_topics = ""
    time_programs = ""
    politician = ndata[ndata['name_lastname'].str.title()
                                  == name_lastname]

    if politician.shape[0] > 0:
        startday, endday, politician = getdfinterval(
            startday, endday, politician)
        affiliations = list(politician.affiliation.unique())
        daily_minutes_average = round(
        politician.minutes_of_information.sum() / politician.shape[0], 2)
        total_days = len(politician.day.unique())
        presencedata = dfpivottable(politician,
                                    indexvalue="name_lastname",
                                    columnsvalue="category_information")
        del presencedata['name_lastname']
        presence = presencedata.to_dict('records')[0]
        time_topics = politician.groupby('topic').aggregate('sum')
        time_topics.rename(
            columns={"minutes_of_information": "time_topics"}, inplace=True)
        time_topics = time_topics.to_dict()['time_topics']
        time_channels = politician.groupby('channel').aggregate('sum')
        time_channels.rename(
            columns={"minutes_of_information": "time_channel"}, inplace=True)
        time_channels = time_channels.sort_values(by=["time_channel", "channel"], ascending=[
                                                  False, False]).to_dict()['time_channel']
        time_programs = politician.groupby('program').aggregate('sum')
        time_programs.rename(
            columns={"minutes_of_information": "time_programs"}, inplace=True)
        time_programs = time_programs.sort_values(by=["time_programs", "program"], ascending=[
                                                  False, False]).to_dict()['time_programs']

    stats = {}
    stats['politician'] = name_lastname
    stats['affiliations'] = affiliations
    stats['from'] = startday
    stats['to'] = endday
    stats['presence_minutes'] = presence
    stats['daily_minutes_average'] = daily_minutes_average
    stats['total_days'] = total_days
    stats['time_topics'] = time_topics
    stats['time_channels'] = time_channels
    stats['time_programs'] = time_programs
    return {"data": stats}


@app.get("/affiliations")
async def get(startday: Union[str, None] = Query(default=from_day, description="start day of the time window", min_length=10, max_length=10, regex=checkitaliandate), 
              endday: Union[str, None] = Query(default=to_day, description="end day of the time window", min_length=10, max_length=10, regex=checkitaliandate),
              filter: Union[str, None] = Query(default='both', regex=checkcategoryinformation)):
    """
    returns the list of the affiliations of each politician in a given time window<br/>
    The time unit is the day (format DD/MM/YYYY)
    """
    ndata = data
    if filter == 'speech':
        ndata = data[data.category_information == 'Parola']
    if filter == 'news':
        ndata = data[data.category_information == 'Notizia']

    startday, endday, ndata = getdfinterval(startday, endday, ndata)
    senddata = {}
    senddata['from'] = startday
    senddata['to'] = endday
    senddata['affiliations'] = list(ndata.affiliation.unique())
    return {'data': senddata}

@app.get("/collectivesubjects")
async def get(startday: Union[str, None] = Query(default=from_day, description="start day of the time window", min_length=10, max_length=10, regex=checkitaliandate), endday: Union[str, None] = Query(default=to_day, description="end day of the time window", min_length=10, max_length=10, regex=checkitaliandate), 
              filter: Union[str, None] = Query(default='both', regex=checkcategoryinformation)):
    """
    returns the list of the collective subjects with information on the minutes of "speech" and "news" in a given time window<br/>
    The time unit is the day (format DD/MM/YYYY)   
    """
    ndata = data_collective_subjects
    if filter == 'speech':
        ndata = ndata[ndata.category_information == 'Parola']
    if filter == 'news':
        ndata = ndata[ndata.category_information == 'Notizia']
    startday, endday, ndata = getdfinterval(
        startday, endday, ndata)
    senddata_collective_subjects = {}
    senddata_collective_subjects['from'] = startday
    senddata_collective_subjects['to'] = endday
    ndata = ndata.pivot_table(index="lastname", columns="category_information",
                              values="minutes_of_information", aggfunc=sum).reset_index()
    ndata = ndata.fillna(0)
    if "Notizia" in ndata.columns:
        ndata['Notizia'] = ndata['Notizia'].astype('int')
    else:
        ndata['Notizia'] = 0
    if "Parola" in ndata.columns:
        ndata['Parola'] = ndata['Parola'].astype('int')
    else:
        ndata['Parola'] = 0
    ndata.rename(columns={'Notizia': 'news', 'Parola': 'speech'}, inplace=True)
    ndata['total'] = ndata['news'] + ndata['speech']
    ndata.rename(columns={'lastname': 'collective_subject'}, inplace=True)
    senddata_collective_subjects['collectivesubjects'] = ndata.sort_values(["total", "collective_subject"], ascending=[
        False, True]).to_dict('records')

    return {'data': senddata_collective_subjects}


@app.get("/collectivesubjects/list")
async def get(startday: Union[str, None] = Query(default=from_day, description="start day of the time window", min_length=10, max_length=10, regex=checkitaliandate), endday: Union[str, None] = Query(default=to_day, description="end day of the time window", min_length=10, max_length=10, regex=checkitaliandate), filter: Union[str, None] = Query(default='both', regex=checkcategoryinformation)):
    """
    returns the list of the collective political subjects in a given time window<br/>
    The time unit is the day (format DD/MM/YYYY)    
    """
    ndata = data_collective_subjects
    if filter == 'speech':
        ndata = ndata[ndata.category_information == 'Parola']
    if filter == 'news':
        ndata = ndata[ndata.category_information == 'Notizia']    
    startday, endday, ndata = getdfinterval(
        startday, endday, data_collective_subjects)
    
    ndata = ndata.sort_values(["lastname"])
    senddata = {}
    senddata['from'] = startday
    senddata['to'] = endday
    senddata['collectivesubjects'] = list(ndata.lastname.unique())

    return {'data': senddata}

@app.get("/collectivesubject/{name}")
async def get(name: str = Path(description="name of the political collective subject"), startday: Union[str, None] = Query(default=from_day, description="start day of the time window", min_length=10, max_length=10, regex=checkitaliandate), endday: Union[str, None] = Query(default=to_day, description="end day of the time window", min_length=10, max_length=10, regex=checkitaliandate), filter: Union[str, None] = Query(default='both', regex=checkcategoryinformation)):
    """
    returns all the data of a collective political subject in a given time window<br/>
    The time unit is the day (format DD/MM/YYYY)  
    """
    ndata = data_collective_subjects
    if filter == 'speech':
        ndata = ndata[ndata.category_information == 'Parola']
    if filter == 'news':
        ndata = ndata[ndata.category_information == 'Notizia']
        
    name = name.title()
    collectivesubject_data = {}
    collectivesubject = ndata[ndata['lastname'].str.title(
    ) == name]
    if collectivesubject.shape[0] > 0:
        startday, endday, collectivesubject = getdfinterval(
            startday, endday, collectivesubject)
        collectivesubject.day = collectivesubject.day.apply(
            lambda x: x.strftime('%d/%m/%Y'))
        collectivesubject_data['collectivesubject'] = name
        collectivesubject_data['from'] = startday
        collectivesubject_data['to'] = endday
        collectivesubject.category_information = collectivesubject.category_information.apply(
            lambda x: changeParolaNotizia(x))
        raw_data = collectivesubject[selected_politicians_columns].to_dict('records')
        collectivesubject_data['television_presence'] = raw_data
    return {"data": collectivesubject_data}

@app.get("/collectivesubject/{name}/stats")
async def get(name: str = Path(description="name of the political collective subject"), startday: Union[str, None] = Query(default=from_day, description="start day of the time window", min_length=10, max_length=10, regex=checkitaliandate), endday: Union[str, None] = Query(default=to_day, description="end day of the time window", min_length=10, max_length=10, regex=checkitaliandate),filter: Union[str, None] = Query(default='both', regex=checkcategoryinformation)):
    """
    returns statical data of a collective political subject in a given time window<br/>
    The time unit is the day (format DD/MM/YYYY)<br/><br/>
    Statistics collected:
    - affiliations with which the politician presented himself
    - total minutes of presence
    - distribution of minutes by topics
    - distribution of minutes by television channel
    - distribution of minutes for television programs
    """
    ndata = data_collective_subjects
    if filter == 'speech':
        ndata = ndata[ndata.category_information == 'Parola']
    if filter == 'news':
        ndata = ndata[ndata.category_information == 'Notizia']
    name = name.title()
    
    presence = ""
    time_topics = ""
    time_channels = ""
    time_topics = ""
    time_programs = ""
    collectivesubject = ndata[ndata['lastname'].str.title(
    ) == name]

    if collectivesubject.shape[0] > 0:
        startday, endday, collectivesubject = getdfinterval(
            startday, endday, collectivesubject)
        presence = int(collectivesubject.minutes_of_information.sum())
        time_topics = collectivesubject.groupby('topic').aggregate('sum')
        time_topics.rename(
            columns={"minutes_of_information": "time_topics"}, inplace=True)
        time_topics = time_topics.to_dict()['time_topics']
        time_channels = collectivesubject.groupby('channel').aggregate('sum')
        time_channels.rename(
            columns={"minutes_of_information": "time_channel"}, inplace=True)
        time_channels = time_channels.sort_values(by=["time_channel", "channel"], ascending=[
                                                  False, False]).to_dict()['time_channel']
        time_programs = collectivesubject.groupby('program').aggregate('sum')
        time_programs.rename(
            columns={"minutes_of_information": "time_programs"}, inplace=True)
        time_programs = time_programs.sort_values(by=["time_programs", "program"], ascending=[
                                                  False, False]).to_dict()['time_programs']
    stats = {}
    stats['collectivesubject'] = name
    stats['from'] = startday
    stats['to'] = endday
    stats['presence_minutes'] = presence
    stats['time_topics'] = time_topics
    stats['time_channels'] = time_channels
    stats['time_programs'] = time_programs
    return {"data": stats}

@app.get("/topics")
async def get(startday: Union[str, None] = Query(default=from_day, description="start day of the time window", min_length=10, max_length=10, regex=checkitaliandate), endday: Union[str, None] = Query(default=to_day, description="end day of the time window", min_length=10, max_length=10, regex=checkitaliandate), filter: Union[str, None] = Query(default='both', regex=checkcategoryinformation)):
    """
    returns the list of the topics in a given time window<br/>
    The time unit is the day (format DD/MM/YYYY)   
    """
    ndata = data
    if filter == 'speech':
        ndata = ndata[ndata.category_information == 'Parola']
    if filter == 'news':
        ndata = ndata[ndata.category_information == 'Notizia']
    name = name.title()
    startday, endday, ndata = getdfinterval(
        startday, endday, ndata)
    
    senddata = {}
    senddata['from'] = startday
    senddata['to'] = endday
    senddata['topics'] = list(ndata.topic.unique())
    return {'data': senddata}

@app.get("/topic/{name}")
async def get(name: str = Path(description="name of the topic"), startday: Union[str, None] = Query(default=from_day, description="start day of the time window", min_length=10, max_length=10, regex=checkitaliandate), endday: Union[str, None] = Query(default=to_day, description="end day of the time window", min_length=10, max_length=10, regex=checkitaliandate), filter: Union[str, None] = Query(default='both', regex=checkcategoryinformation)):
    """
    returns all the data of a topic in a given time window<br/>
    The time unit is the day (format DD/MM/YYYY)  
    """
    ndata = data
    if filter == 'speech':
        ndata = ndata[ndata.category_information == 'Parola']
    if filter == 'news':
        ndata = ndata[ndata.category_information == 'Notizia']
    name = name.title()
    startday, endday, ndata = getdfinterval(
        startday, endday, ndata)
    name = name.title()
    topic_data = {}
    ndata = ndata[ndata['topic'].str.title() == name]
    if ndata.shape[0] > 0:
        startday, endday, ndata = getdfinterval(startday, endday, ndata)
        ndata.day = ndata.day.apply(lambda x: x.strftime('%d/%m/%Y'))
        topic_data['topic'] = name
        #topic_data['channels'] = channel
        topic_data['from'] = startday
        topic_data['to'] = endday
        ndata.category_information = ndata.category_information.apply(
            lambda x: changeParolaNotizia(x))
        raw_data = ndata.to_dict('records')
        topic_data['topic_history'] = raw_data
    return {"data": topic_data}

@app.get("/topic/{name}/stats")
async def get(name: str = Path(description="name of the topic"), startday: Union[str, None] = Query(default=from_day, description="start day of the time window", min_length=10, max_length=10, regex=checkitaliandate), endday: Union[str, None] = Query(default=to_day, description="end day of the time window", min_length=10, max_length=10, regex=checkitaliandate), filter: Union[str, None] = Query(default='both', regex=checkcategoryinformation)):
    """
    returns statical data of a topic in a given time window<br/>
    The time unit is the day (format DD/MM/YYYY)<br/><br/>
    Statistics collected:
    - daily minutes average
    - total days 
    - total minutes of speech
    - total minutes of news
    - the minutes by each individual politician on the topic
    - the minutes of each political collective subject on the topic
    - the minutes for each italian television channel
    - the minutes for each italian television program
    """
    ndata = data
    if filter == 'speech':
        ndata = ndata[ndata.category_information == 'Parola']
    if filter == 'news':
        ndata = ndata[ndata.category_information == 'Notizia']
    name = name.title()
    startday, endday, ndata = getdfinterval(
        startday, endday, ndata)
    name = name.title()
    topic_data = {}
    ndata = ndata[ndata['topic'].str.title() == name]
    daily_minutes_average = round(
        ndata.minutes_of_information.sum() / ndata.shape[0], 2)

    if ndata.shape[0] > 0:
        startday, endday, ndata = getdfinterval(startday, endday, ndata)
        ndata.day = ndata.day.apply(lambda x: x.strftime('%d/%m/%Y'))
        topic_data['topic'] = name.title()
        topic_data['from'] = startday
        topic_data['to'] = endday
        daily_minutes_average = round(
            ndata.minutes_of_information.sum() / ndata.shape[0], 2)
        topic_data['daily_minutes_average'] = daily_minutes_average
        topic_data['total_days'] = len(ndata.day.unique())
        ndata.category_information = ndata.category_information.apply(
            lambda x: changeParolaNotizia(x))
        tmi = ndata.groupby(by="category_information")[
            'minutes_of_information'].sum().to_frame().T
        tmi = checkParolaNotizia(tmi)
        tmi['total'] = tmi['news'] + tmi['speech']
        topic_data['category_information'] = tmi.to_dict('records')[0]
        ndata_collective_subjects = ndata[ndata.name == "Soggetto Collettivo"]
        ndata_politicians = ndata[ndata.name != "Soggettivo Collettivo"]
        ndata_politicians = ndata_politicians[ndata_politicians.name !=
                                              "Soggetto Collettivo"]
        ndata_politicians['name_lastname'] = ndata_politicians['name'] + \
            " " + ndata_politicians['lastname']
        topic_data['politician_minutes'] = []
        topic_data['collective_subjects_minutes'] = []
        topic_data['channels'] = ndata[ndata.topic.str.title() == name].groupby(by="channel")[
            'minutes_of_information'].sum().to_frame().sort_values(by="minutes_of_information", ascending=False).T.to_dict('records')[0]
        topic_data['programs'] = ndata[ndata.topic.str.title() == name].groupby(by="program")[
            'minutes_of_information'].sum().to_frame().sort_values(by="minutes_of_information", ascending=False).T.to_dict('records')[0]
        if ndata_politicians.shape[0] > 0:
            tmp = ndata_politicians.groupby(by="name_lastname")[
                'minutes_of_information'].sum().to_frame().sort_values(by="minutes_of_information", ascending=False).T
            topic_data['politician_minutes'] = tmp.to_dict('records')[0]
        if ndata_collective_subjects.shape[0]:
            tms = ndata_collective_subjects.groupby(by="lastname")[
                'minutes_of_information'].sum().to_frame().sort_values(by="minutes_of_information", ascending=False).T
            topic_data['collective_subjects_minutes'] = tms.to_dict('records')[
                0]

    return {"data": topic_data}

@app.get("/programs")
async def get(startday: Union[str, None] = Query(default=from_day, description="start day of the time window", min_length=10, max_length=10, regex=checkitaliandate), endday: Union[str, None] = Query(default=to_day, description="end day of the time window", min_length=10, max_length=10, regex=checkitaliandate), filter: Union[str, None] = Query(default='both', regex=checkcategoryinformation)):
    """
    returns the list of the italian television **programs** available on a given time window<br/>
    The format of the date is DD/MM/YYYY
    """
    ndata = data
    if filter == 'speech':
        ndata = ndata[ndata.category_information == 'Parola']
    if filter == 'news':
        ndata = ndata[ndata.category_information == 'Notizia']
    programs_data = {}
    startday, endday, ndata = getdfinterval(startday, endday, ndata)
    programs_data['from'] = startday
    programs_data['to'] = endday
    ndata = ndata.pivot_table(index="program", columns="category_information",
                              values="minutes_of_information", aggfunc=sum).reset_index()
    ndata = ndata.fillna(0)
    if "Notizia" in ndata.columns:
        ndata['Notizia'] = ndata['Notizia'].astype('int')
    else:
        ndata['Notizia'] = 0
    if "Parola" in ndata.columns:
        ndata['Parola'] = ndata['Parola'].astype('int')
    else:
        ndata['Parola'] = 0
    ndata.rename(columns={'Notizia': 'news', 'Parola': 'speech'}, inplace=True)
    ndata['total'] = ndata['news'] + ndata['speech']

    programs_data['programs'] = ndata.sort_values(["total", "program"], ascending=[
        False, True]).to_dict('records')

    return {'data': programs_data}


@app.get("/program/{name}")
async def get(name: str = Path(description="name of the italian program"), startday: Union[str, None] = Query(default=from_day, description="start day of the time window", min_length=10, max_length=10, regex=checkitaliandate), endday: Union[str, None] = Query(default=to_day, description="end day of the time window", min_length=10, max_length=10, regex=checkitaliandate), filter: Union[str, None] = Query(default='both', regex=checkcategoryinformation)):
    """
    returns the list of the italian television **programs** available on a given time window<br/>
    The format of the date is DD/MM/YYYY
    """
    ndata = data
    if filter == 'speech':
        ndata = ndata[ndata.category_information == 'Parola']
    if filter == 'news':
        ndata = ndata[ndata.category_information == 'Notizia']
    name = name.title()
    startday, endday, ndata = getdfinterval(
        startday, endday, ndata)
    name = name.upper()
    program_data = {}
    ndata = ndata[ndata['program'].str.upper() == name]
    channel = ndata[ndata.program == name].channel.unique()[0]
    if ndata.shape[0] > 0:
        startday, endday, ndata = getdfinterval(startday, endday, ndata)
        ndata.day = ndata.day.apply(lambda x: x.strftime('%d/%m/%Y'))
        program_data['program'] = name
        program_data['channels'] = channel
        program_data['from'] = startday
        program_data['to'] = endday
        ndata.category_information = ndata.category_information.apply(lambda x: changeParolaNotizia(x))
        raw_data = ndata.to_dict('records')
        program_data['program_history'] = raw_data
    return {"data": program_data}

@app.get("/program/{name}/stats")
async def get(name: str = Path(description="name of the italian program"), startday: Union[str, None] = Query(default=from_day, description="start day of the time window", min_length=10, max_length=10, regex=checkitaliandate), endday: Union[str, None] = Query(default=to_day, description="end day of the time window", min_length=10, max_length=10, regex=checkitaliandate), filter: Union[str, None] = Query(default='both', regex=checkcategoryinformation)):
    name = name.upper()
    program_data = {}
    ndata = data
    if filter == 'speech':
        ndata = ndata[ndata.category_information == 'Parola']
    if filter == 'news':
        ndata = ndata[ndata.category_information == 'Notizia']
    ndata = ndata[ndata['program'].str.upper() == name]
    channel = ndata[ndata.program == name].channel.unique()[0]
    daily_minutes_average = round(ndata.minutes_of_information.sum() / ndata.shape[0], 2)

    if ndata.shape[0] > 0:
        startday, endday, ndata = getdfinterval(startday, endday, ndata)
        ndata.day = ndata.day.apply(lambda x: x.strftime('%d/%m/%Y'))
        program_data['program'] = name
        program_data['channels'] = channel
        program_data['from'] = startday
        program_data['to'] = endday
        daily_minutes_average = round(
            ndata.minutes_of_information.sum() / ndata.shape[0], 2)
        program_data['daily_minutes_average'] = daily_minutes_average
        program_data['total_days'] = len(ndata.day.unique())
        ndata.category_information = ndata.category_information.apply(
            lambda x: changeParolaNotizia(x))
        tmi = ndata.groupby(by="category_information")['minutes_of_information'].sum().to_frame().T
        tmi = checkParolaNotizia(tmi)
        tmi['total'] = tmi['news'] + tmi['speech']
        program_data['category_information'] = tmi.to_dict('records')[0]
        ndata_collective_subjects = ndata[ndata.name == "Soggetto Collettivo"]
        ndata_politicians = ndata[ndata.name != "Soggettivo Collettivo"]
        ndata_politicians = ndata_politicians[ndata_politicians.name !=
                                        "Soggetto Collettivo"]
        ndata_politicians['name_lastname'] = ndata_politicians['name'] + \
            " " + ndata_politicians['lastname']
        program_data['politician_minutes'] = []
        program_data['collective_subjects_minutes'] = []
        if ndata_politicians.shape[0] > 0:
            tmp = ndata_politicians.groupby(by="name_lastname")[
                'minutes_of_information'].sum().to_frame().sort_values(by="minutes_of_information", ascending=False).T
            program_data['politician_minutes'] = tmp.to_dict('records')[0]
        if ndata_collective_subjects.shape[0]:
            tms = ndata_collective_subjects.groupby(by="lastname")[
                'minutes_of_information'].sum().to_frame().sort_values(by="minutes_of_information", ascending=False).T
            program_data['collective_subjects_minutes'] = tms.to_dict('records')[0]
            
    return {"data": program_data}

@app.get("/channels")
async def get(startday: Union[str, None] = Query(default=from_day, description="start day of the time window", min_length=10, max_length=10, regex=checkitaliandate), endday: Union[str, None] = Query(default=to_day, description="end day of the time window", min_length=10, max_length=10, regex=checkitaliandate), filter: Union[str, None] = Query(default='both', regex=checkcategoryinformation)):
    """
    returns the list of the italian television **channels** available on a given time window<br/>
    The format of the date is DD/MM/YYYY
    """
    ndata = data
    if filter == 'speech':
        ndata = ndata[ndata.category_information == 'Parola']
    if filter == 'news':
        ndata = ndata[ndata.category_information == 'Notizia']
    startday, endday, ndata = getdfinterval(startday, endday, ndata)
    senddata_channels = {}
    senddata_channels['from'] = startday
    senddata_channels['to'] = endday
    ndata = ndata.pivot_table(index="channel", columns="category_information",
                              values="minutes_of_information", aggfunc=sum).reset_index()
    ndata = ndata.fillna(0)
    if "Notizia" in ndata.columns:
        ndata['Notizia'] = ndata['Notizia'].astype('int')
    else:
        ndata['Notizia'] = 0
    if "Parola" in ndata.columns:
        ndata['Parola'] = ndata['Parola'].astype('int')
    else:
        ndata['Parola'] = 0
    ndata.rename(columns={'Notizia': 'news', 'Parola': 'speech'}, inplace=True)
    ndata['total'] = ndata['news'] + ndata['speech']

    senddata_channels['channels'] = ndata.sort_values(["total", "channel"], ascending=[
        False, True]).to_dict('records')

    return {'data': senddata_channels}

@app.get("/channel/{name}")
async def get(name: str = Path(description="name of the italian channel"), startday: Union[str, None] = Query(default=from_day, description="start day of the time window", min_length=10, max_length=10, regex=checkitaliandate), endday: Union[str, None] = Query(default=to_day, description="end day of the time window", min_length=10, max_length=10, regex=checkitaliandate), filter: Union[str, None] = Query(default='both', regex=checkcategoryinformation)):
    """
    returns all the data of a single italian tv **channel** and relative **programs** in a given time window<br/>
    The time unit is the day (format DD/MM/YYYY)  
    """
    ndata = data
    if filter == 'speech':
        ndata = ndata[ndata.category_information == 'Parola']
    if filter == 'news':
        ndata = ndata[ndata.category_information == 'Notizia']
    name = name.title()
    channel_data = {}
    ndata = ndata[ndata['channel'].str.title() == name]
    programs = list(ndata.program.unique())
    if ndata.shape[0] > 0:
        startday, endday, ndata = getdfinterval(startday, endday, ndata)
        ndata.day = ndata.day.apply(lambda x: x.strftime('%d/%m/%Y'))
        channel_data['channel'] = name
        channel_data['programs'] = programs
        channel_data['from'] = startday
        channel_data['to'] = endday
        ndata.category_information = ndata.category_information.apply(
            lambda x: changeParolaNotizia(x))
        raw_data = ndata.to_dict('records')
        channel_data['channel_history'] = raw_data
    return {"data": channel_data}

@app.get("/channel/{name}/stats")
async def get(name: str = Path(description="name of the italian channel"), startday: Union[str, None] = Query(default=from_day, description="start day of the time window", min_length=10, max_length=10, regex=checkitaliandate), endday: Union[str, None] = Query(default=to_day, description="end day of the time window", min_length=10, max_length=10, regex=checkitaliandate), filter: Union[str, None] = Query(default='both', regex=checkcategoryinformation)):
    name = name.title()
    channel_data = {}
    ndata = data
    if filter == 'speech':
        ndata = ndata[ndata.category_information == 'Parola']
    if filter == 'news':
        ndata = ndata[ndata.category_information == 'Notizia']
    ndata = ndata[ndata['channel'].str.title() == name]
    daily_minutes_average = round(
        ndata.minutes_of_information.sum() / ndata.shape[0], 2)

    if ndata.shape[0] > 0:
        startday, endday, ndata = getdfinterval(startday, endday, ndata)
        ndata.day = ndata.day.apply(lambda x: x.strftime('%d/%m/%Y'))
        programs = list(ndata.program.unique())
        channel_data['channel'] = name
        channel_data['programs'] = programs
        channel_data['from'] = startday
        channel_data['to'] = endday
        daily_minutes_average = round(
            ndata.minutes_of_information.sum() / ndata.shape[0], 2)
        channel_data['daily_minutes_average'] = daily_minutes_average
        channel_data['total_days'] = len(ndata.day.unique())
        ndata.category_information = ndata.category_information.apply(
            lambda x: changeParolaNotizia(x))
        tmi = ndata.groupby(by="category_information")[
            'minutes_of_information'].sum().to_frame().T
        tmi = checkParolaNotizia(tmi)
        tmi['total'] = tmi['news'] + tmi['speech']
        channel_data['category_information'] = tmi.to_dict('records')[0]
        ndata_collective_subjects = ndata[ndata.name == "Soggetto Collettivo"]
        ndata_politicians = ndata[ndata.name != "Soggettivo Collettivo"]
        ndata_politicians = ndata_politicians[ndata_politicians.name !=
                                              "Soggetto Collettivo"]
        ndata_politicians['name_lastname'] = ndata_politicians['name'] + \
            " " + ndata_politicians['lastname']
        channel_data['politician_minutes'] = []
        channel_data['collective_subjects_minutes'] = []
        if ndata_politicians.shape[0] > 0:
            tmp = ndata_politicians.groupby(by="name_lastname")[
                'minutes_of_information'].sum().to_frame().sort_values(by="minutes_of_information", ascending=False).T
            channel_data['politician_minutes'] = tmp.to_dict('records')[0]
        if ndata_collective_subjects.shape[0]:
            tms = ndata_collective_subjects.groupby(by="lastname")[
                'minutes_of_information'].sum().to_frame().sort_values(by="minutes_of_information", ascending=False).T
            channel_data['collective_subjects_minutes'] = tms.to_dict('records')[
                0]

    return {"data": channel_data}