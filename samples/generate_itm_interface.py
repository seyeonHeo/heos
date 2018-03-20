import os
import re

file_in = os.path.abspath(os.sep.join([os.path.split(__file__)[0], '..', 'omas', 'omas_imas.py']))
file_out = os.path.abspath(os.sep.join([os.path.split(__file__)[0], '..', 'omas', 'omas_itm.py']))

print('Reading   : ' + file_in)

# generate ITM interface from IMAS interface
orig = open(file_in, 'r').read()
mod = re.sub('IMAS', 'ITM', orig)
mod = re.sub('imas', 'itm', mod)
mod = re.sub('IDS', 'CPO', mod)
mod = re.sub('ids', 'cpo', mod)
mod = re.sub('import itm', 'import ual', mod)
mod = re.sub('cpo = itm\.cpo\(\)', 'cpo = ual.itm()', mod)

mod = re.sub('\ndef', '\n\n# AUTOMATICALLY GENERATED FILE - DO NOT EDIT\n\ndef', mod)

with open(file_out, 'w') as f:
    f.write('# THIS FILE IS GENERATED BY TRANSLATING the `omas_imas.py` SCRIPT\n')
    f.write('# DO NOT EDIT THIS FILE BECAUSE IT WILL BE OVERWRITTEN\n\n\n')
    f.write(mod)

print('Generated : ' + file_out)
