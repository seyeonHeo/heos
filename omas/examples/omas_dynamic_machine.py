#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Dynamic loading of experimental data
====================================
This example illustrates how OMAS can load in memory only the data when it is first requested.
This approach can also be used to transfer data on demand.
"""

import os
from omas import *
from omfit.classes.omfit_eqdsk import OMFITgeqdsk
from matplotlib import pyplot
from pprint import pprint

os.environ['OMAS_DEBUG_TOPIC'] = 'dynamic'

ods1 = ODS()
with ods1.open('machine', 'd3d', 168830, options={'EFIT_tree': 'EFIT01'}):
    g1 = OMFITgeqdsk(None).from_omas(ods1, time=2.1)

ods2 = ODS()
with ods2.open('machine', 'd3d', 168830, options={'EFIT_tree': 'EFIT02'}):
    g2 = OMFITgeqdsk(None).from_omas(ods2, time=2.1)

pprint(list(ods.flat().keys()))

g1.plot()
g2.plot()
pyplot.show()
