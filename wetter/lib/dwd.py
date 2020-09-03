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
import datetime
import shutil
import tempfile

import urllib.request
from geopy.distance import geodesic
import numpy as np
import pandas as pd




class DWD():
    """Prepare a list of weather stations and calculate the distance to the place of interest."""
    def __init__(self):
        """Create instance variables.
        
        stations -- list of all weather stations -> list
        module_dir -- current directory within the Django framework.
        """
        self.stations = []
        self.module_dir = os.path.dirname(__file__)  
       
    def get_stations(self) -> None:
        "Open the file which contains the weather station meta data."
        f = open(os.path.join(self.module_dir, "../data/stations.json"), "r")
        list_ = json.load(f)
        f.close()
        for e in list_:
            self.stations.append(DwdStation(e))

    def get_distance(self, start_point: tuple, end_point: tuple) -> float:
        """Calculate the distance between point (lat,lon) in kilometers."""
        return round(geodesic(start_point, end_point).km, 1)


class DwdStation():
    """Manage data and meta data of one weather station."""
    
    def __init__(self, dict_: dict):
        self.stations_id = dict_["Stations_id"]  
        self.von_datum = dict_["von_datum"]
        self.bis_datum = dict_["bis_datum"]
        self.stationshoehe = dict_["Stationshoehe"]
        self.geo_breite = dict_["geoBreite"]
        self.geo_laenge = dict_["geoLaenge"]
        self.stationsname = dict_['Stationsname']
        self.bundesland = dict_["Bundesland"]
    

    def set_data(self, df: pd.DataFrame) -> None:
        """Add the data record to the station"""
        self.data = df
    
    def set_distance(self, distance: float) -> None:
        """Add the distance between the station and a place"""
        self.distance = distance


class DwdFile():
    """Fetch and clean the historic weather data from the DWD open data server."""
    
    module_dir = os.path.dirname(__file__)  # get current directory
    base_path = "https://opendata.dwd.de/climate_environment/CDC/observations_germany/climate/daily/kl/historical/"

    def __init__(self):
        self.module_dir = self.module_dir[:-3] + "data"
        
    def get_data(self, stations_id: int) -> pd.DataFrame: 
        """Read the raw data from a local file or fetch them from the DWD open data server."""
        shortname = str(stations_id).zfill(5)
        dffilename = os.path.join(self.module_dir,"station_data", shortname + ".csv.gz")
        if os.path.isfile(dffilename):
            return self.clean_data(pd.read_csv(dffilename))
        else:
            df = self.get_station_file(stations_id)
            df = self.clean_data(df)
            df.to_csv(dffilename, index=False, compression="gzip")
            return df

    def clean_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Clean the raw weather data."""
        if not df.empty:
            df.columns = df.columns.str.replace(" ", "")
            df = df.convert_dtypes()
            df = df.replace(-999, np.NaN)
            df = df.replace(pd.NA, np.NaN)
            df.MESS_DATUM = df.MESS_DATUM.apply(str)
        return df



    def get_station_file(self, stations_id: int) -> pd.DataFrame:
        """Extract the raw data from the station's remote zipped data file. 
        
        Take the name of the zip file from localy stored an index file. 
        """

        file_list = [
            x for x in open(
                os.path.join(self.module_dir, "filelist.txt"), "r").
            read().split("\n")
        ]
        filename = next(
            (x for x in file_list if x[14:19] == str(stations_id).zfill(5)), "")
        if filename == "":
            return pd.DataFrame()

        with urllib.request.urlopen(self.base_path + filename) as response:
            with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
                shutil.copyfileobj(response, tmp_file)

        archive = zipfile.ZipFile(tmp_file.name, 'r')
        archive_files = zipfile.ZipFile.namelist(archive)
        filename = next((x for x in archive_files if x.startswith("pro")), "")
        if filename == "":
            return pd.DataFrame()
        data = archive.read(filename)
        with tempfile.TemporaryFile() as fp:
            fp.write(data)
            fp.seek(0)
            df = pd.read_csv(fp, sep=";")
        return df


class Forecast():
    """Aggregate the weater data for specific place and day"""

    def __init__(self, geo_breite: float, geo_laenge: float, max_distance: float, monattag: str, max_stations: int):
        """
        geo_breite: geographical latitude of the forecast location (dec)
        geo_laenge: geographical longitude of the forecast location (dec)
        max_distance: Maximum distance of the surveyed measuring stations from the forecast location (in km) 
        monattag: Day of the year for which the weather should be predicted as str "MMTT"
        max_stations: Maximum number of stations in the vicinity to be included in the forecast (currently =3)
        """
        self.ort = ""
        self.tag = None
        self.monat = None
        self.datum = None
        self.tagreihe = []
        self.stationen = []
        self.series = {}
        self.aggregate = {}
        self.geo = [geo_breite, geo_laenge]
        dwd = DWD()
        dwd.get_stations()
        self.stations = []
        for e in dwd.stations:
            distance = dwd.get_distance(self.geo,(e.geo_breite, e.geo_laenge))
            if distance <= max_distance:
                station = e
                station.set_distance(distance)
                self.stations.append(station)
        self.stations = sorted(self.stations, key=lambda station: station.distance)
        if len(self.stations) < max_stations:
            max_stations = len(self.stations)
        self.stations = self.stations[0:max_stations]
        for i in range(0, max_stations):
            dwdfile = DwdFile()
            data = dwdfile.get_data(self.stations[i].stations_id)
            self.stations[i].set_data(data)
        self.set_date(monattag)

    def set_date(self, monattag: str) -> None:
        """Set the day of the year and calculate neighboring days."""
        self.tag = int(monattag[2:4])
        self.monat = int(monattag[0:2])
        self.datum = monattag
        today = datetime.date.today()
        date_ = datetime.date(today.year, self.monat, self.tag)
        yesterday = date_ + datetime.timedelta(days=-1)
        for i in range(0, 3):
            d = yesterday + datetime.timedelta(days=i)
            self.tagreihe.append(str(d.month).zfill(2) + str(d.day).zfill(2))

    def filter(self, df: pd.DataFrame, col: str, monattag: str) -> pd.Series:
        """Filter a named column from a stations data.
        
        Return only values from different years, which were registred for the same day and month. 
        """
        if not df.empty:
            newdf = df[df["MESS_DATUM"].str.contains(
                "\d\d\d\d" + monattag, regex = True)]
            return pd.Series(newdf[col].values, index = newdf["MESS_DATUM"])
        else:
            return pd.Series([np.NaN], index=["2020"+monattag])

    def make_history(self):
        """Create a data object ready for delivery"""
        list_ = []
        for e in self.stations:
            d = {}
            d = {
                "stationsname":e.stationsname,
                "stationshoehe":e.stationshoehe,
                "bundesland":e.bundesland,
                "distance":e.distance,
                "von_datum":e.von_datum,
                "bis_datum":e.bis_datum
                }
            d["TXK"] = json.loads(
                self.filter(e.data, "TXK", self.datum).to_json(orient="split"))
            d["TNK"] = json.loads(
                self.filter(e.data, "TNK", self.datum).to_json(orient="split"))
            d["RSK"] = json.loads(
                self.filter(e.data, "RSK", self.datum).to_json(orient="split"))
            d["SDK"] = json.loads(
                self.filter(e.data, "SDK", self.datum).to_json(orient="split"))
            d["PM"] = json.loads(
                self.filter(e.data, "PM", self.datum).to_json(orient="split"))
            d["UPM"] = json.loads(
                self.filter(e.data, "UPM", self.datum).to_json(orient="split"))
            list_.append(d.copy())
        return list_.copy()

    def get_month(self, monat: int) -> str:
        """Return the name of a month."""
        return [
            "Januar", "Februar", "März", "April", "Mai", "Juni", "Juli",
            "August", "September", "Oktober", "November", "Dezember"
        ][int(monat) - 1]

    def get_aggregates(self, monattag: str = "") -> dict:
        """Calculate aggregates from data"""
        aggregates = {}
        for e in ["TXK", "TNK", "RSK", "SDK", "PM", "UPM"]:
            d = {}
            if monattag == "":
                list_ = [self.create_timeline(e, t) for t in self.tagreihe]
                s = sum(list_) / len(list_)
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
                if "2010" in s.index:
                    index_2010 = s.index.to_list().index("2010")
                    d["mean2010"] = round(s[index_2010:][~s.isnull()].mean(), 0)
                else:
                    d["mean2010"]=""
                d["first_year"] = s[~s.isnull()].index[0]
                d["last_year"] = s[~s.isnull()].index[-1]
                d["mean"] = round(s[~s.isnull()].mean(), 0)
                
                d["count"] = s[~s.isnull()].count()
                d["std"] = round(s[~s.isnull()].std(), 0)
                d["median"] = s[~s.isnull()].median()
                d["max"] = round(s.max(), 1)
                d["max_year"] = s.index[np.where(s == np.max(s))[0][0]]
                d["min_year"] = s.index[np.where(s == np.min(s))[0][0]]
                d["min"] = round(s.min(), 1)
                if e == "RSK":
                    d["zerorain"] = s[s == 0.0].count()
                if e == "SDK":
                    d["zerosun"] = s[s == 0.0].count()
                if e == "PM":
                    mittelhoehe = sum([x.stationshoehe for x in self.stations]) / len(self.stations)
                    d["mean_pressure"] = round(1013.25 * (1 - (0.0065 * mittelhoehe) / 288.15)**5.255,0)   #Barometric formula
                    d["depression_days"] = s[s < d["mean_pressure"]].count()
            aggregates[e] = d.copy()
            self.aggregates = aggregates.copy()
        return aggregates

    def aggregate_over_year(self) -> dict:
        """Aggregate the date for one place for all days of the year"""
        oy = {
            "monattag": [],
            "TXK": {
                "mean": [],
                "std": []
            },
            "TNK": {
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
            aggregates = {}
            aggregates = self.get_aggregates(mt)
            for e in ["TXK", "TNK", "RSK", "SDK", "PM", "UPM"]:
                oy[e]["mean"].append(aggregates[e]["mean"])
                oy[e]["std"].append(aggregates[e]["std"])
        return oy

    def monattag_generator(self) -> str:
        """Generate all days of a year."""
        for m in range(1, 13):
            for t in range(1, 32):
                if t > 29 and m == 2:
                    continue
                if t > 30 and m in [2, 4, 6, 9, 11]:
                    continue
                yield str(m).zfill(2) + str(t).zfill(2)

    def create_timeline(self, column: str, monattag: str) -> pd.Series:
        """Merge the data from multiple stations into one series.
        
        Create average values in case of overlaping data.
        """
        d = {}
        max = 0
        min = 30000000
        for e in self.stations:
            s = self.filter(e.data, column, monattag)
            for index, value in s.items():
                if index[4:8] != monattag:
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
        list_ = s.index.tolist()
        list_ = [x[0:4] for x in list_]
        s.index = list_
        return s


class Plz():
    """Handle ajax queries concerning postal codes 
    
    Prepare the return value for the jquery.autocomplete element.
    """
    module_dir = os.path.dirname(__file__)  # get current directory
    
    def __init__(self):
        f = open(os.path.join(self.module_dir, "../data/plz.json"), "r")
        self.json = json.load(f)

    def query(self, query: str) -> dict:
        return {
            "query":
            "Unit",
            "suggestions": [
                x for x in self.json
                if x['value'].lower().find(query.lower()) > -1
            ]
        }



class Monattage():
    """Handle ajax queries concerning date selection.
    
    Prepare the return value for the jquery.autocomplete element.
    """
    module_dir = os.path.dirname(__file__)  # get current directory

    def __init__(self):
        f = open(os.path.join(self.module_dir, "../data/monattage.json"), "r")
        self.json = json.load(f)

    def query(self, query: str) -> dict:
        return {
            "query":
            "Unit",
            "suggestions": [
                x for x in self.json
                if x["value"].lower().find(query.lower()) > -1
            ]
        }

