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


def test_config_name():
    
    # Empty config
    c = Config('aa')
    assert len(c) == 0
    
    with raises(TypeError):
        Config()
    
    with raises(ValueError):
        Config(3)
    
    with raises(ValueError):
        Config('0aa')
    
    with raises(ValueError):
        Config('_aa')
    

def test_defaults():
    
    c = Config('testconfig',
               x01=(3, int, 'an int'),
               x02=(3, float, 'a float'),
               x03=('yes', bool, 'a bool'),
               x04=((1,2,3), str, 'A list of ints, as a string'),
               x05=((1,2,3), (int, ), 'A list of ints, as a tuple'),
               x06=((1,2,3), (str, ), 'A list of strings, as a tuple'),
               )
    
    # Test iteration
    assert len(c) == 6
    for name in c:
        assert name in ('x01', 'x02', 'x03', 'x04', 'x05', 'x06')
    assert set(dir(c)) == set([name for name in c])
    
    # Test values
    assert c.x01 == 3
    assert c.x02 == 3.0
    assert c.x03 == True
    assert c.x04 == '(1, 2, 3)'
    assert c.x05 == (1, 2, 3)
    assert c.x06 == ('1', '2', '3')
    
    # Test docstring (e.g. alphabetic order)
    i1 = c.__doc__.find('x01')
    i2 = c.__doc__.find('x02')
    i3 = c.__doc__.find('x03')
    i4 = c.__doc__.find('x04')
    assert i1 > 0
    assert i2 > i1
    assert i3 > i2
    assert i4 > i3
    assert 'x01 (int): ' in c.__doc__
    assert 'x04 (str): ' in c.__doc__
    assert 'x05 (int-tuple): ' in c.__doc__
    assert 'x06 (str-tuple): ' in c.__doc__


def test_read_file():
    
    # Prepare config file
    filename = os.path.join(tempfile.gettempdir(), 'flexx_config_test.cfg')
    with open(filename, 'wb') as f:
        f.write(SAMPLE.encode())
    
    # Config without sources
    c = Config('testconfig', 
               foo=(False, bool, ''), bar=(1, int, ''), 
               spam=(0.0, float, ''), eggs=('', str, ''))
    assert c.foo == False
    assert c.bar == 1
    
    # Config with filename
    c = Config('testconfig', filename,
               foo=(False, bool, ''), bar=(1, int, ''), 
               spam=(0.0, float, ''), eggs=('', str, ''))
    assert c.foo == True
    assert c.bar == 3

    # Config with string
    c = Config('testconfig', SAMPLE,
               foo=(False, bool, ''), bar=(1, int, ''), 
               spam=(0.0, float, ''), eggs=('', str, ''))
    assert c.foo == True
    assert c.bar == 3
    
    # Config with both, and filenames can be nonexistent
    c = Config('testconfig', SAMPLE, filename, filename+'.cfg',
               foo=(False, bool, ''), bar=(1, int, ''), 
               spam=(0.0, float, ''), eggs=('', str, ''))
    assert c.foo == True
    assert c.bar == 3
    
    # Fails
    with raises(ValueError):
        c = Config('testconfig', [])
    with raises(ValueError):
        c = Config('testconfig', 3)


def test_access():
    
    c = Config('testconfig', foo=(1, int, ''), BAR=(1, int, ''))
    assert len(c) == 2
    
    c.foo = 3
    c.BAR = 4
    c['foo'] == 3
    c['BAR'] == 4
    c['foO'] == 30
    c['BAr'] == 40
    c['FOO'] == 30
    c['bar'] == 40
    with raises(AttributeError):
        c.FOO
    with raises(AttributeError):
        c.bar


def test_stack():
    pass  # todo: test stack


def test_set_from_cmdline():
    pass # todo: ...

    
def test_bool():
    c = Config('testconfig', foo=(True, bool, ''), bar=(False, bool, ''))
    assert c.foo == True
    c.foo = True
    assert c.foo == True
    c.foo = False
    assert c.foo == False
    
    for name in 'yes on true Yes On TRUE 1'.split(' '):
        c.foo = name
        assert c.foo == True
    for name in 'no off fAlse No Off FALSE 0'.split(' '):
        c.foo = name
        assert c.foo == False
    
    for name in 'none ok bla asdasdasd cancel'.split(' '):
        with raises(ValueError):
            c.foo = name

    for val in (1, 2, [2], None, 0, 0.0, 1.0, []):
        with raises(ValueError):
            c.foo = val


def test_int():
    c = Config('testconfig', foo=(1, int, ''), bar=('1', int, ''))
    assert c.foo == 1
    assert c.bar == 1
    
    c.foo = 12.1
    assert c.foo == 12
    c.foo = '7'
    assert c.foo == 7
    c.foo = '-23'
    assert c.foo == -23
    
    for val in ([], None, '1e2', '12.1', 'a'):
        with raises(ValueError):
            c.foo = val


def test_float():
    c = Config('testconfig', foo=(1, float, ''), bar=('1', float, ''))
    assert c.foo == 1.0
    assert c.bar == 1.0
    
    c.foo = 3
    assert c.foo == 3.0
    c.foo = -3.1
    assert c.foo == -3.1
    c.foo = '2e3'
    assert c.foo == 2000.0
    c.foo = '12.12'
    assert c.foo == 12.12
    
    for val in ([], None, 'a', '0a'):
        with raises(ValueError):
            c.foo = val


def test_str():
    c = Config('testconfig', foo=(1, str, ''), bar=((1,2,3), str, ''))
    assert c.foo == '1'
    assert c.bar == '(1, 2, 3)'
    
    c.foo = 3
    assert c.foo == '3'
    c.foo = 3.1
    assert c.foo == '3.1'
    c.foo = 'hello there, you!'
    assert c.foo == 'hello there, you!'
    c.foo = None
    assert c.foo == 'None'
    c.foo = False
    assert c.foo == 'False'
    c.foo = []
    assert c.foo == '[]'


def test_tuple():
    c = Config('testconfig', foo=('1,2', [int], ''), bar=((1,2,3), [str], ''))
    assert c.foo == (1, 2)
    assert c.bar == ('1', '2', '3')
    
    c.foo = 1.2, 3.3, 5
    assert c.foo == (1, 3, 5)
    c.foo = '1,               2,-3,4'
    assert c.foo == (1, 2, -3, 4)
    c.foo = [1, '2']
    assert c.foo == (1, 2)
    
    
    for val in ([[]], [None], ['a'], ['0a'], ['1.2']):
        with raises(ValueError):
            c.foo = val
    
    c.bar = 'hello,  there,     you '
    assert c.bar == ('hello', 'there', 'you')
    c.bar = [1, '2']
    assert c.bar == ('1', '2')


run_tests_if_main()

