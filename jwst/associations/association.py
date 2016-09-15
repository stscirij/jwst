from ast import literal_eval
from collections import namedtuple, MutableMapping
from copy import deepcopy
from datetime import datetime
from itertools import count
import json
import jsonschema
import logging
from nose.tools import nottest
import re

from astropy.extern import six
from numpy.ma import masked

from .exceptions import (AssociationError, AssociationProcessMembers)
from .registry import AssociationRegistry

__all__ = [
    'Association',
    'getattr_from_list',
    'SERIALIZATION_PROTOCOLS',
    'validate',
]


# Configure logging
logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())

# Timestamp template
_TIMESTAMP_TEMPLATE = '%Y%m%dT%H%M%S'


class Association(MutableMapping):
    """An Association

    Parameters
    ----------
    member: dict
        The member to initialize the association with.

    timestamp: str
        Timestamp to use in the name of this association. Should conform
        to the datetime.strftime format '%Y%m%dT%M%H%S'. If None, class
        instantiation will create this string using current time.

    Raises
    ------
    AssociationError
        If a member doesn't match any of the registered associations.

    Attributes
    ----------
    instance: dict-like
        The instance is the association data structure.
        See `data` below

    meta: dict
        Information about the association.

    data: dict
        The association. The format of this data structure
        is determined by the individual assocations and, if
        defined, valided against their specified schema.

    schema_file: str
        The name of the output schema that an association
        must adhere to.

    registry: AssocitionRegistry
        The registry this association came from.
    """

    # Assume no registry
    registry = None

    # Default force a constraint to use first value.
    DEFAULT_FORCE_UNIQUE = False

    # Default require that the constraint exists or otherwise
    # can be explicitly checked.
    DEFAULT_REQUIRE_CONSTRAINT = True

    # Global constraints
    GLOBAL_CONSTRAINTS = {}

    # Associations of the same type are sequenced.
    _sequence = count(1)

    def __init__(
            self,
            member=None,
            timestamp=None,
    ):

        self.data = dict()
        self.add_constraints(deepcopy(self.GLOBAL_CONSTRAINTS))
        self.run_init_hook = True
        self.meta = {}

        if timestamp is not None:
            self.timestamp = timestamp
        else:
            self.timestamp = make_timestamp()

        self.data.update({
            'asn_type': 'None',
            'asn_rule': self.asn_rule,
            'creation_time': self.timestamp
        })

        if member is not None:
            self.add(member)
        self.sequence = next(self._sequence)

    @property
    def asn_name(self):
        return 'unamed_association'

    @classmethod
    def _asn_rule(cls):
        return cls.__name__

    @property
    def asn_rule(self):
        return self._asn_rule()

    def dump(self, protocol='json'):
        """Serialize the association

        Parameters
        ----------
        protocol: ('json',)
            The format to use for serialization.

        Returns
        -------
        (name, serialized):
            Tuple where the first item is the suggested
            base name for the file.
            Second item is the serialization.
        """
        return SERIALIZATION_PROTOCOLS[protocol].serialize(self)

    @classmethod
    def load(cls, serialized):
        """Marshall a previously serialized association

        Parameters
        ----------
        serialized: object
            The serialized form of the association.

        Returns
        -------
        The Association object
        """
        asn = None
        for protocol in SERIALIZATION_PROTOCOLS:
            try:
                asn = SERIALIZATION_PROTOCOLS[protocol].unserialize(serialized)
                break
            except AssociationError:
                continue
        else:
            raise AssociationError(
                'Cannot translate "{}" to an association'.format(serialized)
            )

        return asn

    def to_json(self):
        """Create JSON representation.

        Returns
        -------
        (name, str):
            Tuple where the first item is the suggested
            base name for the JSON file.
            Second item is the string containing the JSON serialization.
        """

        # Validate
        with open(self.schema_file, 'r') as schema_file:
            asn_schema = json.load(schema_file)
        jsonschema.validate(self.data, asn_schema)

        return (
            self.asn_name,
            json.dumps(self.data, indent=4, separators=(',', ': '))
        )

    @classmethod
    def from_json(cls, serialized):
        """Unserialize an assocation from JSON

        Parameters
        ----------
        serialized: str or file object
            The JSON to read

        Returns
        -------
        association: dict
            The association
        """
        try:
            asn = json.loads(serialized)
        except TypeError:
            try:
                asn = json.load(serialized)
            except (AttributeError, IOError):
                raise AssociationError(
                    'Containter is not JSON: "{}"'.format(serialized)
                )

        return asn

    def add(self, member, check_constraints=True):
        """Add the member to the association

        Parameters
        ----------
        member: dict
            The member to add.

        check_constraints: bool
            If True, see if the member should belong to this association.
            If False, just add it.

        """
        if check_constraints:
            self.test_and_set_constraints(member)

        if self.run_init_hook:
            self._init_hook(member)
        self._add(member)
        self.run_init_hook = False

    @nottest
    def test_and_set_constraints(self, member):
        """Test whether the given dictionaries match parameters for
        for this association

        Parameters
        ----------
        member: dict
            The parameters to check/set for this association.
            This can be a list of dictionaries.

        Raises
        ------
        AssociationError
            If a match fails.

        Notes
        -----
        If a constraint is present, but does not have a value,
        that constraint is set, and, by definition, matches.
        """
        for constraint, conditions in self.constraints.items():
            logger.debug('Constraint="{}" Conditions="{}"'.format(constraint, conditions))
            try:
                input, value = getattr_from_list(member, conditions['inputs'])
            except KeyError:
                if conditions.get('required', self.DEFAULT_REQUIRE_CONSTRAINT):
                    raise AssociationError(
                        'Constraint {} not present in member.'.format(constraint)
                    )
                else:
                    conditions['value'] = 'Constraint not present and ignored'
                    continue

            # If the value is a list, signal that a reprocess
            # needs to be done.
            logger.debug('To check: Input="{}" Value="{}"'.format(input, value))
            evaled = evaluate(value)

            if is_iterable(evaled):
                process_members = []
                for avalue in evaled:
                    new_member = deepcopy(member)
                    new_member[input] = str(avalue)
                    process_members.append(new_member)
                raise AssociationProcessMembers(
                    process_members,
                    [type(self)]
                )

            evaled_str = str(evaled)
            if conditions['value'] is not None:
                if not meets_conditions(
                        evaled_str, conditions['value']
                ):
                    raise AssociationError(
                        'Constraint {} does not match association.'.format(constraint)
                    )

            # Fix the conditions.
            logger.debug('Success Input="{}" Value="{}"'.format(input, evaled_str))
            if conditions['value'] is None or \
               conditions.get('force_unique', self.DEFAULT_FORCE_UNIQUE):
                conditions['value'] = re.escape(evaled_str)
                conditions['inputs'] = [input]
                conditions['force_unique'] = False

    def add_constraints(self, new_constraints):
        """Add a set of constraints to the current constraints."""

        try:
            constraints = self.constraints
        except AttributeError:
            constraints = {}
            self.constraints = constraints
        for constraint, value in six.iteritems(new_constraints):
            constraints[constraint] = constraints.get(constraint, value)

    def constraints_to_text(self):
        yield 'Constraints:'
        for c, p in self.constraints.items():
            yield '    {:s}: {}'.format(c, p['value'])

    @classmethod
    def reset_sequence(cls):
        cls._sequence = count(1)

    def _init_hook(self, member):
        """Post-check and pre-member-adding initialization."""
        pass

    def _add(self, member):
        """Add a member, association-specific"""
        raise NotImplementedError(
            'Association._add must be implemented by a specific assocation rule.'
        )

    def __getitem__(self, key):
        return self.data[self.__keytransform__(key)]

    def __setitem__(self, key, value):
        self.data[self.__keytransform__(key)] = value

    def __delitem__(self, key):
        del self.data[self.__keytransform__(key)]

    def __iter__(self):
        return iter(self.data)

    def __len__(self):
        return len(self.data)

    def __keytransform__(self, key):
        return key


# User module level functions
def validate(
        association,
        definition_files=None,
        include_default=True,
        global_constraints=None
):
    """Validate an association against know schema

    Parameters
    ----------
    association: dict-like
        The association to validate

    definition_files: [str,]
        The files to find the association definitions in.

    include_default: bool
        True to include the default definitions.

    global_constraints: dict
        Constraints to be added to each rule.

    Returns
    -------
    schemas: list
        List of schemas which validated

    Raises
    ------
    AssociationNotValidError
        Association did not validate
    """
    rules = AssociationRegistry(
        definition_files=definition_files,
        include_default=include_default,
        global_constraints=global_constraints
    )
    return rules.validate(association)


# Utilities
def meets_conditions(value, conditions):
    """Check whether value meets any of the provided conditions

    Parameters
    ----------
    values: str
        The value to be check with.

    condition: regex,
        Regular expressions to match against.

    Returns
    -------
    True if any condition is meant.
    """

    if not is_iterable(conditions):
        conditions = [conditions]
    for condition in conditions:
        condition = ''.join([
            '^',
            condition,
            '$'
        ])
        match = re.match(condition, value, flags=re.IGNORECASE)
        if match:
            return True
    return False


def make_timestamp():
    timestamp = datetime.utcnow().strftime(
        _TIMESTAMP_TEMPLATE
    )
    return timestamp


def getattr_from_list(adict, attributes):
    """Retrieve value from dict using a list of attributes

    Parameters
    ----------
    adict: dict
        dict to retrieve from

    attributes: list
        List of attributes

    Returns
    -------
    (attribute, value)
        Returns the value and the attribute from
        which the value was taken.

    Raises
    ------
    KeyError
        None of the attributes are found in the dict.
    """
    for attribute in attributes:
        try:
            result = adict[attribute]
            if result is masked:
                raise KeyError
            return attribute, result
        except KeyError:
            continue
    else:
        raise KeyError


# Available serialization protocols
ProtocolFuncs = namedtuple('ProtocolFuncs', ['serialize', 'unserialize'])
SERIALIZATION_PROTOCOLS = {
    'json': ProtocolFuncs(
        serialize=Association.to_json,
        unserialize=Association.from_json)
}


# Utility
def evaluate(value):
    """Evaluate a value

    Parameters
    ----------
    value: str
        The string to evaluate.

    Returns
    -------
    type or str
        The evaluation. If the value cannot be
        evaluated, the value is simply returned
    """
    try:
        evaled = literal_eval(value)
    except (ValueError, SyntaxError):
        evaled = value
    return evaled


def is_iterable(obj):
    return not isinstance(obj, six.string_types) and \
        not isinstance(obj, tuple) and \
        hasattr(obj, '__iter__')
