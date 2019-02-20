#!/usr/bin/env python
# # -*- coding: utf-8 -*-

"""
Test script for omas/omas_core.py

.. code-block:: none

   python -m unittest omas/tests/test_omas_core

-------
"""

# Basic imports
from __future__ import print_function, division, unicode_literals
import unittest
import numpy
from pprint import pprint

# OMAS imports
from omas import *
from omas.omas_setup import *


class TestOmasCore(unittest.TestCase):
    """
    Test suite for omas_physics.py
    """

    # Flags to edit while testing
    verbose = False  # Spammy, but occasionally useful for debugging a weird problem

    # Utilities for this test
    def printv(self, *arg):
        """Utility for tests to use"""
        if self.verbose:
            print(*arg)

    def setUp(self):
        test_id = self.id()
        test_name = '.'.join(test_id.split('.')[-2:])
        self.printv('{}...'.format(test_name))

    def tearDown(self):
        test_name = '.'.join(self.id().split('.')[-2:])
        self.printv('    {} done.'.format(test_name))

    def test_misc(self):
        ods = ODS()
        # check effect of disabling dynamic path creation
        try:
            ods.dynamic_path_creation = False
            ods['dataset_description.data_entry.user']
        except LookupError:
            ods['dataset_description'] = ODS()
            ods['dataset_description.data_entry.user'] = os.environ['USER']
        else:
            raise (Exception('OMAS error handling dynamic_path_creation=False'))
        finally:
            ods.dynamic_path_creation = True

        # check that accessing leaf that has not been set raises a ValueError, even with dynamic path creation turned on
        try:
            ods['dataset_description.data_entry.machine']
        except ValueError:
            pass
        else:
            raise (Exception('OMAS error querying leaf that has not been set'))

        # info ODS is used for keeping track of IMAS metadata
        ods['dataset_description.data_entry.machine'] = 'ITER'
        ods['dataset_description.imas_version'] = omas_rcparams['default_imas_version']
        ods['dataset_description.data_entry.pulse'] = 1
        ods['dataset_description.data_entry.run'] = 0

        # check .get() method
        assert (ods.get('dataset_description.data_entry.pulse') == ods['dataset_description.data_entry.pulse'])
        assert (ods.get('dataset_description.bad', None) is None)

        # check that keys is an iterable (so that Python 2/3 work the same way)
        keys = ods.keys()
        keys[0]

        # check that dynamic path creation during __getitem__ does not leave empty fields behind
        try:
            print(ods['wall.description_2d.0.limiter.unit.0.outline.r'])
        except ValueError:
            assert 'wall.description_2d.0.limiter.unit.0.outline' not in ods

        ods['equilibrium']['time_slice'][0]['time'] = 1000.
        ods['equilibrium']['time_slice'][0]['global_quantities']['ip'] = 1.5

        ods2 = copy.deepcopy(ods)
        ods2['equilibrium']['time_slice'][1] = ods['equilibrium']['time_slice'][0]
        ods2['equilibrium.time_slice.1.time'] = 2000.

        ods2['equilibrium']['time_slice'][2] = copy.deepcopy(ods['equilibrium']['time_slice'][0])
        ods2['equilibrium.time_slice[2].time'] = 3000.

        assert (ods2['equilibrium']['time_slice'][0]['global_quantities'].ulocation == ods2['equilibrium']['time_slice'][2]['global_quantities'].ulocation)

        ods2['equilibrium.time_slice.1.global_quantities.ip'] = 2.

        # check different ways of addressing data
        for item in [ods2['equilibrium.time_slice']['1.global_quantities'],
                     ods2[['equilibrium', 'time_slice', 1, 'global_quantities']],
                     ods2[('equilibrium', 'time_slice', 1, 'global_quantities')],
                     ods2['equilibrium.time_slice.1.global_quantities'],
                     ods2['equilibrium.time_slice[1].global_quantities']]:
            assert item.ulocation == 'equilibrium.time_slice.:.global_quantities'

        ods2['equilibrium.time_slice.0.profiles_1d.psi'] = numpy.linspace(0, 1, 10)

        # check data slicing
        assert numpy.all(ods2['equilibrium.time_slice[:].global_quantities.ip'] == numpy.array([1.5, 2.0, 1.5]))

        # uncertain scalar
        ods2['equilibrium.time_slice[2].global_quantities.ip'] = ufloat(3, 0.1)

        # uncertain array
        ods2['equilibrium.time_slice[2].profiles_1d.q'] = uarray([0., 1., 2., 3.], [0, .1, .2, .3])

        ckbkp = ods.consistency_check
        tmp = pickle.dumps(ods2)
        ods2 = pickle.loads(tmp)
        if ods2.consistency_check != ckbkp:
            raise (Exception('consistency_check attribute changed'))

        # check flattening
        tmp = ods2.flat()
        # pprint(tmp)

        # check deepcopy
        ods3 = ods2.copy()

    def test_coordinates(self):
        ods = ods_sample()
        assert (len(ods.list_coordinates()) > 0)
        assert (len(ods['equilibrium'].list_coordinates()) > 0)

    def test_time(self):
        # test generation of a sample ods
        ods = ODS()
        ods['equilibrium.time_slice'][0]['time'] = 100
        ods['equilibrium.time_slice.0.global_quantities.ip'] = 0.0
        ods['equilibrium.time_slice'][1]['time'] = 200
        ods['equilibrium.time_slice.1.global_quantities.ip'] = 1.0
        ods['equilibrium.time_slice'][2]['time'] = 300
        ods['equilibrium.time_slice.2.global_quantities.ip'] = 2.0

        # get time information from children
        extra_info = {}
        assert numpy.allclose(ods.time('equilibrium', extra_info=extra_info), [100, 200, 300])
        assert extra_info['location'] == 'equilibrium.time_slice.:.time'
        assert extra_info['homogeneous_time'] is True
        assert ods['equilibrium'].homogeneous_time() is True

        # time arrays can be set using `set_time_array` function
        # this simplifies the logic in the code since one does not
        # have to check if the array was already there or not
        ods.set_time_array('equilibrium.time', 0, 101)
        ods.set_time_array('equilibrium.time', 1, 201)
        ods.set_time_array('equilibrium.time', 2, 302)

        # the make the timeslices consistent
        ods['equilibrium.time_slice'][0]['time'] = 101
        ods['equilibrium.time_slice'][1]['time'] = 201
        ods['equilibrium.time_slice'][2]['time'] = 302

        # get time information from explicitly set time array
        extra_info = {}
        assert numpy.allclose(ods.time('equilibrium', extra_info=extra_info), [101, 201, 302])
        assert extra_info['homogeneous_time'] is False
        assert ods['equilibrium'].homogeneous_time() is False

        # get time value from a single item in array of structures
        extra_info = {}
        assert ods['equilibrium.time_slice'][0].time(extra_info=extra_info) == 101
        assert extra_info['homogeneous_time'] is None
        tmp = ods['equilibrium']
        assert tmp.homogeneous_time('time_slice.0') is True
        assert ods['equilibrium'].homogeneous_time('time_slice.0', default=False) is False

        # get time array from array of structures
        extra_info = {}
        assert numpy.allclose(ods['equilibrium.time_slice'].time(extra_info=extra_info), [101, 201, 302])
        assert extra_info['homogeneous_time'] is False
        assert ods['equilibrium'].homogeneous_time() is False

        # get time from parent
        extra_info = {}
        assert ods.time('equilibrium.time_slice.0.global_quantities.ip', extra_info=extra_info) == 101
        assert extra_info['homogeneous_time'] is None
        assert ods.homogeneous_time('equilibrium.time_slice.0.global_quantities.ip') is True
        assert ods.homogeneous_time('equilibrium.time_slice.0.global_quantities.ip', default=False) is False

        # slice at time
        ods1 = ods['equilibrium'].slice_at_time(101)
        numpy.allclose(ods.time('equilibrium'), [101])

    def test_address_structures(self):
        ods = ODS()

        # make sure data structure is of the right type
        assert isinstance(ods['core_transport'].omas_data, dict)
        assert isinstance(ods['core_transport.model'].omas_data, list)

        # append elements by using `+`
        for k in range(10):
            ods['equilibrium.time_slice.+.global_quantities.ip'] = k
        assert len(ods['equilibrium.time_slice']) == 10
        assert (ods['equilibrium.time_slice'][9]['global_quantities.ip'] == 9)

        # access element by using negative indices
        assert (ods['equilibrium.time_slice'][-1]['global_quantities.ip'] == 9)
        assert (ods['equilibrium.time_slice.-10.global_quantities.ip'] == 0)

        # set element by using negative indices
        ods['equilibrium.time_slice.-1.global_quantities.ip'] = -99
        ods['equilibrium.time_slice'][-10]['global_quantities.ip'] = -100
        assert (ods['equilibrium.time_slice'][-1]['global_quantities.ip'] == -99)
        assert (ods['equilibrium.time_slice'][-10]['global_quantities.ip'] == -100)

        # access by pattern
        assert (ods['@eq.*1.*.ip'] == 1)

    def test_version(self):
        ods = ODS(imas_version='3.20.0')
        ods['ec_antennas.antenna.0.power'] = 1.0

        try:
            ods = ODS(imas_version='3.21.0')
            ods['ec_antennas.antenna.0.power'] = 1.0
            raise AssertionError('3.21.0 should not have `ec_antennas.antenna.0.power`')
        except LookupError:
            pass

    def test_satisfy_imas_requirements(self):
        ods = ods_sample()

        # check if data structures satisfy IMAS requirements (this should Fail)
        try:
            ods.satisfy_imas_requirements()
            raise (ValueError('It is expected that not all the sample structures have the .time array set'))
        except ValueError as _excp:
            pass

        # add .time information for all data structures
        while True:
            try:
                ods.satisfy_imas_requirements()
            except ValueError as _excp:
                # print(str(_excp).split()[0])
                ods[str(_excp).split()[0]] = [100]
            else:
                break

        # re-check if data structures satisfy IMAS requirements (this should pass)
        ods.satisfy_imas_requirements()


if __name__ == '__main__':
    suite = unittest.TestLoader().loadTestsFromTestCase(TestOmasCore)
    unittest.TextTestRunner(verbosity=2).run(suite)
