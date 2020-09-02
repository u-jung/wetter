      $(document).ready(function(){

        
        /*oydata={{oy}};*/
        vars={"TXK":{},"RSK":{},"SDK":{},"PM":{},"UPM":{}};
        //var ii=0;
        for ( var ii=0; ii<3;ii++){
          ["TXK","RSK","SDK","PM","UPM"].forEach(
            function createPlot(item,index){
              
              if (typeof wdata[ii][item] !== 'undefined'){
                
                ind=[];
                wdata[ii][item]['index'].forEach(function(item){ind.push(item.slice(0,4))});
                
                vars[item][ii]={
                  /*x:ind,*/
                  x:wdata[ii][item]['data'],
                  name: wdata[ii]["Stationsname"]+"/"+wdata[ii]["Bundesland"]+ " ["+wdata[ii]["Stationshoehe"]+"m] ("+parseInt(wdata[ii].von_datum/10000) +"-"+ parseInt(wdata[ii].bis_datum/10000) + ")",
                  boxpoints: 'Outliers',
                  jitter: 0.3,
                  /*pointpos: -1.8,*/
                  boxmean: true,
                  type:'box'
                };
                
              };
             }
          );
        };
        legende={"TXK":"Tagesmaximum der Lufttemperatur in 2m Höhe (°C)",
          "RSK":"tägliche Niederschlagshöhe (mm)",
          "SDK":"tägliche Sonnenscheindauer (h)",
          "PM":"Tagesmittel des Luftdrucks (hPa)",
          "UPM":"Tagesmittel der relativen Feuchte (%)"};
        
        Object.keys(legende).forEach(function(key) {
          data=[]
          
          for (var i=0; i< Object.keys(vars[key]).length;i++){
            
            data.push(vars[key][i]);
          };
          var layout = {
            title:legende[key],
                xaxis: {
                    autorange: true,
                    showgrid: true,
                    zeroline: true,
                    dtick: 5,
                    gridcolor: 'rgb(255, 255, 255)',
                    gridwidth: 1,
                    zerolinecolor: 'rgb(255, 255, 255)',
                    zerolinewidth: 2
                },
                margin: {
                    l: 40,
                    r: 30,
                    b: 80,
                    t: 100
                },
                paper_bgcolor: 'rgb(243, 243, 243)',
                plot_bgcolor: 'rgb(243, 243, 243)'
          }
          
          Plotly.newPlot(key.toLowerCase()+"0",[...data],layout,{responsive: true});
        });

         t_data={};

         for(var j=0; j<wdata.length;j++){
            t_data[j]=[];
            jQuery("#tab-tit"+j).html("<h3>"+wdata[j]["Stationsname"]+"</h3>");
            for(var i=0; i< wdata[j]["TXK"]["index"].length; i++){
              t_data[j].push(
                {"Jahr":wdata[j]["TXK"]["index"][i].slice(0,4),
                  "TXK":wdata[j]["TXK"]["data"][i]+" °C",
                  "RSK":wdata[j]["RSK"]["data"][i]+" mm",
                  "SDK":wdata[j]["SDK"]["data"][i]+ " h",
                  "PM":wdata[j]["PM"]["data"][i] + " hPa",
                  "UPM":wdata[j]["UPM"]["data"][i] + " %",
                }

              );

            }
            console.log('#tab'+j);
            jQuery('#tab'+j).DataTable( {
            data: t_data[j],
            columns: [
                { data: 'Jahr' },
                { data: 'TXK' },
                { data: 'RSK' },
                { data: 'SDK' },
                { data: 'PM' },
                { data: 'UPM' }
            ]
             } );
         };




      });