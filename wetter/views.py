from django.shortcuts import render,HttpResponse
from django.http import JsonResponse
from .lib.dwd import Dwd, Forecast, Plz, Monattage
import pandas, json, re
from datetime import date
#import matplotlib.pyplot as plt
from django.utils.safestring import SafeString

# Create your view
def index(request):
   return render(request,'wetter/index.html')

def daten(request, geo,monattag):
  if "ort" in request.GET:
    ort=re.split("\ \d",request.GET['ort'])[0]
  else:
    ort=""
  
  p1=geo.split(",")
  fc=Forecast(p1[0],p1[1],50,monattag,3)
  aggregates=fc.get_aggregates()
  oy=[]
  #oy=SafeString(fc.aggregate_over_year())
  #oy=oy.replace( "None","null")
  #oy=oy.replace( "'",'"')
  jstr=SafeString(fc.make_history())
  jstr=jstr.replace( "None","null")
  jstr=jstr.replace( "'",'"')  
  heute=date.today()
  #raise ValueError (geo, p1)
  return render(request,'wetter/daten.html', {"aggr":fc.aggr,
                                              "geoBreite":p1[0], 
                                              "geoLaenge":p1[1],
                                              "monattag":str(fc.tag)+". "+fc.get_month(fc.monat)+"",
                                              "monattatstr":str(fc.tag),
                                              "ort":ort,
                                              "history":SafeString(jstr), 
                                              "stationen":[(x[0]["Stationsname"],x[0]["Bundesland"],x[0]["Stationshoehe"],x[1]) for x in fc.stationen],
                                              "heutetag":heute.day,
                                              "heutemonat":fc.get_month(heute.month)[0:3],
                                              "heutejahr":heute.year
  })



def plz(request):
  
  plz=Plz()
  #raise ValueError (plz.json)
  data=plz.query(request.GET['query'])
  return JsonResponse(data, safe=False)


def monattage(request):
  
  monattage=Monattage()
  #raise ValueError (plz.json)
  data=monattage.query(request.GET['query'])
  return JsonResponse(data, safe=False)