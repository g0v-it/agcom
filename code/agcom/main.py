from fastapi import FastAPI
import pandas as pd
#import os
from datetime import datetime
pd.options.mode.chained_assignment = None  # default='warn'

data = pd.read_parquet(
    "https://github.com/g0v-it/agcom/raw/main/data/dati_presenze_politici.parquet")
from_day = data.DATA.min().strftime('%d/%m/%Y')
to_day = data.DATA.max().strftime('%d/%m/%Y')

data.rename(columns={'CANALE': 'channel', 'PROGRAMMA': 'program', 'DATA':'day', 
                     'COGNOME':'lastname','NOME':'name',
                     'MICRO_CATEGORIA':'affiliation',
                     'ARGOMENTO': 'topic', 'DURATA': 'minutes_of_intervention',
                     'TIPO_TEMPO':'category_intervention'}, inplace=True)

description = """
## AGCOM - elementary data of the italian television monitoring

This API provides the possibility to query the elementary televised monitoring data provided by [AGCOM](https://www.agcom.it/) - Italian authority for guarantees in communications - of political interventions (data as news or as word)

The data can be found in XML format at [https://www.agcom.it/dati-elementari-di-monitoraggio-televisivo](https://www.agcom.it/dati-elementari-di-monitoraggio-televisivo)

Period:<br/>
from **%s** to **%s**


The license under which the data is released by AGCOM is CC-BY-SA-NC

![](https://www.agcom.it/documents/10179/4502194/Logo+Creative+common/2e1fe5a2-4324-4965-b8af-76403bb42b15?t=1618583317352)

""" % (from_day, to_day)

app = FastAPI(
    docs_url=None, redoc_url="/",
    title="AGCOM - dati elementari di monitoraggio televisivo",
    description=description,
    version="0.0.1",
    contact={
        "name": "napo",
        "url": "https://twitter.com/napo"
    }
)

tags_metadata = [
    {
        "name": "period",
        "description": "returns the historical period that can be queried on the data",
    },
    {
        "name": "presencecategories",
        "description": "the interventions are collected in different categories.<br/>Eg. 'Parola' => speeches<Br/>'Notizia' = > when the person or collective subject made news"
    },
    {
        "name": "channels",
        "description": "returns the list of the italian television channels that are availables"
    }
]

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


def dfpivottable(df, indexvalue, columnsvalue, aggvalues="minutes_of_intervention"):
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


@app.get("/period") #, tags=["period"])
async def read_period():
    period = {}
    period['from'] = from_day
    period['to'] = to_day
    return {"period": period}

@app.get("/presencecategories") #, tags=["presencecategories"])
async def read_presencecategories(startday: str = from_day, endday: str = to_day):
    startday, endday, ndata = getdfinterval(startday, endday, data)
    presencecategories = list(ndata.category_intervention.unique())
    return {'presencecategories': presencecategories}

@app.get("/channels") #,tags=["channels"])
async def read_channels(startday: str = from_day, endday: str = to_day):
    startday, endday, ndata = getdfinterval(startday, endday, data)
    senddata_channels = {}
    senddata_channels['from'] = startday
    senddata_channels['to'] = endday
    ndata = ndata.pivot_table(index="channel", columns="category_intervention",
                              values="minutes_of_intervention", aggfunc=sum).reset_index()
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

@app.get("/programs")
async def read_programs(startday: str = from_day, endday: str = to_day):
    programs_data = {}
    #programs = list(ndata.program.unique())
    startday, endday, ndata = getdfinterval(startday, endday, data)
    programs_data['from'] = startday
    programs_data['to'] = endday
    ndata = ndata.pivot_table(index="program", columns="category_intervention",
                              values="minutes_of_intervention", aggfunc=sum).reset_index()
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
    #programs_data["from"] = startday
    #programs_data['to'] = endday
    #programs_data['programs'] = programs
    return {'data': programs_data}

@app.get("/collectivesubjects")
async def read_collectivesubjects(startday: str = from_day, endday: str = to_day):
    startday, endday, ndata = getdfinterval(
        startday, endday, data_collective_subjects)
    senddata_collective_subjects = {}
    senddata_collective_subjects['from'] = startday
    senddata_collective_subjects['to'] = endday
    ndata = ndata.pivot_table(index="lastname", columns="category_intervention",
                              values="minutes_of_intervention", aggfunc=sum).reset_index()
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

@app.get("/topics")
async def read_topics(startday: str = from_day, endday: str = to_day):
    startday, endday, ndata = getdfinterval(
        startday, endday, data)
    list_topics = list(ndata.topic.unique())
    return {'topics': list_topics}

@app.get("/politicians")
async def read_politicians(startday: str = from_day, endday: str = to_day):
    startday, endday, ndata = getdfinterval(
        startday, endday, data_politicians)
    senddata_politicians = {}
    senddata_politicians['from'] = startday
    senddata_politicians['to'] = endday
    
    ndata = ndata.pivot_table(index="name_lastname", columns="category_intervention",
                      values="minutes_of_intervention", aggfunc=sum).reset_index()
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

@app.get("/affiliations")
async def read_affiliations(startday: str = from_day, endday: str = to_day):
    startday, endday, ndata = getdfinterval(
        startday, endday, data)
    affiliations = list(ndata.affiliation.unique())
    return {'affiliations': affiliations}


@app.get("/collectivesubject/{name}")
async def read_collectivesubject(name: str, startday: str = from_day, endday: str = to_day):
    name = name.title()
    collectivesubject_data = {}
    collectivesubject = data_collective_subjects[data_collective_subjects['lastname'] == name]
    if collectivesubject.shape[0] > 0:
        startday, endday, collectivesubject = getdfinterval(
            startday, endday, collectivesubject)
        collectivesubject.day = collectivesubject.day.apply(
            lambda x: x.strftime('%d/%m/%Y'))
        collectivesubject_data['collectivesubject'] = name
        collectivesubject_data['from'] = startday
        collectivesubject_data['to'] = endday
        raw_data = collectivesubject[selected_politicians_columns].to_dict('records')
        collectivesubject_data['television_presence'] = raw_data
    return {"data": collectivesubject_data}

@app.get("/politician/{name_lastname}")
async def read_politician(name_lastname: str, startday: str = from_day, endday: str = to_day):
    name_lastname = name_lastname.title()
    politician_data = {}
    affiliations = "not present"
    politician = data_politicians[data_politicians['name_lastname'] == name_lastname]
    print(politician.head(3))
    if politician.shape[0] > 0:
        startday, endday, politician = getdfinterval(startday, endday, politician)
        affiliations = list(politician.affiliation.unique())
        politician.day = politician.day.apply(lambda x: x.strftime('%d/%m/%Y'))
        politician_data['politician'] = name_lastname
        politician_data['affiliations'] = affiliations
        politician_data['from'] = startday
        politician_data['to'] = endday
        raw_data = politician[selected_politicians_columns].to_dict('records')
        politician_data['television_presence'] = raw_data
    return {"data": politician_data}


@app.get("/collectivesubject/{name}/stats")
async def read_collectivesubject_stats(name: str, startday: str = from_day, endday: str = to_day):
    name = name.title()
    presence = ""
    time_topics = ""
    time_channels = ""
    time_topics = ""
    time_programs = ""
    collectivesubject = data_collective_subjects[data_collective_subjects['lastname'] == name]

    if collectivesubject.shape[0] > 0:
        startday, endday, collectivesubject = getdfinterval(
            startday, endday, collectivesubject)
        presence = int(collectivesubject.minutes_of_intervention.sum())
        time_topics = collectivesubject.groupby('topic').aggregate('sum')
        time_topics.rename(
            columns={"minutes_of_intervention": "time_topics"}, inplace=True)
        time_topics = time_topics.to_dict()['time_topics']
        time_channels = collectivesubject.groupby('channel').aggregate('sum')
        time_channels.rename(
            columns={"minutes_of_intervention": "time_channel"}, inplace=True)
        time_channels = time_channels.sort_values(by=["time_channel", "channel"], ascending=[
                                                  False, False]).to_dict()['time_channel']
        time_programs = collectivesubject.groupby('program').aggregate('sum')
        time_programs.rename(
            columns={"minutes_of_intervention": "time_programs"}, inplace=True)
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

@app.get("/politician/{name_lastname}/stats")
async def read_politician_stats(name_lastname: str, startday: str = from_day, endday: str = to_day):
    name_lastname = name_lastname.title()
    affiliations = "not present"
    presence = ""
    time_topics = ""
    time_channels = ""
    time_topics = ""
    time_programs = ""
    politician = data_politicians[data_politicians['name_lastname']
                                  == name_lastname]
    
    if politician.shape[0] > 0:
        startday, endday, politician = getdfinterval(
            startday, endday, politician)
        affiliations = list(politician.affiliation.unique())
        presencedata = dfpivottable(politician, 
                                    indexvalue="name_lastname", 
                                    columnsvalue="category_intervention")
        del presencedata['name_lastname']
        presence = presencedata.to_dict('records')[0]
        time_topics = politician.groupby('topic').aggregate('sum')
        time_topics.rename(columns={"minutes_of_intervention": "time_topics"}, inplace=True)
        time_topics = time_topics.to_dict()['time_topics']
        #time_topics = timetopicsdata.to_dict('records')
        time_channels = politician.groupby('channel').aggregate('sum')
        time_channels.rename(
            columns={"minutes_of_intervention": "time_channel"}, inplace=True)
        time_channels = time_channels.sort_values(by=["time_channel", "channel"], ascending=[
                                                  False, False]).to_dict()['time_channel']
        time_programs = politician.groupby('program').aggregate('sum')
        time_programs.rename(
            columns={"minutes_of_intervention": "time_programs"}, inplace=True)
        time_programs = time_programs.sort_values(by=["time_programs", "program"], ascending=[False, False]).to_dict()['time_programs']
        #time_programs = time_programs.to_dict()['time_programs']

    stats = {}
    stats['politician'] = name_lastname
    stats['affiliations'] = affiliations
    stats['from'] = startday
    stats['to'] = endday
    stats['presence_minutes'] = presence
    stats['time_topics'] = time_topics
    stats['time_channels'] = time_channels
    stats['time_programs'] = time_programs
    return {"data":stats}