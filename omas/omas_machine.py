# https://confluence.iter.org/display/IMP/UDA+data+mapping+tutorial

import subprocess
import shutil
from .omas_utils import *
from .omas_core import ODS, dynamic_ODS, omas_environment, omas_info_node, imas_json_dir, omas_rcparams
from .omas_physics import cocos_signals

__all__ = [
    'machine_expression_types',
    'machines',
    'machine_mappings',
    'load_omas_machine',
    'machine_mapping_function',
    'test_machine_mapping_functions',
    'mdstree',
    'mdsvalue',
]

url_dir = os.sep.join([omas_rcparams['tmp_omas_dir'], 'machine_mappings', '{branch}', 'omas_machine_mappings_url_{branch}'])

_python_tdi_namespace = {}


def python_tdi_namespace(branch):
    '''
    Returns the namespace of the python_tdi.py file

    :param branch: remote branch to load

    :return: namespace
    '''
    # return cached python tdi function namespace
    if branch in _python_tdi_namespace:
        return _python_tdi_namespace[branch]
    _python_tdi_namespace[branch] = {}

    # get local mapping functions
    if not branch:
        exec('from omas.machine_mappings.python_tdi import *', _python_tdi_namespace[branch])

    # get mapping functions from GitHub
    else:
        printd(f'omas python tdi mappings from branch: `{branch}`', topic='machine')

        # make sure remote branch is transfered
        machines(None, branch)

        # import from temporary directory
        dir = url_dir.format(branch=branch)
        if dir + os.sep + '..' not in sys.path:
            sys.path.insert(0, dir + os.sep + '..')

        exec(f'from omas_machine_mappings_url_{branch}.python_tdi import *', _python_tdi_namespace[branch])

    return _python_tdi_namespace[branch]


def update_mapping(machine, location, value, cocosio=None, default_options=None, update_path=False):
    '''
    Utility function that updates the local mapping file of a given machine with the mapping info of a given location

    :param machine: machine name

    :param location: ODS location to be updated

    :param value: dictionary with mapping info

    :param cocosio: if integer and location has COCOS transform it adds it

    :param update_path: use the same value for the arrays of structures leading to this location

    :return: dictionary with updated raw mappings
    '''
    ulocation = l2u(p2l(location))
    if cocosio and ulocation in cocos_signals and cocos_signals[ulocation] is not None:
        assert isinstance(cocosio, int)
        value['COCOSIO'] = cocosio

    # operate on the raw mappings
    new_raw_mappings = machine_mappings(machine, None, None, return_raw_mappings=True)

    # assign default options
    updated_defaults = False
    if default_options:
        for item in default_options:
            if item not in new_raw_mappings['__options__'] and item not in ['machine', 'pulse', 'location']:
                new_raw_mappings['__options__'][item] = default_options[item]
                updated_defaults = True

    # if the definition is the same do not do anythinig
    if not updated_defaults and ulocation in new_raw_mappings and repr(value) == repr(new_raw_mappings[ulocation]):
        return new_raw_mappings

    # add definition for new/updated location and update the .json file
    new_raw_mappings[ulocation] = value
    filename = machines(machine, '')
    with open(filename, 'w') as f:
        json.dump(new_raw_mappings, f, indent=1, separators=(',', ': '), sort_keys=True)
    print(f"Updated {machine} mapping for {ulocation}")

    # add the same call for arrays of structures going upstream
    if update_path:
        for uloc in [':'.join(ulocation.split(':')[: k + 1]) + ':' for k, l in enumerate(ulocation.split(':')[:-1])]:
            if uloc in new_raw_mappings:
                continue
            if 'COCOSIO' in value:
                value = copy.copy(value)
                del value['COCOSIO']
            update_mapping(machine, uloc, value, None, None, update_path=False)

    return new_raw_mappings


def mds_machine_to_server_mapping(server, treename):
    '''
    Resolve MDS+ server

    :param machine: machine name

    :param treename: treename (in case treename affects server to be used)

    :return: string with MDS+ server and port to be used
    '''
    return server.format(**os.environ)


_mds_connection_cache = {}


class mdstree(dict):
    '''
    Class to handle the structure of an MDS+ tree.
    Nodes in this tree are mdsvalue objects
    '''

    def __init__(self, server, treename, pulse):
        for TDI in sorted(mdsvalue(server, treename, pulse, rf'getnci("***","FULLPATH")').raw())[::-1]:
            TDI = TDI.decode('utf8').strip()
            path = TDI.replace('::TOP', '').lstrip('\\').replace(':', '.').split('.')
            h = self
            for p in path[1:-1]:
                h = h.setdefault(p, mdsvalue(server, treename, pulse, ''))
            if path[-1] not in h:
                h[path[-1]] = mdsvalue(server, treename, pulse, TDI)
            else:
                h[path[-1]].TDI = TDI


class mdsvalue(dict):
    '''
    Execute MDS+ TDI functions
    '''

    def __init__(self, server, treename, pulse, TDI):
        self.treename = treename
        self.pulse = pulse
        self.TDI = TDI
        try:
            # handle the case that server is just the machine name
            server = machine_mappings(server, None)['__mdsserver__']
        except NotImplementedError:
            if '.' not in server:
                raise
        self.server = mds_machine_to_server_mapping(server, self.treename)

    def data(self):
        return self.raw(f'data({self.TDI})')

    def dim_of(self, dim):
        return self.raw(f'dim_of({self.TDI},{dim})')

    def units(self):
        return self.raw(f'units({self.TDI})')

    def error(self):
        return self.raw(f'error({self.TDI})')

    def error_dim_of(self, dim):
        return self.raw(f'error_dim_of({self.TDI},{dim})')

    def units_dim_of(self, dim):
        return self.raw(f'units_dim_of({self.TDI},{dim})')

    def size(self, dim):
        return self.raw(f'size({self.TDI})')

    def raw(self, TDI=None):
        '''
        Fetch data from MDS+ with connection caching

        :param TDI: string
            MDS+ TDI expression (overrides the one passed when the object was instantiated)

        :return: result of TDI expression
        '''
        import MDSplus

        if TDI is None:
            TDI = self.TDI

        try:
            for fallback in [0, 1]:
                if (self.server, self.treename, self.pulse) not in _mds_connection_cache:
                    conn = MDSplus.Connection(self.server)
                    if self.treename is not None:
                        conn.openTree(self.treename, self.pulse)
                    _mds_connection_cache[(self.server, self.treename, self.pulse)] = conn
                try:
                    conn = _mds_connection_cache[(self.server, self.treename, self.pulse)]
                    break
                except Exception as _excp:
                    if (self.server, self.treename, self.pulse) in _mds_connection_cache:
                        del _mds_connection_cache[(self.server, self.treename, self.pulse)]
                    if fallback:
                        raise

            return MDSplus.Data.data(conn.get(TDI))
        except Exception as _excp:
            txt = []
            for item in ['server', 'treename', 'pulse']:
                txt += [f' - {item}: {getattr(self, item)}']
            txt += [f' - TDI: {TDI}']
            raise _excp.__class__(str(_excp) + '\n' + '\n'.join(txt))


machine_expression_types = ['VALUE', 'ENVIRON', 'PYTHON', 'TDI', 'eval2TDI']


def machine_to_omas(ods, machine, pulse, location, options={}, branch='', user_machine_mappings=None, cache=None):
    '''
    Routine to convert machine data to ODS

    :param ods: input ODS to populate

    :param machine: machine name

    :param pulse: pulse number

    :param location: ODS location to be populated

    :param options: dictionary with options to use when loadinig the data

    :param branch: load machine mappings and mapping functions from a specific GitHub branch

    :param user_mappings: allow specification of external mappings

    :param cache: if cache is a dictionary, this will be used to establiish a cash

    :return: updated ODS and data before being assigned to the ODS
    '''
    if user_machine_mappings is None:
        user_machine_mappings = {}

    location = l2o(p2l(location))

    for branch in [branch, 'master']:
        mappings = machine_mappings(machine, branch, user_machine_mappings)
        options_with_defaults = copy.copy(mappings['__options__'])
        options_with_defaults.update(options)
        options_with_defaults.update({'machine': machine, 'pulse': pulse, 'location': location})
        try:
            mapped = mappings[location]
        except KeyError:
            if branch == 'master':
                raise
    idm = (machine, branch)

    # cocosio
    cocosio = None
    if mapped.get('COCOSIO', False):
        if isinstance(mapped['COCOSIO'], int):
            cocosio = mapped['COCOSIO']

    # CONSTANT VALUE
    if 'VALUE' in mapped:
        data0 = data = mapped['VALUE']
        if isinstance(data0, str):
            data0 = data = data0.format(**options_with_defaults)

    # ENVIRONMENTAL VARIABLE
    elif 'ENVIRON' in mapped:
        data0 = data = os.environ[mapped['ENVIRON'].format(**options_with_defaults)]

    # PYTHON
    elif 'PYTHON' in mapped:
        call = mapped['PYTHON'].format(**options_with_defaults)
        # python functions tend to set multiple locations at once
        # it is thus very beneficial to cache that
        if cache and call in cache:
            ods = cache[call]
        else:
            namespace = {}
            namespace.update(_namespace_mappings[idm])
            namespace['ods'] = ODS()
            namespace['__file__'] = machines(machine, branch)[:-5] + '.py'
            tmp = compile(call, machines(machine, branch)[:-5] + '.py', 'exec')
            exec(tmp, namespace)
            ods = namespace[mapped.get('RETURN', 'ods')]
            if isinstance(cache, dict):
                cache[call] = ods
        if location.endswith(':'):
            return (
                int(len(ods[u2n(location[:-2], [0] * 100)])),
                {'raw_data': ods, 'processed_data': ods, 'cocosio': cocosio, 'branch': mappings['__branch__']},
            )
        else:
            return ods, {'raw_data': ods, 'processed_data': ods, 'cocosio': cocosio, 'branch': mappings['__branch__']}

    # MDS+
    elif 'TDI' in mapped:
        try:
            TDI = mapped['TDI'].format(**options_with_defaults)
            treename = mapped['treename'].format(**options_with_defaults) if 'treename' in mapped else None
            data0 = data = mdsvalue(machine, treename, pulse, TDI).raw()
            if data is None:
                raise ValueError('data is None')
        except Exception:
            printe(mapped['TDI'].format(**options_with_defaults).replace('\\n', '\n'))
            raise

    else:
        raise ValueError(f"Could not fetch data for {location}. Must define one of {machine_expression_types}")

    # handle size definition for array of structures
    if location.endswith(':'):
        return int(data), {'raw_data': data0, 'processed_data': data, 'cocosio': cocosio, 'branch': mappings['__branch__']}

    # transpose manipulation
    if mapped.get('TRANSPOSE', False):
        data = numpy.transpose(data, mapped['TRANSPOSE'])

    # transpose filter
    nanfilter = lambda x: x
    if mapped.get('NANFILTER', False):
        nanfilter = lambda x: x[~numpy.isnan(x)]

    # cocosio
    if cocosio is None and mapped.get('COCOSIO', False):
        if 'TDI' in mapped:
            TDI = mapped['COCOSIO'].format(**options_with_defaults)
            cocosio = int(mdsvalue(machine, treename, pulse, TDI).raw())
        else:
            raise ValueError('COCOSIO should be an integer or a TDI expression')

    # assign data to ODS
    if not hasattr(data, 'shape'):
        ods[location] = data
    else:
        with omas_environment(ods, cocosio=cocosio):
            csize = mapped.get('COORDINATES', [])
            osize = len([c for c in mapped.get('COORDINATES', []) if c != '1...N'])
            dsize = len(data.shape)
            if dsize - osize == 0 or ':' not in location:
                if data.size == 1:
                    data = data.item()
                ods[location] = nanfilter(data)
            else:
                for k in range(data.shape[0]):
                    ods[u2n(location, [k] + [0] * 10)] = nanfilter(data[k, ...])

    return ods, {'raw_data': data0, 'processed_data': data, 'cocosio': cocosio, 'branch': mappings['__branch__']}


def machine_mapping_function(__all__):
    """
    Decorator for identifying mapping functions
    """

    def machine_mapping_decorator(f, __all__):
        __all__.append(f.__name__)

        def machine_mapping_caller(*args, **kwargs):
            if omas_git_repo:
                import inspect

                # figure out the machine name from where the function `f` is defined
                machine = os.path.splitext(os.path.split(inspect.getfile(f))[1])[0]
                if (
                    machine == '<string>'
                ):  # if `f` is called via exec then we need to look at the call stack to figure out the macchine name
                    machine = os.path.splitext(os.path.split(inspect.getframeinfo(inspect.currentframe().f_back)[0])[1])[0]

                # call signature
                argspec = inspect.getfullargspec(f)
                f_args_str = ", ".join('{%s}' % item for item in argspec.args)
                call = f"{f.__qualname__}({f_args_str})".replace('{ods}', 'ods')
                default_options = None
                if argspec.defaults:
                    default_options = dict(zip(argspec.args[::-1], argspec.defaults[::-1]))

            # call
            out = f(*args, **kwargs)

            # update mappings definitions
            if omas_git_repo:
                for ulocation in numpy.unique(list(map(o2u, args[0].flat().keys()))):
                    update_mapping(machine, ulocation, {'PYTHON': call}, 11, default_options, update_path=True)

            return out

        return machine_mapping_caller

    return lambda x: machine_mapping_decorator(x, __all__)


def test_machine_mapping_functions(__all__, global_namespace, local_namespace):
    '''
    Function used to test python mapping functions

    :param __all__: list of functionss to test

    :param namespace: testing namespace
    '''
    from pprint import pprint

    for func in __all__:
        print('=' * len(func))
        print(func)
        print('=' * len(func))
        ods = ODS()
        func = eval(func, global_namespace, local_namespace)
        try:
            try:
                func(ods)
            except Exception:
                raise
        except TypeError as _excp:
            if re.match('.*missing [0-9]+ required positional argument.*', str(_excp)):
                raise _excp.__class__(
                    str(_excp)
                    + '\n'
                    + 'For testing purposes, make sure to provide default valuess to all arguments of the machine mapping functions'
                )
            else:
                raise
        pprint(numpy.unique(list(map(o2u, ods.flat().keys()))).tolist())


def load_omas_machine(
    machine,
    pulse,
    options={},
    consistency_check=True,
    imas_version=omas_rcparams['default_imas_version'],
    cls=ODS,
    branch='',
    user_machine_mappings=None,
):
    printd('Loading from %s' % machine, topic='machine')
    ods = cls(imas_version=imas_version, consistency_check=consistency_check)
    for location in [location for location in machine_mappings(machine, branch, user_machine_mappings) if not location.startswith('__')]:
        if location.endswith(':'):
            continue
        print(location)
        machine_to_omas(ods, machine, pulse, location, options, branch)
    return ods


class dynamic_omas_machine(dynamic_ODS):
    """
    Class that provides dynamic data loading from machine mappings
    This class is not to be used by itself, but via the ODS.open() method.
    """

    def __init__(self, machine, pulse, options={}, branch='', user_machine_mappings=None, verbose=True):
        self.kw = {'machine': machine, 'pulse': pulse, 'options': options, 'branch': branch, 'user_machine_mappings': user_machine_mappings}
        self.active = False
        self.cache = {}

    def open(self):
        printd('Dynamic open  %s' % self.kw, topic='dynamic')
        self.active = True
        return self

    def close(self):
        printd('Dynamic close %s' % self.kw, topic='dynamic')
        self.active = False
        self.cache.clear()
        return self

    def __getitem__(self, key):
        if not self.active:
            raise RuntimeError('Dynamic link broken: %s' % self.kw)
        if o2u(key) not in self.cache:
            printd('Dynamic read  %s: %s' % (self.kw, key), topic='dynamic')
            ods, _ = machine_to_omas(
                ODS(),
                self.kw['machine'],
                self.kw['pulse'],
                o2u(key),
                self.kw['options'],
                self.kw['branch'],
                self.kw['user_machine_mappings'],
                self.cache,
            )
            self.cache[o2u(key)] = ods
        if isinstance(self.cache[o2u(key)], int):
            return self.cache[o2u(key)]
        else:
            return self.cache[o2u(key)][key]

    def __contains__(self, location):
        ulocation = o2u(location)
        if not self.active:
            raise RuntimeError('Dynamic link broken: %s' % self.kw)
        if ulocation.endswith(':'):
            return False
        return ulocation in machine_mappings(self.kw['machine'], self.kw['branch'], self.kw['user_machine_mappings'])

    def keys(self, location):
        ulocation = o2u(location)
        if ulocation + '.:' in machine_mappings(self.kw['machine'], self.kw['branch'], self.kw['user_machine_mappings']):
            return list(range(self[ulocation + '.:']))
        else:
            return numpy.unique(
                [
                    convert_int(k[len(ulocation) :].lstrip('.').split('.')[0])
                    for k in machine_mappings(self.kw['machine'], self.kw['branch'], self.kw['user_machine_mappings'])
                    if k.startswith(ulocation)
                ]
            )


_machines_dict = {}


def machines(machine=None, branch=''):
    '''
    Function to get machines that have their mappings defined
    This function takes care of remote transfer the needed files (both .json and .py) if a remote branch is requested

    :param machine: string with machine name or None

    :param branch: GitHub branch from which to load the machine mapping information

    :return: if `machine==None` returns dictionary with list of machines and their json mapping files
             if `machine` is a string, then returns json mapping filename and branch
    '''

    # return cached results
    if branch in _machines_dict:
        if machine is None:
            return _machines_dict[branch]
        elif machine in _machines_dict:
            return _machines_dict[branch][machine]

    # local mappings
    if not branch:
        dir = imas_json_dir + '/../machine_mappings'

    # remote mappings from GitHub
    else:
        if branch == 'master':
            svn_branch = 'trunk'
        else:
            svn_branch = 'branches/' + branch

        dir = url_dir.format(branch=branch)
        if os.path.exists(dir):
            shutil.rmtree(dir)
        subprocess.Popen(
            f'''
svn export --force https://github.com/gafusion/omas.git/{svn_branch}/omas/machine_mappings/ {dir}
''',
            stdout=subprocess.PIPE,
            shell=True,
        ).communicate()[0]

    # go through machine files
    _machines_dict[branch] = {}
    for filename in glob.glob(f'{dir}/*.json'):
        _machines_dict[branch][os.path.splitext(os.path.split(filename)[1])[0]] = os.path.abspath(filename)

    # return list of supported machines
    if machine is None:
        return _machines_dict[branch]
    # return filename with mappings for this machine
    else:
        if machine not in _machines_dict[branch]:
            raise NotImplementedError(f'Machine `{machine}` has no mapping defined')
        return _machines_dict[branch][machine]


_machine_mappings = {}
_namespace_mappings = {}
_user_machine_mappings = {}


def machine_mappings(machine, branch, user_machine_mappings=None, return_raw_mappings=False):
    '''
    Function to load the json mapping files (local or remote)
    Allows for merging external mapping rules defined by users.
    This function sanity-checks and the mapping file and adds extra info required for mapping

    :param machine: machine for which to load the mapping files

    :param branch: GitHub branch from which to load the machine mapping information

    :return: dictionary with mapping transformations
    '''
    if user_machine_mappings is None:
        user_machine_mappings = {}

    idm = (machine, branch)

    if (
        return_raw_mappings
        or machine not in _machine_mappings
        or list(_user_machine_mappings.keys()) + list(user_machine_mappings.keys()) != _machine_mappings[idm]['__user_machine_mappings__']
    ):

        # figure out mapping file
        filename = machines(machine, branch)

        # load mappings from file
        with open(filename, 'r') as f:
            mappings = json.load(f)
        for item in ['__cocos_rules__', '__options__']:
            mappings.setdefault(item, {})

        # merge mappings and user_machine_mappings
        mappings['__user_machine_mappings__'] = []
        for umap in [_user_machine_mappings, user_machine_mappings]:
            umap = copy.copy(umap)
            mappings['__user_machine_mappings__'].extend(list(umap.keys()))
            for item in ['__cocos_rules__', '__options__']:
                mappings[item].update(umap.pop(item, {}))
            mappings.update(umap)

        # return raw json mappings if so requested
        if return_raw_mappings:
            mappings.pop('__user_machine_mappings__')
            return mappings

        mappings['__filename__'] = filename
        mappings['__branch__'] = branch

        # read the machine specific python mapping functions
        _namespace_mappings[idm] = {}
        if os.path.exists(os.path.splitext(filename)[0] + '.py'):
            with open(os.path.splitext(filename)[0] + '.py', 'r') as f:
                exec(f.read(), _namespace_mappings[idm])

        # generate TDI for cocos_rules
        for item in mappings['__cocos_rules__']:
            if 'eval2TDI' in mappings['__cocos_rules__'][item]:
                try:
                    mappings['__cocos_rules__'][item]['TDI'] = eval(
                        mappings['__cocos_rules__'][item]['eval2TDI'].replace('\\', '\\\\'), python_tdi_namespace(branch)
                    )
                except:
                    print(mappings['__cocos_rules__'][item]['eval2TDI'])

        # generate TDI and sanity check mappings
        for location in mappings:
            # sanity check format
            if l2o(p2l(location)) != location:
                raise ValueError(f'{location} mapping should be specified as {l2o(p2l(location))}')

            # generate DTI functions based on eval2DTI
            if 'eval2TDI' in mappings[location]:
                mappings[location]['TDI'] = eval(mappings[location]['eval2TDI'].replace('\\', '\\\\'), python_tdi_namespace(branch))

            # make sure required coordinates info are present in the mapping
            info = omas_info_node(location)
            if 'coordinates' in info:
                mappings[location]['COORDINATES'] = list(map(i2o, info['coordinates']))
                for coordinate in mappings[location]['COORDINATES']:
                    if coordinate == '1...N':
                        continue
                    elif coordinate not in mappings:
                        raise ValueError(f'missing coordinate {coordinate} for {location}')

            # add cocos transformation info
            has_COCOS = o2u(location) in cocos_signals and cocos_signals[o2u(location)] is not None
            if 'COCOSIO' not in mappings[location] and has_COCOS:
                cocos_defined = False
                for cocos_rule in mappings['__cocos_rules__']:
                    if 'TDI' in mappings[location] and re.findall(cocos_rule, mappings[location]['TDI']):
                        mappings[location]['COCOSIO'] = mappings['__cocos_rules__'][cocos_rule]['TDI']
                        cocos_defined = True
                        break
                if not cocos_defined:
                    raise ValueError(f'{location} must have COCOS specified')
            if 'COCOSIO' in mappings[location] and not has_COCOS:
                raise ValueError(f'{location} should not have COCOS specified, or COCOS definition should be added to omas_cocos file')

        # cache
        _machine_mappings[idm] = mappings

    return _machine_mappings[idm]
