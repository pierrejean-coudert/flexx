from flexx.util.testing import raises, run_tests_if_main

import os
import tempfile

from flexx.util.config import Config


SAMPLE = """

[testconfig]

foo = yes
bar = 3
spam = 2.3
eggs = bla bla

""" 

def test_defaults():
    c = Config('testconfig',
               eggs=(3, int, 'This is it'),
               spam=((1,2,3), str, 'A list of ints, as a string'))

    assert c.eggs == 3
    assert c.spam == '(1, 2, 3)'
    
    with raises(TypeError):
        Config('testconfig', foo=(None, int, ''))


def test_read_file():
    
    c = Config('testconfig', 
               foo=(False, bool, ''), bar=(1, int, ''), 
               spam=(0.0, float, ''), eggs=('', str, ''))
    
    filename = os.path.join(tempfile.gettempdir(), 'flexx_config_test.cfg')
    with open(filename, 'wb') as f:
        f.write(SAMPLE.encode())
    
    assert c.foo == False
    assert c.bar == 1
    
    c = Config('testconfig', filename,
               foo=(False, bool, ''), bar=(1, int, ''), 
               spam=(0.0, float, ''), eggs=('', str, ''))
    assert c.foo == True
    assert c.bar == 3


run_tests_if_main()
