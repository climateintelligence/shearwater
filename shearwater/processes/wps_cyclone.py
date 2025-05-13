from pywps import Process, LiteralInput, ComplexOutput
from pywps.app.Common import Metadata
from pywps.app.exceptions import ProcessError
import numpy as np
import numpy
import pandas as pd
import os
from pywps import FORMATS, Format
from pathlib import Path
import urllib.request
import xarray as xr

try:
    import metview as mv
except Exception:
    print("sorry ... no metview")
    print(f"{os.environ}")
    mv = None
import matplotlib.pyplot as plt

import logging

LOGGER = logging.getLogger("PYWPS")

FORMAT_PNG = Format("image/png", extension=".png", encoding="base64")


class Cyclone(Process):
    """A process to forecast tropical cyclone activity."""

    def __init__(self):
        inputs = [
            LiteralInput(
                "init_date",
                "Initialisation date",
                data_type="string",
                abstract="""Enter an initialisation date between 1940-01-01 and 2024-12-31.
                Note that the years 1980-2015 have been used for training and tuning the ML models.""",
                default="2024-07-03",
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
                default="0-48 h",
            ),
            LiteralInput(
                "region",
                "Region",
                data_type="string",
                abstract="Choose the region of your interest",
                allowed_values=[
                    "Australia",
                    "East Pacific",
                    "North Atlantic",
                    "Northern Indian",
                    "Northwest Pacific",
                    "South Pacific",
                    "Southern Indian",
                ],
                default="North Atlantic",
            ),
        ]
        outputs = [
            ComplexOutput(
                "output_csv",
                "Tropical cyclone activity forecast",
                abstract="csv file",
                as_reference=True,
                keywords=["output", "result", "response"],
                supported_formats=[FORMATS.CSV],
            ),
            ComplexOutput(
                "output_png",
                "Tropical cyclone activity forecast",
                abstract="png file",
                as_reference=True,
                supported_formats=[FORMAT_PNG],
            ),
        ]

        super(Cyclone, self).__init__(
            self._handler,
            identifier="cyclone",
            title="Tropical cyclone activity",
            abstract="A process to forecast tropical cyclone activity in tropical ocean basins up to 15 days ahead.",
            metadata=[
                Metadata("PyWPS", "https://pywps.org/"),
            ],
            version="0.1",
            inputs=inputs,
            outputs=outputs,
            store_supported=True,
            status_supported=True,
        )

    def _handler(self, request, response):
        msg = "Running tropical cyclone activity process ..."
        LOGGER.info(msg)
        response.update_status(msg, 0)
        # TODO: lazy load tensorflow ... issues with sphinx doc build
        try:
            from tensorflow.keras import models
        except Exception as ex:
            msg = "Models from tensorflow.keras could not be imported. Reason for the failure: {} ".format(
                ex
            )
            LOGGER.error(msg)

        try:
            init_date = request.inputs["init_date"][0].data
            LOGGER.info(init_date)
            leadtime = request.inputs["leadtime"][0].data
            LOGGER.info(leadtime)
            region = request.inputs["region"][0].data
            LOGGER.info(region)
        except Exception as ex:
            msg = (
                "Input variables could not be set. Reason for the failure: {} ".format(
                    ex
                )
            )
            LOGGER.error(msg)

        # Check validity of input date
        VALIDstr = pd.Timestamp("1940-01-01")
        VALIDend = pd.Timestamp("2024-12-31")
        if (pd.Timestamp(init_date) >= VALIDstr) & (
            pd.Timestamp(init_date) <= VALIDend
        ):
            msg = "Input date is valid."
            LOGGER.info(msg)

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
                "Southern Indian": [0, 20, -30, 90],  # Southern Indian
                "North Atlantic": [40, -90, 10, -20],  # North Atlantic
                "Northwest Pacific": [35, 100, 5, 170],  # Northwest Pacific
                "Australia": [0, 90, -30, 160],  # Australia
                "Northern Indian": [30, 30, 0, 100],  # Northern Indian
                "East Pacific": [30, -170, 0, -100],  # East Pacific
                "South Pacific": [0, 160, -30, 230],  # South Pacific
            }

            lags_dict = {
                "0-48 h": 0,
                "24-72 h": 1,
                "48-96 h": 2,
                "72-120 h": 3,
                "96-144 h": 4,
                "120-168 h": 5,
                "144-192 h": 6,
                "168-216 h": 7,
                "192-240 h": 8,
                "216-264 h": 9,
                "240-288 h": 10,
                "264-312 h": 11,
                "288-336 h": 12,
                "312-360 h": 13,
            }

            region_string = {
                "Southern Indian": "Sindian",  # Southern Indian
                "North Atlantic": "Natlantic",  # North Atlantic
                "Northwest Pacific": "NWpacific",  # Northwest Pacific
                "Australia": "Australia",  # Australia
                "Northern Indian": "Nindian",  # Northern Indian
                "East Pacific": "Epacific",  # East Pacific
                "South Pacific": "Spacific",  # South Pacific
            }

            region_bbox = regions_dict[region]
            lag = lags_dict[leadtime]

            data = pd.DataFrame()

            if mv:
                for param1 in parameters:
                    path = f'/pool/data/ERA5/E5/{"sf" if param1[2]==[0] else "pl"}/an/1D/{str(param1[0]).zfill(3)}'
                    filename_part2 = f"{init_date[:7]}_{str(param1[0]).zfill(3)}"
                    fs1_param = mv.read(
                        f"{path}/E5{'sf' if param1[2]==[0] else 'pl'}00_1D_{filename_part2}.grb"
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

            else:
                reg = region_string[region]
                data1 = pd.read_csv(
                    f"https://github.com/climateintelligence/shearwater/raw/main/data/test_dailymeans_{reg}_1.zip"
                )
                data2 = pd.read_csv(
                    f"https://github.com/climateintelligence/shearwater/raw/main/data/test_dailymeans_{reg}_2.zip"
                )
                data = pd.concat((data1, data2), ignore_index=True)
                data = data.loc[(data.time == init_date)]

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
                "https://github.com/climateintelligence/shearwater/raw/main/data/full_statistics.zip"
            )

            data[variables] = (data[variables] - means[variables]) / stds[variables]

            sz_lat = len(data.latitude.dropna().unique())
            sz_lon = len(data.longitude.dropna().unique())
            number_of_img, rows, cols = len(data.time.unique()), sz_lat, sz_lon
            images = np.zeros((number_of_img, rows, cols, len(variables)))
            df = data.sort_values(by=["time", "latitude", "longitude"])
            verbose = False
            k = 0
            for day in range(0, number_of_img):

                a = df.iloc[377 * day : 377 * (day + 1)]
                i = 0
                for var in variables:
                    anew = a.pivot(index="latitude", columns="longitude").sort_index(
                        ascending=False
                    )[var]
                    images[day, :, :, i] = anew
                    i += 1
                k += 1
                if (k % 100 == 0) & (verbose is True):
                    print(k)

            test_img_std = images
            # print("images", test_img_std)

            test_img_std = np.pad(
                test_img_std, ((0, 0), (1, 2), (1, 2), (0, 0)), "constant"
            )

            workdir = Path(self.workdir)
            LOGGER.info(workdir)
            model_path = os.path.join(
                workdir, f"UNET020_sevenAreas_fullStd_{lag}lag_model.keras"
            )
            git_path = "https://github.com/climateintelligence/shearwater/raw/main"
            urllib.request.urlretrieve(
                f"{git_path}/data/UNET020_sevenAreas_fullStd_{lag}lag_model.keras",
                model_path,
            )

            model_trained = models.load_model(model_path)

            prediction = model_trained.predict(test_img_std)

            data = data[["latitude", "longitude", "time"]]
            data[f"predictions_lag{lag}"] = prediction.reshape(-1, 1)

            workdir = Path(self.workdir)
            outfilename = os.path.join(
                workdir,
                f'tcactivity_48_17_{init_date.replace("-","")}_lag{lag}_{region_string[region]}',
            )

            if mv:
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
                    map_coastline_land_shade="on",
                    map_coastline_land_shade_colour="grey",
                )

                gview = mv.geoview(
                    map_area_definition="corners",
                    area=region_bbox,
                    coastlines=coastlines,
                )
                legend = mv.mlegend(
                    legend_text_font_size=0.5,
                )

                VTstr = (
                    pd.Timestamp(init_date) + pd.Timedelta(str(lag) + "d")
                ).strftime("%Y-%m-%d") + " 00Z"
                laggg = pd.Timedelta(str(2) + "d")
                VTend = (
                    pd.Timestamp(init_date) + pd.Timedelta(str(lag) + "d") + laggg
                ).strftime("%Y-%m-%d") + " 00Z"
                subtitle1 = f"<font size='0.4'>{region}, Initialisation: {init_date} 00Z, Lead time: {leadtime}"
                subtitle2 = f", Valid time: {VTstr+' to '+VTend}</font>"
                title = mv.mtext(
                    text_font_size=0.50,
                    text_lines=[
                        "<font size='0.7'>Probability of tropical cyclone activity</font>",
                        subtitle1 + subtitle2,
                        "",
                    ],
                    text_colour="CHARCOAL",
                )

                mv.setoutput(mv.png_output(output_name=outfilename))
                mv.plot(gview, fs, cont_oper, legend, title)
                response.outputs["output_png"].file = outfilename + ".1.png"

                data.to_csv(outfilename + ".csv")
                response.outputs["output_csv"].file = outfilename + ".csv"
            else:
                xr_predictions = xr.Dataset.from_dataframe(
                    data.set_index(["time", "latitude", "longitude"])
                )
                xr_predictions = xr_predictions[f"predictions_lag{lag}"]

                figs, axs = plt.subplots()
                xr_predictions.plot(ax=axs)
                plt.savefig(outfilename + ".png")

                response.outputs["output_png"].file = outfilename + ".png"

                data.to_csv(outfilename + ".csv")
                response.outputs["output_csv"].file = outfilename + ".csv"

        else:
            msg = f"Input date '{init_date}' outside the allowed period."
            LOGGER.error(msg)
            response.update_status(msg, 3)
            raise ProcessError(msg)

        return response
