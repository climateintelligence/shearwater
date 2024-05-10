from pywps import Process, LiteralInput, ComplexOutput
from pywps.app.Common import Metadata
# import birdy
# from tensorflow.keras import models
import pickle
import numpy as np
import numpy
import pandas as pd
# from datetime import datetime
import os
from pywps import FORMATS
from pathlib import Path

# import intake

import logging
LOGGER = logging.getLogger("PYWPS")


class Cyclone(Process):
    """A process to forecast tropical cyclone activities."""
    def __init__(self):
        inputs = [
            LiteralInput(
                "start_day",
                "Start Day",
                data_type="string",
                abstract="Enter the start date, like 2021-01-01",
                default="2022-01-01"
            ),
            LiteralInput(
                "end_day",
                "End Day",
                data_type="string",
                abstract="Enter the end date, like 2023-10-12",
                default="2022-01-31"
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
                          # keywords=['output', 'result', 'response'],
                          supported_formats=[FORMATS.CSV],)
        ]

        super(Cyclone, self).__init__(
            self._handler,
            identifier='cyclone',
            title='Cyclone',
            abstract='A process to forecast tropical cyclone activities.',
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

#         master_catalog = intake.open_catalog(["https://gitlab.dkrz.de/data-infrastructure-services/intake-esm/-/raw/master/esm-collections/cloud-access/dkrz_catalog.yaml"])  # noqa
#         # master_catalog = intake.open_catalog('/pool/data/Catalogs/dkrz_catalog.yaml')
#         era5_catalog = master_catalog['dkrz_era5_disk']

#         query = {
#             'era_id': 'ET',
#             'level_type': 'surface',
#             'table_id': 128,
#             # 'frequency':'hourly',
#             'code': 34,
#             'dataType': 'an',
#             'validation_date': '2023-06-27',
#         }

#         my_catalog = era5_catalog.search(**query)
#         # my_catalog.df

#         era_path = my_catalog.df['uri'].iloc[0]
#         response.outputs['output'].data = f'netcdf {era_path}'
#         response.outputs['output_csv'].data = 'csv ' + request.inputs['model'][0].data
#         return response

        start_date = request.inputs['start_day'][0].data
        end_date = request.inputs['end_day'][0].data
        # area = request.inputs['area'][0].data

        # to be updated with data repository
        data1 = pd.read_csv("https://github.com/climateintelligence/shearwater/raw/main/data/test_dailymeans_Sindian_1.zip") 
        # ("../shearwater/data/test_dailymeans_Sindian_1.zip")
        data2 = pd.read_csv("https://github.com/climateintelligence/shearwater/raw/main/data/test_dailymeans_Sindian_2.zip") 
        # ("../shearwater/data/test_dailymeans_Sindian_2.zip")
        data = pd.concat((data1, data2), ignore_index=True)
        data = data.loc[(data.time >= start_date) & (data.time <= end_date)]

        variables = ['vo', 'r', 'u_200', 'u_850', 'v_200', 'v_850', 'tcwv', 'sst', 'shear']
        with open("https://github.com/climateintelligence/shearwater/raw/main/data/full_statistics.pkl", 'rb') as f:
            means, stds = pickle.load(f)
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

        model_trained = models.load_model("https://github.com/climateintelligence/shearwater/raw/main/data/Unet_sevenAreas_fullStd_0lag_model.keras") 
        # ('../shearwater/data/Unet_sevenAreas_fullStd_0lag_model.keras')

        prediction = model_trained.predict(test_img_std)

        data = data[["latitude", "longitude", "time"]]
        data['predictions_lag0'] = prediction.reshape(-1, 1)

        workdir = Path(self.workdir)
        prediction_path = os.path.join(workdir, "prediction_Sindian.csv")
        data.to_csv(prediction_path)

        response.outputs['output_csv'].file = prediction_path
        return response
