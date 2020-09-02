""" Module Dwd

Read and aggregate historic weather data for Germany.
Use open data from the public German Weather Sevice (DWD)
"""

__all__ = []
__version__ = "0.1"
__author__ = "U. Jung"

import json
import os
import zipfile
import re
import datetime
import shutil
import tempfile

import urllib.request
from geopy.distance import geodesic
import numpy as np
import pandas as pd




class Dwd():
    """Prepare a list of weather stations and calculate the distance to the place of interest."""
    def __init__(self):
        """Create instance variables.
        
        stations -- list of all weather stations -> list
        module_dir -- current directory within the Django framework.
        """
        self.stations = []
        self.module_dir = os.path.dirname(__file__)  
       
    def get_stations(self) -> None:
        "Open the file which contains the station meta data."
        f = open(os.path.join(self.module_dir, "../data/stations.json"), "r")
        list_ = json.load(f)
        self.stations = list_

    def get_distance(self, start_point: tuple, end_point: tuple) -> float:
        """Calculate the distance between point (lat,lon) in kilometers."""
        return round(geodesic(start_point, end_point).km, 1)


class Dwdfile():
    """Fetch and clean the historic weather data from the open data server of DVD."""
    
    module_dir = os.path.dirname(__file__)  # get current directory
    base_path = "https://opendata.dwd.de/climate_environment/CDC/observations_germany/climate/daily/kl/historical/"

    def __init__(self):
        """Initialize the local data directory path"""
        self.module_dir = self.module_dir[:-3] + "data"
        

    def get_data(self, station, von, bis):
        shortname = str(station).zfill(5)
        dffilename = os.path.join(self.module_dir, shortname + ".csv.gz")
        if os.path.isfile(dffilename):
            return self.clean_data(pd.read_csv(dffilename))
        else:
            df = self.get_station_file(station)
            df = self.clean_data(df)
            df.to_csv(dffilename, index=False, compression="gzip")
            return df

    def clean_data(self, df):
        df.columns = df.columns.str.replace(" ", "")
        df = df.convert_dtypes()
        df = df.replace(-999, np.NaN)
        df = df.replace(pd.NA, np.NaN)
        df.MESS_DATUM = df.MESS_DATUM.apply(str)
        return df

    def get_data_from_sobject(self, statobj):
        return self.get_data(statobj["Stations_id"], statobj["von_datum"],
                             statobj["bis_datum"])

    def get_station_file(self, station):

        file_list = [
            x for x in open(
                os.path.join(self.module_dir, "../data/filelist.txt"), "r").
            read().split("\n")
        ]
        filename = next(
            (x for x in file_list if x[14:19] == str(station).zfill(5)), "")
        if filename == "":
            return pd.DataFrame()

        with urllib.request.urlopen(self.base_path + filename) as response:
            with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
                shutil.copyfileobj(response, tmp_file)

        archive = zipfile.ZipFile(tmp_file.name, 'r')
        archive_files = zipfile.ZipFile.namelist(archive)
        filename = next((x for x in archive_files if x[0:3] == "pro"), "")
        if filename == "":
            return pd.DataFrame()
        data = archive.read(filename)
        with tempfile.TemporaryFile() as fp:
            fp.write(data)
            fp.seek(0)
            df = pd.read_csv(fp, sep=";")
        return df


class Forecast():
    """erstellt Vorhersagen"""

    geo = []
    ort = ""
    tag = None
    monat = None
    datum = None
    tagreihe = []
    stationen = []
    series = {}
    aggr = {}

    def __init__(self, geoBreite, geoLaenge, distance, monattag, maxstationen):
        """
        geoBreite: geografische Breite des Vorhersageortes (dec)
        geoLaenge: geografische Länge des Vorhersageortes (dec)
        distance: Maximaler Abstand der befragten Messtationen vom Vorhersageort (in km) 
        monattag: Tag im Jahr, für den das Wetter vorhergesagt werden soll als str "MMTT"
        maxstationen:Maximale Anzahl der Stationen im Umkreis, die für die Vorhersage mit einbezogen werden sollen (default=3)
        """
        self.geo = [geoBreite, geoLaenge]
        dwd = Dwd()
        dwd.get_stations()
        self.stationen = []
        for e in dwd.stations:
            entfernung = dwd.get_distance(self.geo,(e["geoBreite"], e["geoLaenge"]))
            if entfernung <= distance:
                self.stationen.append([e.copy(), entfernung])
        self.stationen = sorted(self.stationen, key=lambda tup: tup[1])
        if len(self.stationen) < maxstationen:
            maxstationen = len(self.stationen)
        self.stationen = self.stationen[0:maxstationen]
        for i in range(0, maxstationen):
            dwdfile = Dwdfile()
            data = dwdfile.get_data_from_sobject(self.stationen[i][0])
            self.stationen[i].append(data.copy())
        self.set_date(monattag)

    def get_nth_station(self, n=0):
        return sorted(self.stationen, key=lambda tup: tup[1])[n]

    def set_date(self, monattag):
        self.tag = int(monattag[2:4])
        self.monat = int(monattag[0:2])
        self.datum = monattag
        heute = datetime.date.today()
        datum = datetime.date(heute.year, self.monat, self.tag)
        gestern = datum + datetime.timedelta(days=-1)
        for i in range(0, 3):
            d = gestern + datetime.timedelta(days=i)
            self.tagreihe.append(str(d.month).zfill(2) + str(d.day).zfill(2))

    def filter(self, df, col, monattag):
        newdf = df[df["MESS_DATUM"].str.contains(
            "\d\d\d\d" + monattag, regex = True)]
        return pd.Series(newdf[col].values, index = newdf["MESS_DATUM"])

    def make_history(self):
        l = []
        for e in self.stationen:
            d = {}
            if len(e) < 3:
                continue
            d = e[0].copy()
            d["entfernung"] = e[1]
            d["TXK"] = json.loads(
                self.filter(e[2], "TXK", self.datum).to_json(orient="split"))
            d["RSK"] = json.loads(
                self.filter(e[2], "RSK", self.datum).to_json(orient="split"))
            d["SDK"] = json.loads(
                self.filter(e[2], "SDK", self.datum).to_json(orient="split"))
            d["PM"] = json.loads(
                self.filter(e[2], "PM", self.datum).to_json(orient="split"))
            d["UPM"] = json.loads(
                self.filter(e[2], "UPM", self.datum).to_json(orient="split"))
            l.append(d.copy())
        return l.copy()

    def get_month(self, monat):
        return [
            "Januar", "Februar", "März", "April", "Mai", "Juni", "Juli",
            "August", "September", "Oktober", "November", "Dezember"
        ][int(monat) - 1]

    def get_aggregates(self, monattag=""):
        aggr = {}
        for e in ["TXK", "RSK", "SDK", "PM", "UPM"]:
            d = {}
            if monattag == "":
                l = [self.create_timeline(e, t) for t in self.tagreihe]
                s = sum(l) / len(l)
            else:
                s = self.create_timeline(e, monattag)
            if s.count() == 0:
                d = {
                    "first_year": "",
                    "last_year": "",
                    "mean": "",
                    "mean2010": "",
                    "count": 0,
                    "std": "",
                    "median": "",
                    "max": "",
                    "max_year": "",
                    "min_year": "",
                    "min": "",
                    "zerorain": "",
                    "zerosun": "",
                    "mitteldruck": "",
                    "depressiondays": ""
                }
            else:
                index_2010 = s.index.to_list().index("2010")

                d["first_year"] = s[~s.isnull()].index[0]
                d["last_year"] = s[~s.isnull()].index[-1]
                d["mean"] = round(s[~s.isnull()].mean(), 0)
                d["mean2010"] = round(s[index_2010:][~s.isnull()].mean(), 0)
                d["count"] = s[~s.isnull()].count()
                d["std"] = round(s[~s.isnull()].std(), 0)
                d["median"] = s[~s.isnull()].median()
                d["max"] = round(s.max(), 1)
                d["max_year"] = s.index[np.where(s == np.max(s))[0][0]]
                d["min_year"] = s.index[np.where(s == np.min(s))[0][0]]
                d["min"] = round(s.min(), 1)
                #d["percentile25"]=np.nanpercentile(s,25)
                #d["percentile75"]=np.nanpercentile(s,75)
                if e == "RSK":
                    d["zerorain"] = s[s == 0.0].count()
                if e == "SDK":
                    d["zerosun"] = s[s == 0.0].count()
                if e == "PM":
                    mittelhoehe = sum(
                        [x[0]["Stationshoehe"]
                         for x in self.stationen]) / len(self.stationen)
                    d["mitteldruck"] = round(
                        1013.25 * (1 - (0.0065 * mittelhoehe) / 288.15)**5.255,
                        0)
                    d["depressiondays"] = s[s < d["mitteldruck"]].count()
            aggr[e] = d.copy()
            self.aggr = aggr.copy()
        return aggr

    def aggregate_over_year(self):
        oy = {
            "monattag": [],
            "TXK": {
                "mean": [],
                "std": []
            },
            "RSK": {
                "mean": [],
                "std": []
            },
            "SDK": {
                "mean": [],
                "std": []
            },
            "PM": {
                "mean": [],
                "std": []
            },
            "UPM": {
                "mean": [],
                "std": []
            }
        }
        for mt in self.monattag_generator():
            oy["monattag"].append(mt)
            aggr = {}
            aggr = self.get_aggregates(mt)
            for e in ["TXK", "RSK", "SDK", "PM", "UPM"]:
                oy[e]["mean"].append(aggr[e]["mean"])
                oy[e]["std"].append(aggr[e]["std"])
        return oy

    def monattag_generator(self):
        for m in range(1, 13):
            for t in range(1, 32):
                if t > 29 and m == 2:
                    continue
                if t > 30 and m in [2, 4, 6, 9, 11]:
                    continue
                yield str(m).zfill(2) + str(t).zfill(2)

    def create_timeline(self, column: str, monthday: str):
        """fasst die Daten mehrerer Stationen zu einer Zeitreihe zusammen. Bei Überlappungen wird der Mittelwert gebildet."""
        d = {}
        max = 0
        min = 30000000
        for e in self.stationen:
            s = self.filter(e[2], column, monthday)
            for index, value in s.items():
                if index[4:8] != monthday:
                    continue
                if int(index) > max:
                    max = int(index)
                if int(index) < min:
                    min = int(index)
                if index in d:
                    d[index].append(value)
                else:
                    d[index] = [value]
        for k, v in d.items():
            d[k] = sum(v) / len(v)
        s = pd.Series(
            d, index=[str(x) for x in range(min, max + 10000, 10000)])
        l = s.index.tolist()
        l = [x[0:4] for x in l]
        s.index = l
        return s


class Plz():
    module_dir = os.path.dirname(__file__)  # get current directory
    json = []

    def __init__(self):
        f = open(os.path.join(self.module_dir, "../data/plz.json"), "r")
        self.json = json.load(f)

    def query(self, query):
        return {
            "query":
            "Unit",
            "suggestions": [
                x for x in self.json
                if x['value'].lower().find(query.lower()) > -1
            ]
        }



class Monattage():
    module_dir = os.path.dirname(__file__)  # get current directory
    json = []

    def __init__(self):
        f = open(os.path.join(self.module_dir, "../data/monattage.json"), "r")
        self.json = json.load(f)

    def query(self, query):
        return {
            "query":
            "Unit",
            "suggestions": [
                x for x in self.json
                if x["value"].lower().find(query.lower()) > -1
            ]
        }

