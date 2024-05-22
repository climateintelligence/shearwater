==========
ShearWater
==========


.. image:: https://img.shields.io/pypi/v/shearwater.svg
        :target: https://pypi.python.org/pypi/shearwater

.. image:: https://img.shields.io/travis/cehbrecht/shearwater.svg
        :target: https://travis-ci.com/cehbrecht/shearwater

.. image:: https://readthedocs.org/projects/shearwater/badge/?version=latest
        :target: https://shearwater.readthedocs.io/en/latest/?version=latest
        :alt: Documentation Status

.. image:: https://img.shields.io/github/license/cehbrecht/shearwater.svg
    :target: https://github.com/cehbrecht/shearwater/blob/master/LICENSE.txt
    :alt: GitHub license

.. image:: https://badges.gitter.im/bird-house/birdhouse.svg
    :target: https://gitter.im/bird-house/birdhouse?utm_source=badge&utm_medium=badge&utm_campaign=pr-badge&utm_content=badge
    :alt: Join the chat at https://gitter.im/bird-house/birdhouse

ShearWater (the bird)
  *ShearWater is a bird to perform detection and forecast of tropical cyclone activity.*

This WPS is designed to perform detection and forecast of tropical-cyclone activities. In particular, the work at the basis of this WPS focuses on predicting the probability of TC activity in some regions of interest, therefore considering spatio-temporally distributed input features and target variable, in the form of gridded data with daily values. The main purpose of this work resides in daily predictions of the probability of TC activity. For this reason, the problem is formulated as a classification problem with binary targets, where the evaluation takes into account the calibration of the predicted probabilities. The target variable, derived from the International Best Track Archive for Climate Stewardship (IBTrACS), is defined as the occurrence of at least one TC exceeding tropical storm strength (>= 17m/s) evaluated within a 48-hour time window and a radius of 300 km at each grid point in the region of interest. Meteorologically relevant features are taken from the ERA5 atmospheric reanalysis dataset, produced by the Copernicus Climate Change Service at ECMWF. The training dataset covers the years 1980 to 2010, providing a substantial amount of historical data to build a robust predictive model (11323 daily values). The validation dataset includes the years from 2011 to 2015 (1826 daily values), allowing for the evaluation and fine-tuning of the model performance. Finally, the test dataset spans from 15 April 2016 to 31 December 2022 (2452 daily values). Additionally, a live connection to the ERA5 catalogue will be implemented as a next step, to enable this WPS to produce forecasts spanning from 15 April 2016 to the current day.

Three main hyperparameters are the core of this WPS. 
Firstly, a region can be selected among six possibilities available, covering the six main basins where TC activity is particularly relevant: Southern India, North Atlantic, North-West Pacific, Australia, Northern India, East Pacific. The current implementation of the WPS only includes the Southern India region, while the other regions will be available in next releases. 
Then, an interval of dates can be selected spanning from 15 April 2016 to the current day, depending on the period of interest of the user for the detection/forecast. As mentioned, the current implementation only spans from 15 April 2016 to 31 December 2022, and it will be updated in next releases. For each selected date, the forecast for each of the subsequent 14 days is provided. If these dates are in the past, the user can validate the forecast skills of the selected model w.r.t. other forecasts. If these days are in the future, this can be actually considered as a forecast. The current implementation only performs the forecast of the TC activity of the current day, next releases will include the forecast in the subsequent 14 days. 
Finally, the user can select the model of interest. The default model is a purely data-driven model, based on a Unet implementation that takes a set of meteorological features as inputs, treating them as channels of an image, and it produces the forecast of prediction probabilities, in the shape of as a grayscale image. Future implementations will include two additional models with different characteristics: the ECMWF’s ensemble forecast system, that produces a forecast based on climate models, and an hybrid approach, that combines a detection phase based on machine learning (the Unet mentioned above), with a forecast of the meteorological features based climate models. This way, the skillfullness of climate models in forecasting meteorological variables is combined with the skillfullness of the Unet to perform detection (i.e., extract TC activity from meteorological variables without lags).

Documentation
-------------

Learn more about ShearWater in its official documentation at
https://shearwater.readthedocs.io.

Submit bug reports, questions and feature requests at
https://github.com/cehbrecht/shearwater/issues

Contributing
------------

You can find information about contributing in our `Developer Guide`_.

Please use bumpversion_ to release a new version.


License
-------

* Free software: Apache Software License 2.0
* Documentation: https://shearwater.readthedocs.io.


Credits
-------

This package was created with Cookiecutter_ and the `bird-house/cookiecutter-birdhouse`_ project template.

.. _Cookiecutter: https://github.com/audreyr/cookiecutter
.. _`bird-house/cookiecutter-birdhouse`: https://github.com/bird-house/cookiecutter-birdhouse
.. _`Developer Guide`: https://shearwater.readthedocs.io/en/latest/dev_guide.html
.. _bumpversion: https://shearwater.readthedocs.io/en/latest/dev_guide.html#bump-a-new-version
