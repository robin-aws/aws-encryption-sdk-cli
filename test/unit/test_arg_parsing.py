# Copyright 2017 Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You
# may not use this file except in compliance with the License. A copy of
# the License is located at
#
# http://aws.amazon.com/apache2.0/
#
# or in the "license" file accompanying this file. This file is
# distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF
# ANY KIND, either express or implied. See the License for the specific
# language governing permissions and limitations under the License.
"""Unit testing suite for ``aws_encryption_sdk_cli.internal.arg_parsing``."""
import shlex

import aws_encryption_sdk
from mock import MagicMock, sentinel
import pytest
from pytest_mock import mocker  # noqa pylint: disable=unused-import

import aws_encryption_sdk_cli
from aws_encryption_sdk_cli.exceptions import ParameterParseError
from aws_encryption_sdk_cli.internal import arg_parsing


@pytest.yield_fixture
def patch_build_parser(mocker):
    mocker.patch.object(arg_parsing, '_build_parser')
    yield arg_parsing._build_parser


@pytest.yield_fixture
def patch_process_master_key_provider_configs(mocker):
    mocker.patch.object(arg_parsing, '_process_master_key_provider_configs')
    yield arg_parsing._process_master_key_provider_configs


@pytest.yield_fixture
def patch_parse_and_collapse_config(mocker):
    mocker.patch.object(arg_parsing, '_parse_and_collapse_config')
    yield arg_parsing._parse_and_collapse_config


@pytest.yield_fixture
def patch_process_caching_config(mocker):
    mocker.patch.object(arg_parsing, '_process_caching_config')
    yield arg_parsing._process_caching_config


def test_version_report():
    test = arg_parsing._version_report()
    assert test == 'aws-encryption-sdk-cli/{cli} aws-encryption-sdk/{sdk}'.format(
        cli=aws_encryption_sdk_cli.__version__,
        sdk=aws_encryption_sdk.__version__
    )


@pytest.mark.parametrize('arg_line, line_args', (
    (  # The default converter leaves a space in front of the first argument
       # when called like this. Make sure we do not.
        '-f test1 test2',
        ['-f', 'test1', 'test2']
    ),
    (
        '   test1   test2    ',
        ['test1', 'test2']
    ),
    (
        '-f test1 test2 # in-line comment',
        ['-f', 'test1', 'test2']
    ),
    (
        '# whole-line comment',
        []
    )
))
def test_comment_ignoring_argument_parser_convert_arg_line_to_args(arg_line, line_args):
    parser = arg_parsing.CommentIgnoringArgumentParser()
    parsed_line = [arg for arg in parser.convert_arg_line_to_args(arg_line)]
    assert line_args == parsed_line


def test_unique_store_action_first_call():
    mock_parser = MagicMock()
    mock_namespace = MagicMock(special_attribute=None)
    action = arg_parsing.UniqueStoreAction(
        option_strings=sentinel.option_strings,
        dest='special_attribute'
    )
    action(
        parser=mock_parser,
        namespace=mock_namespace,
        values=sentinel.values,
        option_string='SPECIAL_ATTRIBUTE'
    )
    assert mock_namespace.special_attribute is sentinel.values


def test_unique_store_action_second_call():
    mock_parser = MagicMock()
    mock_namespace = MagicMock(special_attribute=sentinel.attribute)
    action = arg_parsing.UniqueStoreAction(
        option_strings=sentinel.option_strings,
        dest='special_attribute'
    )
    action(
        parser=mock_parser,
        namespace=mock_namespace,
        values=sentinel.values,
        option_string='SPECIAL_ATTRIBUTE'
    )
    assert mock_namespace.special_attribute is sentinel.attribute
    mock_parser.error.assert_called_once_with('SPECIAL_ATTRIBUTE argument may not be specified more than once')


def build_expected_good_args():  # pylint: disable=too-many-locals
    encrypt = '-e'
    decrypt = '-d'
    short_input = ' -i -'
    long_input = ' --input -'
    short_output = ' -o -'
    long_output = ' --output -'
    valid_io = short_input + short_output
    mkp_1 = ' -m provider=ex_provider_1 key=ex_mk_id_1'
    mkp_1_parsed = {'provider': 'ex_provider_1', 'key': ['ex_mk_id_1']}
    mkp_2 = ' -m provider=ex_provider_2 key=ex_mk_id_2'
    mkp_2_parsed = {'provider': 'ex_provider_2', 'key': ['ex_mk_id_2']}
    default_encrypt = encrypt + valid_io + mkp_1
    good_args = []

    # encrypt/decrypt
    for encrypt_flag in (encrypt, '--encrypt'):
        good_args.append((encrypt_flag + valid_io + mkp_1, 'action', 'encrypt'))
    for decrypt_flag in (decrypt, '--decrypt'):
        good_args.append((decrypt_flag + valid_io + mkp_1, 'action', 'decrypt'))

    # master key config
    good_args.append((default_encrypt, 'master_keys', [mkp_1_parsed]))
    good_args.append((default_encrypt + mkp_2, 'master_keys', [mkp_1_parsed, mkp_2_parsed]))

    # input/output
    for input_flag in (short_input, long_input):
        good_args.append((encrypt + input_flag + short_output + mkp_1, 'input', '-'))
    for output_flag in (short_output, long_output):
        good_args.append((encrypt + output_flag + short_input + mkp_1, 'output', '-'))

    # encryption context
    good_args.append((default_encrypt, 'encryption_context', None))
    good_args.append((
        default_encrypt + ' -c some=data not=secret',
        'encryption_context',
        {'some': 'data', 'not': 'secret'}
    ))

    # algorithm
    algorithm_name = 'AES_128_GCM_IV12_TAG16'
    good_args.append((default_encrypt, 'algorithm', None))
    for algorithm_flag in (' -a ', ' --algorithm '):
        good_args.append((default_encrypt + algorithm_flag + algorithm_name, 'algorithm', algorithm_name))

    # frame length
    good_args.append((default_encrypt, 'frame_length', None))
    good_args.append((default_encrypt + ' --frame-length 99', 'frame_length', 99))

    # max length
    good_args.append((default_encrypt, 'max_length', None))
    good_args.append((default_encrypt + ' --max-length 99', 'max_length', 99))

    # recursive
    good_args.append((default_encrypt, 'recursive', False))
    for recursive_flag in (' -r', ' -R', ' --recursive'):
        good_args.append((default_encrypt + recursive_flag, 'recursive', True))

    # logging verbosity
    good_args.append((default_encrypt, 'verbosity', None))
    for count in (1, 2, 3):
        good_args.append((default_encrypt + ' -' + 'v' * count, 'verbosity', count))

    return good_args


@pytest.mark.parametrize('argstring, attribute, value', build_expected_good_args())
def test_parser_from_shell(argstring, attribute, value):
    parsed = arg_parsing.parse_args(shlex.split(argstring))
    assert getattr(parsed, attribute) == value


@pytest.mark.parametrize('argstring, attribute, value', build_expected_good_args())
def test_parser_fromfile(tmpdir_factory, argstring, attribute, value):
    argfile = tmpdir_factory.mktemp('testing').join('argfile')
    argfile.write(argstring)
    parsed = arg_parsing.parse_args(['@{}'.format(argfile)])
    assert getattr(parsed, attribute) == value


def build_bad_io_arguments():
    return [
        '-d -o - -m provider=ex_provider key=ex_mk_id',
        '-d -i - -m provider=ex_provider key=ex_mk_id'
    ]


def build_bad_multiple_arguments():
    prefix = '-d -i - -o -'
    protected_arguments = [
        ' --caching key=value',
        ' --input -',
        ' --output -',
        ' --encryption-context key=value',
        ' --algorithm ALGORITHM',
        ' --frame-length 256',
        ' --max-length 1024'
    ]
    return [
        prefix + arg + arg
        for arg in protected_arguments
    ]


@pytest.mark.parametrize('args', build_bad_io_arguments() + build_bad_multiple_arguments())
def test_parse_args_fail(args):
    with pytest.raises(SystemExit):
        arg_parsing.parse_args(shlex.split(args))


@pytest.mark.parametrize('source, result', (
    (
        ['a=b', 'c=d', 'e=f'],
        {'a': ['b'], 'c': ['d'], 'e': ['f']}
    ),
    (
        ['a=b', 'b=c', 'b=d'],
        {'a': ['b'], 'b': ['c', 'd']}
    )
))
def test_parse_kwargs_good(source, result):
    test = arg_parsing._parse_kwargs(source)

    assert test == result


def test_parse_kwargs_fail():
    with pytest.raises(ParameterParseError) as excinfo:
        arg_parsing._parse_kwargs(['asdfsadf'])

    excinfo.match(r'Argument parameter must follow the format "key=value"')


def test_collapse_config():
    source = {'a': ['b'], 'c': ['d'], 'e': ['f']}
    result = {'a': 'b', 'c': 'd', 'e': 'f'}

    test = arg_parsing._collapse_config(source)

    assert test == result


def test_parse_and_collapse_config():
    source = ['key1=value1', 'key2=value2', 'key3=value3']
    result = {'key1': 'value1', 'key2': 'value2', 'key3': 'value3'}

    test = arg_parsing._parse_and_collapse_config(source)

    assert test == result


def test_process_caching_config():
    source = ['capacity=3', 'max_messages_encrypted=55', 'max_bytes_encrypted=8', 'max_age=32']
    result = {'capacity': 3, 'max_messages_encrypted': 55, 'max_bytes_encrypted': 8, 'max_age': 32.0}

    test = arg_parsing._process_caching_config(source)

    assert test == result


def test_process_caching_config_bad_key():
    source = [
        'capacity=3',
        'max_age=32',
        'asdifhja9woiefhjuaowiefjoawiuehjc9awehf=fjw28304uq20498gfij83w0erifju'
    ]

    with pytest.raises(ParameterParseError) as excinfo:
        arg_parsing._process_caching_config(source)

    excinfo.match(r'Invalid caching configuration key: "asdifhja9woiefhjuaowiefjoawiuehjc9awehf"')


@pytest.mark.parametrize('source', (
    ['max_messages_encrypted=55', 'max_bytes_encrypted=8', 'max_age=32'],  # no caopacity
    ['capacity=3', 'max_messages_encrypted=55', 'max_bytes_encrypted=8']  # no max_age
))
def test_process_caching_config_required_parameters_missing(source):
    with pytest.raises(ParameterParseError) as excinfo:
        arg_parsing._process_caching_config(source)

    excinfo.match(r'If enabling caching, both "capacity" and "max_age" are required')


KEY_PROVIDER_CONFIGS = [
    (
        [['provider=ex_provider', 'key=ex_key']],
        'encrypt',
        [{'provider': 'ex_provider', 'key': ['ex_key']}]
    ),
    (
        [['provider=ex_provider', 'key=ex_key_1', 'key=ex_key_2']],
        'encrypt',
        [{'provider': 'ex_provider', 'key': ['ex_key_1', 'ex_key_2']}]
    ),
    (
        [['provider=ex_provider', 'key=ex_key_1', 'key=ex_key_2', 'a=b', 'asdf=4']],
        'encrypt',
        [{'provider': 'ex_provider', 'key': ['ex_key_1', 'ex_key_2'], 'a': ['b'], 'asdf': ['4']}]
    )
]
ALL_CONFIG = (
    [i[0][0] for i in KEY_PROVIDER_CONFIGS],
    'encrypt',
    [i[-1][0] for i in KEY_PROVIDER_CONFIGS]
)
KEY_PROVIDER_CONFIGS.append(ALL_CONFIG)
KEY_PROVIDER_CONFIGS.append((None, 'decrypt', [{'provider': 'aws-kms', 'key': []}]))
KEY_PROVIDER_CONFIGS.append(([['provider=aws-kms']], 'decrypt', [{'provider': 'aws-kms', 'key': []}]))
KEY_PROVIDER_CONFIGS.append(([['key=ex_key_1']], 'encrypt', [{'provider': 'aws-kms', 'key': ['ex_key_1']}]))


@pytest.mark.parametrize('source, action, result', KEY_PROVIDER_CONFIGS)
def test_process_master_key_provider_configs(source, action, result):
    test = arg_parsing._process_master_key_provider_configs(source, action)

    assert test == result


def test_process_master_key_provider_configs_not_exactly_one_provider():
    with pytest.raises(ParameterParseError) as excinfo:
        arg_parsing._process_master_key_provider_configs(
            [['provider=a', 'provider=b', 'key=ex_key_1', 'key=ex_key_2']],
            'encrypt'
        )

    excinfo.match(r'Exactly one "provider" must be provided for each master key provider configuration. 2 provided')


def test_process_master_key_provider_configs_no_keys():
    source = [['provider=ex_provider', 'aaa=sadfa']]

    with pytest.raises(ParameterParseError) as excinfo:
        arg_parsing._process_master_key_provider_configs(source, 'encrypt')

    excinfo.match(r'At least one "key" must be provided for each master key provider configuration')


def test_parse_args(
        patch_build_parser,
        patch_process_master_key_provider_configs,
        patch_parse_and_collapse_config,
        patch_process_caching_config
):
    mock_parsed_args = MagicMock(
        master_keys=sentinel.raw_keys,
        encryption_context=sentinel.raw_encryption_context,
        caching=sentinel.raw_caching,
        action=sentinel.action,
        version=False
    )
    patch_build_parser.return_value.parse_args.return_value = mock_parsed_args
    test = arg_parsing.parse_args(sentinel.raw_args)

    patch_build_parser.assert_called_once_with()
    patch_build_parser.return_value.parse_args.assert_called_once_with(args=sentinel.raw_args)
    patch_process_master_key_provider_configs.assert_called_once_with(sentinel.raw_keys, sentinel.action)
    assert test.master_keys is patch_process_master_key_provider_configs.return_value
    patch_parse_and_collapse_config.assert_called_once_with(sentinel.raw_encryption_context)
    assert test.encryption_context is patch_parse_and_collapse_config.return_value
    patch_process_caching_config.assert_called_once_with(sentinel.raw_caching)
    assert test.caching is patch_process_caching_config.return_value
    assert test is mock_parsed_args


def test_parse_args_no_encryption_context(
        patch_build_parser,
        patch_process_master_key_provider_configs,
        patch_parse_and_collapse_config,
        patch_process_caching_config
):
    patch_build_parser.return_value.parse_args.return_value = MagicMock(encryption_context=None)
    test = arg_parsing.parse_args()

    assert not patch_parse_and_collapse_config.called
    assert test.encryption_context is None


def test_parse_args_no_caching_config(
        patch_build_parser,
        patch_process_master_key_provider_configs,
        patch_parse_and_collapse_config,
        patch_process_caching_config
):
    patch_build_parser.return_value.parse_args.return_value = MagicMock(caching=None)
    test = arg_parsing.parse_args()

    assert not patch_process_caching_config.called
    assert test.caching is None


def test_parse_args_error_raised_in_post_processing(
        patch_build_parser,
        patch_process_master_key_provider_configs,
        patch_parse_and_collapse_config,
        patch_process_caching_config
):
    patch_build_parser.return_value.parse_args.return_value = MagicMock(version=False)
    patch_process_caching_config.side_effect = ParameterParseError

    arg_parsing.parse_args()

    patch_build_parser.return_value.error.assert_called_once_with()