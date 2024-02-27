#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
gEQDSK + statefile to input.profiles
====================================
This example shows how OMAS can be used to generate a GACODE input.profiles
file given a gEQDSK file and a ONETWO statefile.
"""

from matplotlib import pyplot
import os
from omas import *

from omfit_classes.omfit_eqdsk import OMFITgeqdsk
from omfit_classes.omfit_onetwo import OMFITstatefile
from omfit_classes.omfit_gacode import OMFITinputprofiles

gfilename = omas_dir + 'samples/g145419.02100'  # gEQDSK file
sfilename = omas_dir + 'samples/state145419_02100.nc'  # ONETWO statefile
ipfilename = omas_dir + 'samples/input.profiles_145419_02100'  # input.profiles generated with PROFILES_GEN

# load OMFIT classes
gEQDSK = OMFITgeqdsk(gfilename)
statefile = OMFITstatefile(sfilename)
ip = OMFITinputprofiles(ipfilename)

# equilibrium ods from gEQDSK (and fluxSurfaces)
ods = gEQDSK.to_omas()

# append core profiles and sources based on ONETWO statefile
ods = statefile.to_omas(ods)

# generate new input.profiles file
ip1 = OMFITinputprofiles(ipfilename).from_omas(ods)

# compare the input.profiles file generated by PROFILES_GEN and the one generated via OMFIT+OMAS
ip.plot()
ip1.plot()
pyplot.show()
