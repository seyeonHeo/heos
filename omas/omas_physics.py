from __future__ import print_function, division, unicode_literals

import numpy
from .omas_utils import *

__all__ = []

def add_to__all__(f):
    __all__.append(f.__name__)
    return f

# constants class that mimics scipy.constants
class constants(object):
    e = 1.6021766208e-19

@add_to__all__
def core_profiles_pressures(ods, update=True):
    '''
    calculates individual ions pressures
        `core_profiles.profiles_1d.:.ion.:.pressure_thermal` #Pressure (thermal) associated with random motion ~average((v-average(v))^2)
        `core_profiles.profiles_1d.:.ion.:.pressure`         #Pressure (thermal+non-thermal)

    as well as total pressures

        `core_profiles.profiles_1d.:.pressure_thermal`       #Thermal pressure (electrons+ions)
        `core_profiles.profiles_1d.:.pressure_ion_total`     #Total (sum over ion species) thermal ion pressure
        `core_profiles.profiles_1d.:.pressure_perpendicular` #Total perpendicular pressure (electrons+ions, thermal+non-thermal)
        `core_profiles.profiles_1d.:.pressure_parallel`      #Total parallel pressure (electrons+ions, thermal+non-thermal)

    NOTE: the fast particles ion pressures are read, not set by this function:
        `core_profiles.profiles_1d.:.ion.:.pressure_fast_parallel`      #Pressure (thermal) associated with random motion ~average((v-average(v))^2)
        `core_profiles.profiles_1d.:.ion.:.pressure_fast_perpendicular` #Pressure (thermal+non-thermal)

    :param ods: input ods

    :param update: operate in place

    :return: updated ods
    '''
    ods_p = ods
    if not update:
        from omas import ODS
        ods_p = ODS().copy_attrs_from(ods)

    for time_index in ods['core_profiles']['profiles_1d']:
        prof1d = ods['core_profiles']['profiles_1d'][time_index]
        prof1d_p = ods_p['core_profiles']['profiles_1d'][time_index]
        __p__ = prof1d['electrons']['density'] * prof1d['electrons']['temperature'] * constants.e
        prof1d_p['pressure_thermal'] = __p__
        prof1d_p['pressure_ion_total'] = __p__ * 0.0
        prof1d_p['pressure_perpendicular'] = __p__ / 3.
        prof1d_p['pressure_parallel'] = __p__ / 3.
        for k in range(len(prof1d['ion'])):
            prof1d_p['ion'][k]['pressure'] = __p__ * 0.0
            for therm_fast, density in [('therm', 'density'), ('fast', 'density_fast')]:
                if (len(prof1d['ion']) and density in prof1d['ion'][k] and numpy.sum(
                        numpy.abs(prof1d['ion'][k][density])) > 0):
                    if therm_fast == 'therm':
                        __p__ = prof1d['ion'][k]['density'] * prof1d['ion'][k]['temperature'] * constants.e
                        prof1d_p['ion'][k]['pressure_thermal'] = __p__
                        prof1d_p['pressure_ion_total'] += __p__
                        prof1d_p['pressure_thermal'] += __p__
                        prof1d_p['pressure_perpendicular'] += __p__ / 3.
                        prof1d_p['pressure_parallel'] += __p__ / 3.
                    else:
                        if not update:
                            prof1d_p['ion'][k]['pressure_fast_perpendicular'] = prof1d['ion'][k][
                                'pressure_fast_perpendicular']
                            prof1d_p['ion'][k]['pressure_fast_parallel'] = prof1d['ion'][k]['pressure_fast_parallel']
                        prof1d_p['pressure_perpendicular'] += prof1d['ion'][k]['pressure_fast_perpendicular']
                        prof1d_p['pressure_parallel'] += prof1d['ion'][k]['pressure_fast_parallel']
                        __p__ = prof1d_p['ion'][k]['pressure_fast_perpendicular'] * 2 + prof1d_p['ion'][k]['pressure_fast_parallel']
                    prof1d_p['ion'][k]['pressure'] += __p__

        #extra pressure information that is not within IMAS structure is set only if consistency_check is not True
        if ods_p.consistency_check is not True:
            prof1d_p['pressure'] = prof1d_p['pressure_perpendicular'] * 2 + prof1d_p['pressure_parallel']
            prof1d_p['pressure_electron_total'] = prof1d_p['pressure_thermal'] - prof1d_p['pressure_ion_total']
            prof1d_p['pressure_fast'] = prof1d_p['pressure'] - prof1d_p['pressure_thermal']

    return ods_p

def define_cocos(cocos_ind):
    """
    Defines the cocos dictionary given a cocos index

    https://crppwww.epfl.ch/~sauter/COCOS/
    In the cocos, definition:
    The * marks that in these cases abs(q) is effectively used (since ideal axisymmetric MHD does not depend on its sign)

    Some codes do not really use the poloidal coordinates, therefore are compatible with two COCOS conventions (valid with sigma_rhotp = +-1). We mark with these cases ^ when we know it

    We do not discuss in detail the case where the phi direction is opposite in the cylindrical and the poloidal systems, since we think this case should not be used as it can be confusing.
    However it is used, for example by the ASTRA code[12], so we refer to '-COCOS' with the COCOS convention being the one obtained with phi in the direction of the positive magnetic field.
    """

    cocos=dict.fromkeys(['sigma_Bp', 'sigma_RpZ', 'sigma_rhotp', 'sign_q_pos', 'sign_pprime_pos', 'exp_Bp'])

    # if COCOS>=10, this should be 1
    cocos['exp_Bp'] = 0
    if cocos_ind>=10:
        cocos['exp_Bp'] = +1

    if cocos_ind in [1,11]:
        # These cocos are for
        # (1)  psitbx(various options), Toray-GA
        # (11) ITER, Boozer
        cocos['sigma_Bp']        = +1
        cocos['sigma_RpZ']       = +1
        cocos['sigma_rhotp']     = +1
        cocos['sign_q_pos']      = +1
        cocos['sign_pprime_pos'] = -1

    elif cocos_ind in [2,12,-12]:
        # These cocos are for
        # (2)  CHEASE, ONETWO, HintonHazeltine, LION, XTOR, MEUDAS, MARS, MARS-F
        # (12) GENE
        # (-12) ASTRA
        cocos['sigma_Bp']        = +1
        cocos['sigma_RpZ']       = -1
        cocos['sigma_rhotp']     = +1
        cocos['sign_q_pos']      = +1
        cocos['sign_pprime_pos'] = -1

    elif cocos_ind in [3,13]:
        # These cocos are for
        # (3) Freidberg*, CAXE and KINX*, GRAY, CQL3D^, CarMa, EFIT* with : ORB5, GBSwith : GT5D
        # (13) 	CLISTE, EQUAL, GEC, HELENA, EU ITM-TF up to end of 2011
        cocos['sigma_Bp']        = -1
        cocos['sigma_RpZ']       = +1
        cocos['sigma_rhotp']     = -1
        cocos['sign_q_pos']      = -1
        cocos['sign_pprime_pos'] = +1

    elif cocos_ind in [4,14]:
        #These cocos are for
        cocos['sigma_Bp']        = -1
        cocos['sigma_RpZ']       = -1
        cocos['sigma_rhotp']     = -1
        cocos['sign_q_pos']      = -1
        cocos['sign_pprime_pos'] = +1

    elif cocos_ind in [5,15]:
        # These cocos are for
        # (5) TORBEAM, GENRAY^
        cocos['sigma_Bp']        = +1
        cocos['sigma_RpZ']       = +1
        cocos['sigma_rhotp']     = -1
        cocos['sign_q_pos']      = -1
        cocos['sign_pprime_pos'] = -1

    elif cocos_ind in [6,16]:
        #These cocos are for
        cocos['sigma_Bp']        = +1
        cocos['sigma_RpZ']       = -1
        cocos['sigma_rhotp']     = -1
        cocos['sign_q_pos']      = -1
        cocos['sign_pprime_pos'] = -1

    elif cocos_ind in [7,17]:
        #These cocos are for
        # (17) LIUQE*, psitbx(TCV standard output)
        cocos['sigma_Bp']        = -1
        cocos['sigma_RpZ']       = +1
        cocos['sigma_rhotp']     = +1
        cocos['sign_q_pos']      = +1
        cocos['sign_pprime_pos'] = +1

    elif cocos_ind in [8,18]:
        #These cocos are for
        cocos['sigma_Bp']        = -1
        cocos['sigma_RpZ']       = -1
        cocos['sigma_rhotp']     = +1
        cocos['sign_q_pos']      = +1
        cocos['sign_pprime_pos'] = +1

    return cocos

@add_to__all__
def cocos_transform(cocosin_index, cocosout_index):
    """
    :param cocosin_index: COCOS index in

    :param cocosout_index: COCOS index out

    :return: transformation multipliers

    /home/matlab/crpptbx-8.3.0/CHEASEgui/eqdsk_cocos_transform.m
    https://crppwww.epfl.ch/~sauter/COCOS/
    Sauter, O., and S. Yu Medvedev. "Tokamak coordinate conventions: COCOS." Computer Physics Communications 184.2 (2013): 293-302.
    """

    cocosin = define_cocos(cocosin_index)
    cocosout = define_cocos(cocosout_index)

    sigma_Ip_eff = cocosin['sigma_RpZ'] * cocosout['sigma_RpZ']
    sigma_B0_eff = cocosin['sigma_RpZ'] * cocosout['sigma_RpZ']
    sigma_Bp_eff = cocosin['sigma_Bp'] * cocosout['sigma_Bp']
    exp_Bp_eff = cocosout['exp_Bp'] - cocosin['exp_Bp']
    sigma_rhotp_eff = cocosin['sigma_rhotp'] * cocosout['sigma_rhotp']

    # Transform
    transforms = {}
    transforms['dPSI'] = sigma_Ip_eff * sigma_Bp_eff / (2 * numpy.pi) ** exp_Bp_eff
    transforms['PSI'] = sigma_Ip_eff * sigma_Bp_eff * (2 * numpy.pi) ** exp_Bp_eff
    transforms['Q'] = sigma_Ip_eff * sigma_B0_eff * sigma_rhotp_eff
    transforms['BT'] = sigma_B0_eff
    transforms['IP'] = sigma_Ip_eff
    transforms['F'] = transforms['BT']
    transforms['F_FPRIME'] = transforms['dPSI']
    transforms['PPRIME'] = transforms['dPSI']

    printd("COCOS tranformation from "+str(cocosin_index)+" to "+str(cocosout_index),topic='cocos')
    printd(transforms,topic='cocos')

    return transforms

#this dictionary defines the IMAS locations and the `cocos_transform` function
cocos_signals = {}
cocos_signals['equilibrium.time_slice.:.profiles_1d.psi'] = 'PSI'
__all__.append('cocos_signals')
