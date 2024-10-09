from pywps import Process, LiteralInput, ComplexOutput, LiteralOutput
from pywps.app.Common import Metadata
# from tensorflow.keras import models
# import pickle
import numpy as np
import numpy
import pandas as pd
# from datetime import datetime
import os
from pywps import FORMATS, Format
from pathlib import Path
import urllib.request
import metview as mv

# import intake

import logging
LOGGER = logging.getLogger("PYWPS")

FORMAT_PNG = Format("image/png", extension=".png", encoding="base64")

class Cyclone(Process):
    """A process to forecast tropical cyclone activities."""
    def __init__(self):
        inputs = [
            LiteralInput(
                "init_date",
                "Initialisation date",
                data_type="string",
                abstract="Enter the initialisation date, like 2024-02-17",
                default="2024-02-17"
            ),
            LiteralInput(
                "leadtime",
                "Lead time",
                data_type="string",
                abstract="Enter the lead time, like 0-48 h",
                allowed_values=[
                    "0-48 h",
                    "24-72 h",
                    "48-96 h",
                    "72-120 h",
                    "96-144 h",
                    "120-168 h",
                    "144-192 h",
                    "168-216 h",
                    "192-240 h",
                    "216-264 h",
                    "240-288 h",
                    "264-312 h",
                    "288-336 h",
                    "312-360 h",
                ],
                default="0-48 h"
            ),
            LiteralInput(
                "region",
                "Region",
                data_type="string",
                abstract="Choose the region of your interest",
                allowed_values=[
                    "Southern Indian",
                    "North Atlantic",
                    "Northwest Pacific",
                    "Australia",
                    "Northern Indian",
                    "East Pacific",
                    "South Pacific",
                ],
                default="Southern Indian",
            )
        ]
        outputs = [
            # LiteralOutput('output', 'Cyclone activity forecast',
            #               abstract='netcdf',
            #               # keywords=['output', 'result', 'response'],
            #               data_type='string'),
            ComplexOutput('output_csv', 'Cyclone activity forecast',
                          abstract='csv file',
                          as_reference=True,
                          keywords=['output', 'result', 'response'],
                          supported_formats=[FORMATS.CSV],),
            # LiteralOutput('output_png', 'Cyclone activity forecast',
                          # abstract='png file',
                          # keywords=['output', 'result', 'response'],
                          # data_type='string'),
            ComplexOutput(
                "output_png",
                "Cyclone activity forecast",
                abstract="png file",
                as_reference=True,
                supported_formats=[FORMAT_PNG],
            ),
        ]

        super(Cyclone, self).__init__(
            self._handler,
            identifier='cyclone',
            title='Cyclone',
            abstract='A process to forecast tropical cyclone activity.',
            # keywords=['hello', 'demo'],
            metadata=[
                Metadata('PyWPS', 'https://pywps.org/'),
            ],
            version='0.1',
            inputs=inputs,
            outputs=outputs,
            store_supported=True,
            status_supported=True
        )

    def _handler(self, request, response):
        LOGGER.info("running cyclone ...")
        # TODO: lazy load tensorflow ... issues with sphinx doc build
        from tensorflow.keras import models

        init_date = request.inputs['init_date'][0].data
        
        leadtime = request.inputs['leadtime'][0].data
        region = request.inputs['region'][0].data

        parameters = [
            [138, "vo", [850]],
            [157, "r", [700]],
            [131, "u", [200, 850]],
            [132, "v", [200, 850]],
            [34, "sst", [0]],
            [137, "tcwv", [0]],
        ]
        reso = 2.5

        regions_dict = {
                                # [ N,    E,   S,    W]
            "Southern Indian"   : [ 0,   20, -30,   90],   # Southern Indian
            "North Atlantic"    : [40,  -90,  10,  -20],   # North Atlantic
            "Northwest Pacific" : [35,  100,   5,  170],   # Northwest Pacific
            "Australia"         : [ 0,   90, -30,  160],   # Australia
            "Northern Indian"   : [30,   30,   0,  100],   # Northern Indian
            "East Pacific"      : [30, -170,   0, -100],   # East Pacific
            "South Pacific"     : [ 0,  160, -30,  230],   # South Pacific
        }
        
        lags_dict = {
             "0-48 h"    :  0,
             "24-72 h"   :  1,
             "48-96 h"   :  2,
             "72-120 h"  :  3,
             "96-144 h"  :  4,
             "120-168 h" :  5,
             "144-192 h" :  6,
             "168-216 h" :  7,
             "192-240 h" :  8,
             "216-264 h" :  9,
             "240-288 h" : 10,
             "264-312 h" : 11,
             "288-336 h" : 12,
             "312-360 h" : 13,
            }
        
        region_bbox = regions_dict[region]
        lag = lags_dict[leadtime]

        data = pd.DataFrame()
        for param1 in parameters:
            path = f'/pool/data/ERA5/E5/{"sf" if param1[2]==[0] else "pl"}/an/1D/{str(param1[0]).zfill(3)}'
            fs1_param = mv.read(
                f"{path}/E5{'sf' if param1[2]==[0] else 'pl'}00_1D_{init_date[:7]}_{str(param1[0]).zfill(3)}.grb"
            )
            fs1_param = fs1_param.select(
                date=init_date.replace("-", ""), level=param1[2]
            )
            fs1_param_interp = mv.read(
                data=fs1_param,
                grid=[reso, reso],
                area=region_bbox,
                interpolation='"--interpolation=grid-box-average"',
            )
            for level in param1[2]:
                data.loc[
                    :,
                    f"{param1[1]}{'_'+str(level) if (param1[1]=='u' or param1[1]=='v') else ''}",
                ] = (
                    fs1_param_interp.select(level=level)
                    .to_dataset()
                    .to_dataframe()
                    .reset_index(drop=True)[param1[1]]
                )

        data.loc[:, ["latitude", "longitude"]] = (
            fs1_param_interp.select(level=level)
            .to_dataset()
            .to_dataframe()
            .reset_index()[["latitude", "longitude"]]
        )
        data.loc[:, "time"] = init_date
        data.loc[:, "shear"] = (
            (data.u_200 - data.u_850) ** 2 + (data.v_200 - data.v_850) ** 2
        ) ** 0.5
        data.loc[:, "sst"] = data.sst.fillna(0)

        variables = [
            "vo",
            "r",
            "u_200",
            "u_850",
            "v_200",
            "v_850",
            "tcwv",
            "sst",
            "shear",
        ]

        means, stds = pd.read_pickle(
            "https://github.com/climateintelligence/shearwater/raw/main/data/full_statistics.zip")

        data[variables] = (data[variables]-means[variables])/stds[variables]

        number_of_img, rows, cols = len(data.time.unique()), len(data.latitude.unique()), len(data.longitude.unique())
        images = np.zeros((number_of_img, rows, cols, len(variables)))
        df = data.sort_values(by=['time', 'latitude', 'longitude'])
        verbose = False
        k = 0
        for day in range(0, number_of_img):

            a = df.iloc[377*day:377*(day+1)]
            i = 0
            for var in variables:
                images[day, :, :, i] = a.pivot(index='latitude', columns='longitude').sort_index(ascending=False)[var]
                i += 1
            k += 1
            if ((k % 100 == 0) & (verbose is True)):
                print(k)

        test_img_std = images

        test_img_std = np.pad(test_img_std, ((0, 0), (1, 2), (1, 2), (0, 0)), 'constant')

        workdir = Path(self.workdir)
        model_path = os.path.join(workdir, f"Unet_sevenAreas_fullStd_{lag}lag_model.keras")
        urllib.request.urlretrieve(
            f"https://github.com/climateintelligence/shearwater/raw/codeSprint/data/Unet_sevenAreas_fullStd_{lag}lag_model.keras",
            model_path
        )

        model_trained = models.load_model(model_path)

        prediction = model_trained.predict(test_img_std)

        data = data[["latitude", "longitude", "time"]]
        data[f'predictions_lag{lag}'] = prediction.reshape(-1, 1)

        workdir = Path(self.workdir)
        outfilename = os.path.join(
            workdir, f'tcactivity_48_17_{init_date.replace("-","")}_lag{lag}_Sindian'
        )

        if True:
            predscol = f"predictions_lag{lag}"
            gpt = mv.create_geo(
                latitudes=data["latitude"].values,
                longitudes=data["longitude"].values,
                values=data[predscol].values,
            ).set_dates([pd.Timestamp(init_date)] * data.shape[0])
            fs = mv.geo_to_grib(geopoints=gpt, grid=[2.5, 2.5], tolerance=1.5) * 1e2

            # cont_gen = mv.mcont(
            #     legend="on",
            #     contour_line_colour="avocado",
            #     contour_shade="on",
            #     contour_shade_technique="grid_shading",
            #     contour_shade_max_level_colour="red",
            #     contour_shade_min_level_colour="blue",
            #     contour_shade_colour_direction="clockwise",
            # )
            # cont_tc = mv.mcont(
            #     legend="on",
            #     contour_line_colour="avocado",
            #     contour_shade="on",
            #     contour_max_level=105,
            #     contour_min_level=0,
            #     contour_shade_technique="grid_shading",
            #     contour_shade_max_level_colour="red",
            #     contour_shade_min_level_colour="blue",
            #     contour_shade_colour_direction="clockwise",
            # )

            cont_oper = mv.mcont(
                contour_automatic_setting="style_name",
                contour_style_name="prob_green2yellow",
                legend="on",
            )
            coastlines = mv.mcoast(
                map_coastline_land_shade="on", map_coastline_land_shade_colour="grey"
            )

            gview = mv.geoview(
                map_area_definition="corners", area=region_bbox, coastlines=coastlines
            )
            legend = mv.mlegend(
                legend_text_font_size=0.5,
            )

            mv.setoutput(mv.png_output(output_name=outfilename)) # + ".png"))
            mv.plot(gview, fs, cont_oper, legend)
            response.outputs["output_png"].file = outfilename + ".1.png"
        # else:
            data.to_csv(outfilename + ".csv")
            response.outputs["output_csv"].file = outfilename + ".csv"

        return response
