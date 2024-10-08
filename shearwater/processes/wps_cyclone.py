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

# import intake

import logging
LOGGER = logging.getLogger("PYWPS")

FORMAT_PNG = Format("image/png", extension=".png", encoding="base64")

class Cyclone(Process):
    """A process to forecast tropical cyclone activities."""
    def __init__(self):
        inputs = [
            LiteralInput(
                "start_day",
                "Start Day",
                data_type="string",
                abstract="Enter the start date, like 2024-05-01",
                default="2024-05-01"
            ),
            LiteralInput(
                "end_day",
                "End Day",
                data_type="string",
                abstract="Enter the end date, like 2024-05-28",
                default="2024-05-28"
            ),
            LiteralInput(
                "area",
                "Area",
                data_type="string",
                abstract="Choose the region of your interest",
                allowed_values=[
                    "Sindian",
                    "TBD"
                ],
                default="Sindian",
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
        import metview as mv
        from tensorflow.keras import models

        start_date = request.inputs['start_day'][0].data
        end_date = request.inputs['end_day'][0].data
        # area = request.inputs['area'][0].data

        parameters = [
            [138, "vo", [850]],
            [157, "r", [700]],
            [131, "u", [200, 850]],
            [132, "v", [200, 850]],
            [34, "sst", [0]],
            [137, "tcwv", [0]],
        ]
        reso = 2.5
        area_bbox = [0, 20, -30, 90]

        data = pd.DataFrame()
        for param1 in parameters:
            path = f'/pool/data/ERA5/ET/{"sf" if param1[2]==[0] else "pl"}/an/1D/{str(param1[0]).zfill(3)}'
            fs1_param = mv.read(
                f"{path}/ET{'sf' if param1[2]==[0] else 'pl'}00_1D_{start_date[:7]}_{str(param1[0]).zfill(3)}.grb"
            )
            fs1_param = fs1_param.select(
                date=start_date.replace("-", ""), level=param1[2]
            )
            fs1_param_interp = mv.read(
                data=fs1_param,
                grid=[reso, reso],
                area=area_bbox,
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
        data.loc[:, "time"] = start_date
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
        model_path = os.path.join(workdir, "Unet_sevenAreas_fullStd_0lag_model.keras")
        urllib.request.urlretrieve(
            "https://github.com/climateintelligence/shearwater/raw/main/data/Unet_sevenAreas_fullStd_0lag_model.keras",
            model_path  # "Unet_sevenAreas_fullStd_0lag_model.keras"
        )

        model_trained = models.load_model(model_path)

        prediction = model_trained.predict(test_img_std)

        data = data[["latitude", "longitude", "time"]]
        data['predictions_lag0'] = prediction.reshape(-1, 1)

        prediction_path = os.path.join(workdir, "prediction_Sindian.csv")
        data.to_csv(prediction_path)

        lag = 0
        workdir = Path(self.workdir)
        outfilename = os.path.join(
            workdir, f'tcactivity_48_17_{start_date.replace("-","")}_lag{lag}_Sindian'
        )

        if True:
            predscol = f"predictions_lag{lag}"
            gpt = mv.create_geo(
                latitudes=data["latitude"].values,
                longitudes=data["longitude"].values,
                values=data[predscol].values,
            ).set_dates([pd.Timestamp(start_date)] * data.shape[0])
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
                map_area_definition="corners", area=area_bbox, coastlines=coastlines
            )
            legend = mv.mlegend(
                legend_text_font_size=0.5,
            )

            mv.setoutput(mv.png_output(output_name=outfilename + ".png"))
            mv.plot(gview, fs, cont_oper, legend)
            response.outputs["output_png"].data = outfilename + ".png"
        # else:
            data.to_csv(outfilename + ".csv")
            response.outputs["output_csv"].data = outfilename + ".csv"

        # response.outputs['output_csv'].file = prediction_path
        return response
