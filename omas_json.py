from __future__ import absolute_import, print_function, division, unicode_literals

from omas_utils import *
from omas import omas, save_omas_pkl, load_omas_pkl

#---------------------------
# save and load OMAS to Json
#---------------------------
def save_omas_json(ods, filename, **kw):
    '''
    Save an OMAS data set to Json

    :param ods: OMAS data set

    :param filename: filename to save to

    :param kw: arguments passed to the json.dumps method
    '''

    printd('Saving OMAS data to Json: %s'%filename, topic=['Json','json'])

    json_string=json.dumps(ods, default=json_dumper, indent=0, separators=(',',': '), **kw)
    open(filename,'w').write(json_string)

def load_omas_json(filename, **kw):
    '''
    Load an OMAS data set from Json

    :param filename: filename to load from

    :param kw: arguments passed to the json.loads mehtod

    :return: OMAS data set
    '''

    printd('Loading OMAS data to Json: %s'%filename, topic='json')

    if isinstance(filename,basestring):
        filename=open(filename,'r')

    def cls():
        tmp=omas()
        tmp.consistency_check=False
        return tmp
    tmp=json.loads(filename.read(),object_pairs_hook=lambda x:json_loader(x,cls), **kw)
    tmp.consistency_check=omas_rcparams['consistency_check']
    return tmp

def test_omas_json(ods):
    '''
    test save and load OMAS Json

    :param ods: ods

    :return: ods
    '''
    filename='test.json'
    save_omas_json(ods,filename)
    ods1=load_omas_json(filename)
    return ods1

#--------------------------------------------
if __name__ == '__main__':
    print('='*20)

    from omas import ods_sample
    os.environ['OMAS_DEBUG_TOPIC']='json'
    ods=ods_sample()

    ods=test_omas_json(ods)
    pprint(ods)
