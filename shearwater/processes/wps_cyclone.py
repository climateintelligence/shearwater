from pywps import Process, LiteralInput, LiteralOutput
from pywps.app.Common import Metadata
# from datetime import datetime

import intake

import logging
LOGGER = logging.getLogger("PYWPS")


class Cyclone(Process):
    """A process to forecast tropical cyclone activities. Minor change to test commit."""
    def __init__(self):
        inputs = [
            LiteralInput('model', 'Model name',
                         abstract='trained ML model ...: CNN, Unet',
                         # keywords=['name', 'firstname'],
                         default='CNN',
                         # allowed_values=['CNN', 'Unet'],
                         data_type='string'),
            LiteralInput('start_day', 'Start Day',
                         abstract='2023-10-12',
                         # keywords=['name', 'firstname'],
                         # default=f"{datetime.today()}",
                         data_type='string'),
        ]
        outputs = [
            LiteralOutput('output', 'Cyclone activity forecast',
                          abstract='netcdf',
                          # keywords=['output', 'result', 'response'],
                          data_type='string'),
            LiteralOutput('output_csv', 'Cyclone activity forecast',
                          abstract='csv file',
                          # keywords=['output', 'result', 'response'],
                          data_type='string')
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

    @staticmethod
    def _handler(request, response):
        LOGGER.info("running cyclone ...")

        master_catalog = intake.open_catalog(["https://gitlab.dkrz.de/data-infrastructure-services/intake-esm/-/raw/master/esm-collections/cloud-access/dkrz_catalog.yaml"])  # noqa
        # master_catalog = intake.open_catalog('/pool/data/Catalogs/dkrz_catalog.yaml')
        era5_catalog = master_catalog['dkrz_era5_disk']

        query = {
            'era_id': 'ET',
            'level_type': 'surface',
            'table_id': 128,
            # 'frequency':'hourly',
            'code': 34,
            'dataType': 'an',
            'validation_date': '2023-06-27',
        }

        my_catalog = era5_catalog.search(**query)
        # my_catalog.df

        era_path = my_catalog.df['uri'].iloc[0]
        response.outputs['output'].data = f'netcdf {era_path}'
        response.outputs['output_csv'].data = 'csv ' + request.inputs['model'][0].data
        return response
