from datetime import date
import re
import sys

from django.shortcuts import render
from django.http import JsonResponse
from django.utils.safestring import SafeString
from .lib.dwd import  Forecast, Plz, Monattage

# Create your view
def index(request):
    return render(request, 'wetter/index.html')


def daten(request, geo, monattag):
    if "ort" in request.GET:
        ort = re.split("\ \d", request.GET['ort'])[0]
    else:
        ort = ""

    p1 = geo.split(",")
    try:
        fc = Forecast(p1[0], p1[1], 100, monattag, 3)
        fc.get_aggregates()
        jstr = SafeString(fc.make_history())
        jstr = jstr.replace("None", "null")
        jstr = jstr.replace("'", '"')
        heute = date.today()
        stations = [(x.stationsname, x.bundesland, x.stationshoehe, x.distance)
                    for x in fc.stations]
        if len(set([x[1] for x in stations])) == 1:
            bundesland = "/" + stations[0][1]
        else:
            bundesland = ""

        return render(
            request, 'wetter/daten.html', {
                "aggr": fc.aggregates,
                "geoBreite": p1[0],
                "geoLaenge": p1[1],
                "monattag": str(fc.tag) + ". " + fc.get_month(fc.monat) + "",
                "monattatstr": str(fc.tag),
                "ort": ort,
                "bundesland": bundesland,
                "history": SafeString(jstr),
                "stationen": stations,
                "heutetag": heute.day,
                "heutemonat": fc.get_month(heute.month)[0:3],
                "heutejahr": heute.year
            })
    except:
        msg = "Entschuldigung, das hat leider nicht geklappt. \
        Wahrscheinlich gab es eine Problem mit der Bereitsstellung der Daten. \
        Versuche es bitte mit einen anderen Ort. "
        e = sys.exc_info()[0]
        
        return render(request, "wetter/index.html", {"error": msg,"err_info":e})


def plz(request):
    plz = Plz()
    data = plz.query(request.GET['query'])
    return JsonResponse(data, safe=False)


def monattage(request):
    monattage = Monattage()
    data = monattage.query(request.GET['query'])
    return JsonResponse(data, safe=False)
