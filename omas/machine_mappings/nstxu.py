import os
import numpy as np
from inspect import unwrap
from omas import *
from omas.omas_utils import printd, printe, unumpy
from omas.machine_mappings._common import *
import glob

# NOTES:
# List of MDS+ signals
# https://nstx.pppl.gov/nstx/Software/FAQ/signallabels.html
# magnetics:
# https://nstx.pppl.gov/DragNDrop/Operations/Physics_Operations_Course/11%20OpsCourse_EquilibriumMagnetics_Rev1.pdf

__all__ = []
__regression_arguments__ = {'__all__': __all__}

def nstx_filenames(filename, pulse):
    if pulse >= 200184:# — > (200184 205433)
        path = '01152015Av1.0'
    elif pulse >= 112811: # — > (112811 143905)
        path = '04202005Av1.0'
    elif pulse >= 115151: #— > (115151 115178)
        path = '04122005Av1.0'
    elif pulse >= 106806:# — > (106806 114478)
        path = '02072002Av1.0'
    elif pulse >= 101099: # — > (101099 106807)
        path = '02222000Av1.0'
    filename = os.sep.join([omas_dir, 'machine_mappings', 'support_files', 'nstxu', path, filename])
    filename = glob.glob(filename + '*')[0]
    printd(f'Reading {filename}', topic='machine')
    return filename

@machine_mapping_function(__regression_arguments__, pulse=204202)
def pf_active_hardware(ods, pulse):
    r"""
    Loads NSTX-U tokamak poloidal field coil hardware geometry

    :param ods: ODS instance
    """
    from omfit_classes.omfit_efund import OMFITmhdin, OMFITnstxMHD

    mhdin = get_support_file(OMFITmhdin, nstx_filenames('mhdin', pulse))
    mhdin.to_omas(ods, update='pf_active')

    signals = get_support_file(OMFITnstxMHD, nstx_filenames('signals', pulse))
    icoil_signals = signals['mappings']['icoil']

    for c in ods[f'pf_active.coil']:
        for e in ods[f'pf_active.coil'][c]['element']:
            cname = icoil_signals[c + 1]['name']
            cid = icoil_signals[c + 1]['mds_name_resolved'].strip('\\')
            ename = icoil_signals[c + 1]['mds_name_resolved'].strip('\\') + f'_element_{e}'
            eid = ename
            ods[f'pf_active.coil'][c]['name'] = cname
            ods[f'pf_active.coil'][c]['identifier'] = cid
            ods[f'pf_active.coil'][c]['element'][e]['name'] = ename
            ods[f'pf_active.coil'][c]['element'][e]['identifier'] = eid


@machine_mapping_function(__regression_arguments__, pulse=140001)
def pf_active_coil_current_data(ods, pulse):
    r"""
    Load NSTX-U tokamak pf_active coil current data

    :param ods: ODS instance

    :param pulse: shot number
    """
    from omfit_classes.omfit_efund import OMFITnstxMHD

    ods1 = ODS()
    unwrap(pf_active_hardware)(ods1, pulse)

    with omas_environment(ods, cocosio=1):
        fetch_assign(
            ods,
            ods1,
            pulse,
            channels='pf_active.coil',
            identifier='pf_active.coil.{channel}.identifier',
            time='pf_active.coil.{channel}.current.time',
            data='pf_active.coil.{channel}.current.data',
            validity=None,
            mds_server='nstxu',
            mds_tree='NSTX',
            tdi_expression='\\{signal}',
            time_norm=1.0,
            data_norm=1.0,
            homogeneous_time=False
        )

    # handle uncertainties
    signals = get_support_file(OMFITnstxMHD, nstx_filenames('signals', pulse))
    icoil_signals = signals['mappings']['icoil']
    for channel in ods1['pf_active.coil']:
        if f'pf_active.coil.{channel}.current.data' in ods:
            data = ods[f'pf_active.coil.{channel}.current.data']
            rel_error = data * icoil_signals[channel + 1]['rel_error']
            abs_error = icoil_signals[channel + 1]['abs_error']
            error = np.sqrt(rel_error ** 2 + abs_error ** 2)
            error[data < icoil_signals[channel + 1]['sig_thresh']] = icoil_signals[channel + 1]['sig_thresh']
            ods[f'pf_active.coil.{channel}.current.data_error_upper'] = error

    # IMAS stores the current in the coil not multiplied by the number of turns
    for channel in ods1['pf_active.coil']:
        if f'pf_active.coil.{channel}.current.data' in ods:
            ods[f'pf_active.coil.{channel}.current.data'] /= ods1[f'pf_active.coil.{channel}.element.0.turns_with_sign']
        else:
            print(f'WARNING: pf_active.coil[{channel}].current.data is missing')


@machine_mapping_function(__regression_arguments__, pulse=140001)
def magnetics_hardware(ods, pulse):
    r"""
    Load NSTX-U tokamak flux loops and magnetic probes hardware geometry

    :param ods: ODS instance
    """
    from omfit_classes.omfit_efund import OMFITmhdin, OMFITnstxMHD

    mhdin = get_support_file(OMFITmhdin, nstx_filenames('mhdin', pulse))
    mhdin.to_omas(ods, update='magnetics')

    signals = get_support_file(OMFITnstxMHD, nstx_filenames('signals', pulse))

    for k in ods[f'magnetics.flux_loop']:
        ods[f'magnetics.flux_loop.{k}.identifier'] = str(signals['mappings']['tfl'][k + 1]['mds_name']).strip('\\')

    for k in ods[f'magnetics.b_field_pol_probe']:
        ods[f'magnetics.b_field_pol_probe.{k}.identifier'] = str(signals['mappings']['bmc'][k + 1]['mds_name']).strip('\\')


@machine_mapping_function(__regression_arguments__, pulse=204202)
def magnetics_floops_data(ods, pulse):
    r"""
    Load NSTX-U tokamak flux loops flux data

    :param ods: ODS instance

    :param pulse: shot number
    """
    from omfit_classes.omfit_efund import OMFITnstxMHD

    ods1 = ODS()
    unwrap(magnetics_hardware)(ods1, pulse)
    with omas_environment(ods, cocosio=1):
        fetch_assign(
            ods,
            ods1,
            pulse,
            channels='magnetics.flux_loop',
            identifier='magnetics.flux_loop.{channel}.identifier',
            time='magnetics.flux_loop.{channel}.flux.time',
            data='magnetics.flux_loop.{channel}.flux.data',
            validity='magnetics.flux_loop.{channel}.flux.validity',
            mds_server='nstxu',
            mds_tree='OPERATIONS',
            tdi_expression='\\{signal}',
            time_norm=1.0,
            data_norm=1.0 / 2.0 / np.pi,
        )

    # handle uncertainties
    signals = get_support_file(OMFITnstxMHD, nstx_filenames('signals', pulse))

    # flux loops
    tfl_signals = signals['mappings']['tfl']
    for channel in range(len(ods1['magnetics.flux_loop']) - 1):
        if f'magnetics.flux_loop.{channel}.flux.data' in ods:
            data = ods[f'magnetics.flux_loop.{channel}.flux.data']
            rel_error = data * tfl_signals[channel + 1]['rel_error']
            abs_error = tfl_signals[channel + 1]['abs_error'] / 2.0 / np.pi
            error = np.sqrt(rel_error ** 2 + abs_error ** 2)
            error[data < tfl_signals[channel + 1]['sig_thresh']] = tfl_signals[channel + 1]['sig_thresh']
            ods[f'magnetics.flux_loop.{channel}.flux.data_error_upper'] = error


@machine_mapping_function(__regression_arguments__, pulse=204202)
def magnetics_probes_data(ods, pulse):
    r"""
    Load NSTX-U tokamak magnetic probes field data

    :param ods: ODS instance

    :param pulse: shot number
    """
    from omfit_classes.omfit_efund import OMFITnstxMHD

    ods1 = ODS()
    unwrap(magnetics_hardware)(ods1, pulse)
    with omas_environment(ods, cocosio=1):
        fetch_assign(
            ods,
            ods1,
            pulse,
            channels='magnetics.b_field_pol_probe',
            identifier='magnetics.b_field_pol_probe.{channel}.identifier',
            time='magnetics.b_field_pol_probe.{channel}.field.time',
            data='magnetics.b_field_pol_probe.{channel}.field.data',
            validity='magnetics.b_field_pol_probe.{channel}.field.validity',
            mds_server='nstxu',
            mds_tree='OPERATIONS',
            tdi_expression='\\{signal}',
            time_norm=1.0,
            data_norm=1.0,
        )

    # handle uncertainties
    signals = get_support_file(OMFITnstxMHD, nstx_filenames('signals', pulse))
    bmc_signals = signals['mappings']['bmc']
    for channel in ods1['magnetics.b_field_pol_probe']:
        if f'magnetics.b_field_pol_probe.{channel}.field.data' in ods:
            data = ods[f'magnetics.b_field_pol_probe.{channel}.field.data']
            rel_error = data * bmc_signals[channel + 1]['rel_error']
            abs_error = bmc_signals[channel + 1]['abs_error']
            error = np.sqrt(rel_error ** 2 + abs_error ** 2)
            error[data < bmc_signals[channel + 1]['sig_thresh']] = bmc_signals[channel + 1]['sig_thresh']
            ods[f'magnetics.b_field_pol_probe.{channel}.field.data_error_upper'] = error


@machine_mapping_function(__regression_arguments__, pulse=204202)
def MDS_gEQDSK_psi_nstx(ods, pulse, EFIT_tree='EFIT01'):
    return MDS_gEQDSK_psi(ods, 'nstxu', pulse, EFIT_tree)


@machine_mapping_function(__regression_arguments__, pulse=204202)
def MDS_gEQDSK_bbbs_nstx(ods, pulse, EFIT_tree='EFIT01'):
    r"""
    Load NSTX-U EFIT boundary data

    :param ods: ODS instance

    :param pulse: shot number

    :param EFIT_tree: MDS+ EFIT tree
    """
    TDIs = {
        'r': f'\\{EFIT_tree}::TOP.RESULTS.GEQDSK.RBBBS',
        'z': f'\\{EFIT_tree}::TOP.RESULTS.GEQDSK.ZBBBS',
        'n': f'\\{EFIT_tree}::TOP.RESULTS.GEQDSK.NBBBS',
    }
    res = mdsvalue('nstxu', pulse=pulse, treename=EFIT_tree, TDI=TDIs).raw()
    res['n'] = res['n'].astype(int)
    for k in range(len(res['n'])):
        ods[f'equilibrium.time_slice.{k}.boundary.outline.r'] = res['r'][k, : res['n'][k]]
        ods[f'equilibrium.time_slice.{k}.boundary.outline.z'] = res['z'][k, : res['n'][k]]


@machine_mapping_function(__regression_arguments__, pulse=204202)
def ip_bt_dflux_data(ods, pulse):
    r"""
    Load NSTX-U tokamak Ip, Bt, and diamagnetic flux data

    :param ods: ODS instance

    :param pulse: shot number
    """
    from omfit_classes.omfit_efund import OMFITnstxMHD

    signals = get_support_file(OMFITnstxMHD, nstx_filenames('signals', pulse))

    # F_DIA does not work at least for 204202
    if pulse > 200000:
        signals['DL'][0]['mds_name'] = '\\F_DIAMAG2'
        signals['DL'][0]['mds_tree'] = 'operations'
        signals['DL'][0]['mds_tree_resolved'] = 'operations'

    mappings = {'PR': 'magnetics.ip.0', 'TF': 'tf.b_field_tor_vacuum_r', 'DL': 'magnetics.diamagnetic_flux.0'}

    TDIs = {}
    for item in ['PR', 'TF', 'DL']:
        TDIs[item + '_data'] = '\\' + signals[item][0]['mds_name'].strip('\\')
        TDIs[item + '_time'] = 'dim_of(\\' + signals[item][0]['mds_name'].strip('\\') + ')'
    res = mdsvalue('nstxu', pulse=pulse, treename='NSTX', TDI=TDIs).raw()

    for item in ['PR', 'TF', 'DL']:
        if not isinstance(res[item + '_data'], Exception) and not isinstance(res[item + '_time'], Exception):
            ods[mappings[item] + '.data'] = res[item + '_data'] * signals[item][0]['scale']
            ods[mappings[item] + '.time'] = res[item + '_time']
        else:
            printe(f'No data for {mappings[item]}')
            ods[mappings[item] + '.data'] = []
            ods[mappings[item] + '.time'] = []

    # handle uncertainties
    for item in ['PR', 'TF', 'DL']:
        if mappings[item] + '.data' in ods:
            data = ods[mappings[item] + '.data']
            rel_error = data * signals[item][0]['rel_error']
            abs_error = signals[item][0]['abs_error']
            error = np.sqrt(rel_error ** 2 + abs_error ** 2)
            error[data < signals[item][0]['sig_thresh'] * signals[item][0]['scale']] = (
                signals[item][0]['sig_thresh'] * signals[item][0]['scale']
            )
            ods[mappings[item] + '.data_error_upper'] = error


@machine_mapping_function(__regression_arguments__, pulse=140001)
def mse_data(ods, pulse, MSE_revision="ANALYSIS", MSE_Er_correction=True):
    r"""
    Load NSTX-U MSE data

    :param ods: ODS instance

    :param pulse: shot number

    :param MSE_revision: revision of the data to load

    :param MSE_Er_correction: Use pitch angle corrected data using Er from between-shot EFIT and CHERS

    NOTES:
    MSE constraint in GA EFIT code follows the description given in Brad Rice RSI Vol. 70 No. 1 (1999)
    Geometry follows right-handed coordinate system

    Alpha is the angle between a beam directed in +phi and the phi vector at the MSE measurement location
        Alpha is positive and less than 90 degrees for co-Ip beam, zero for a tangential beam, +90 deg for a radial beam
    Omega is the angle between the MSE sightline vector and phi vector at the MSE measurement location
        Omega is zero for tangential sightline that is pointed toward +phi (starting from the measurement, pointing to the MSE collection optics)
        Omega is +90 degrees for a radial sightline, assuming MSE port is on the outboard midplane
        Omega is 180 degrees for a tangential sightline that is pointed toward -phi

    NOTE: In this coordinate system, the omega = om_nstx + 180 degrees where om_nstx is the omega recorded in the MDS+ Tree
    **NOTE: The signs of the A1, A4, A5 and A7 coefficients are reversed compared to DIII-D to reflect the NSTX definition of omega

    In NSTX, standard operation is BT<0 (CCW) and Ip>0 (CW) ... identical to standard DIII-D operation
    Thus, Bpol>0 in theta dimension. Bz<0 at outboard midplane, Bz>0 at inboard midplane

    Gamma is the pitch of the local electric field relative to the MSE sightline vector (sigma polization component)
    GA EFIT assumes pitch angle (gamma) is the measured polarization angle
    NSTX MSE data is saved on the MDS+ tree as the actual field pitch angle = (A2/A1)*tan(gamma)
    The MSE data from MDS+ is multiplied by A1/A2 to convert the actual field pitch angle into the measured polization angle to be consistent with GA EFIT
    A2 and A1 are positive in the NSTX geometry
        For a co-Ip beam (+phi) with CCW BT, EZ = vb x Bphi is positive (+Z), Ephi = vb x Bz is negative (-phi) at outboard midplane
        Thus, on NSTX, with MSE sightline vectors pointing in -phi, postive R, gamma should be positive outboard of the magnetic axis
        This is consistent with the tan_alpha recorded in MDS+

    The A coefficients modified from for the NSTX convention are A1>0, A2>0, A5>0 for alpha and omega between 0 and 90 degrees
    At outboard midplane, BZ<0, Bphi<0, ER>0
        tan(gamma_cor) ~ [ (A1 Bz) / (A2 Bphi) ] - [ (A5 ER) / (A2 Bphi) ]  (assuming for simplicity that Br ~ 0)
    making
        tan(gamma_cor) ~ (big positive) - (small negative)
    Thus, tan(gamma_cor) is more positive than the reported tan(gamma)
    """
    beamline, beam_species, minVolt_keV, usebeam = ('1A', 'D', 40.0, True)
    geometries = [('ALPHA', f'{np.pi/180.0}', True), ('OMEGA', f'{np.pi/180.0}', True), ('RADIUS', '1', True)]

    if not MSE_Er_correction:
        # Uncorrected pitch angle from a subset of good channels
        measurements = ('PA', 'PA_ERR', f'{np.pi / 180.0}', 'tan_alpha', False)
    else:
        # Pitch angle corrected using Er uses between-shot EFIT and CHERS
        measurements = ('PA_CORR_ER', 'PA_ERR', f'{np.pi / 180.0}', 'tan_alpha', False)

    TDIs = {'time': f'\\MSE::TOP.MSE_CIF.{MSE_revision}.TIME'}

    # find average beam voltage
    voltage = mdsvalue('nstxu', pulse=pulse, treename='NBI', TDI=f'\\NBI::CALC_NB_{beamline}_VACCEL').raw()
    keep = voltage >= minVolt_keV
    avg_voltage = np.mean(voltage[keep]) * 1000.0  # Average beam voltage in Volts
    if beam_species == 'D':
        ud = 2.014
    elif beam_species == 'H':
        ud = 1.0
    else:
        raise ValueError('beam_species can only be D or H')
    vbeam = np.sqrt(2.0 * 1.6022e-19 * avg_voltage / (ud * 1.6605e-27))
    printd('Beam voltage:', avg_voltage / 1000.0, ' kV', topic='machine')
    printd('Beam species mass:', ud, ' amu', topic='machine')

    # Geometry for all channels
    for name, norm, usegeo in geometries:
        if usegeo:
            TDIs['geom_' + name] = f'\\MSE::TOP.MSE_CIF.{MSE_revision}.GEOMETRY.{name} * {norm}'
    TDIs['geom_R'] = f'\\MSE::TOP.MSE_CIF.{MSE_revision}.RADIUS'

    # pitch angle measurements
    MDSname, MDSERRname, norm, name, fit = measurements
    TDIs[name] = f'\\MSE::TOP.MSE_CIF.{MSE_revision}.{MDSname} * {norm}'
    TDIs[name + '_error'] = f'\\MSE::TOP.MSE_CIF.{MSE_revision}.{MDSERRname} * {norm}'

    # data fetching
    res = mdsvalue('nstxu', pulse=pulse, treename='MSE', TDI=TDIs).raw()

    # Er correction coefficients (assumes MSE sight lines are in the same Z plane as the beam line (theta =0)
    coef_list = {}
    zero_array = res['geom_ALPHA'] * 0.0
    one_array = zero_array + 1.0
    coef_list['beam_velocity'] = vbeam + zero_array
    coef_list['AA1GAM'] = np.cos(res['geom_ALPHA'] + res['geom_OMEGA'])  # See notes at top on sign convention
    coef_list['AA2GAM'] = np.sin(res['geom_ALPHA'])
    coef_list['AA3GAM'] = np.cos(res['geom_ALPHA'])
    coef_list['AA4GAM'] = zero_array  # Assume theta=0
    coef_list['AA5GAM'] = np.cos(res['geom_OMEGA']) / coef_list['beam_velocity']  # See notes at top on sign convention
    coef_list['AA6GAM'] = -1.0 / coef_list['beam_velocity']  # Assume theta=0
    coef_list['AA7GAM'] = zero_array  # Assume theta=0

    # remap data per individual channel
    MDSname, MDSERRname, norm, name, fit = measurements
    if isinstance(res[name], Exception):
        return
    for ch in range(res[name].shape[1]):  # Loop through subset of good channels with pitch angle data
        valid = res[name + '_error'][:, ch] > 0  # uncertainty greater than zero
        valid &= res[name][:, ch] != 0  # no exact zero values
        valid &= (res[name][:, ch] * np.min(np.abs(res['geom_RADIUS'] - res['geom_R'][ch]))) < 0.001  # radius of measurement as expected

        if False:
            norm = 1.0
        else:
            # Convert actual pitch angle to measured pitch angle
            norm = coef_list['AA1GAM'][ch] / coef_list['AA2GAM'][ch]

        ods[f'mse.channel[{ch}].polarisation_angle.time'] = res['time']
        ods[f'mse.channel[{ch}].polarisation_angle.data'] = res[name][:, ch]
        ods[f'mse.channel[{ch}].polarisation_angle.data_error_upper'] = res[name + '_error'][:, ch]
        ods[f'mse.channel[{ch}].polarisation_angle.validity_timed'] = (valid != 1).astype(int)
        ods[f'mse.channel[{ch}].polarisation_angle.validity'] = int(np.sum(valid) == 0)
        ods[f'mse.channel[{ch}].name'] = f'{ch+1}'

        ods[f'mse.channel[{ch}].active_spatial_resolution[0].centre.r'] = res['geom_R'][ch]
        ods[f'mse.channel[{ch}].active_spatial_resolution[0].centre.z'] = res['geom_R'][ch] * 0.0
        ods[f'mse.channel[{ch}].active_spatial_resolution[0].centre.phi'] = res['geom_R'][ch] * 0.0  # don't actually know this one


# =====================
if __name__ == '__main__':
    test_machine_mapping_functions(__all__, globals(), locals())
