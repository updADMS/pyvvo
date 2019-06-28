"""Module for pyvvo's genetic algorithm."""
# Standard library:
import random
import multiprocessing as mp
import array
from uuid import uuid4

# Third party:
from deap import base, creator, tools

# pyvvo:
from pyvvo import equipment


def map_chromosome(regulators, capacitors):
    """Given regulators and capacitors, map states onto a chromosome.

    :param regulators: dictionary as returned by
        equipment.initialize_regulators
    :param capacitors: dictionary as returned by
        equipment.initialize_capacitors

    The map will be keyed by name rather than MRID - this is because
    we'll be looking up objects in GridLAB-D models by name many times,
    but only commanding regulators by MRID once.

    Equipment phase will be appended to the name with an underscore.
    E.g., reg1_A.
    """
    # Initialize our output
    out = {}

    # Track the current index in our chromosome.
    idx = 0

    def map_reg(reg_in, dict_out, idx_in):
        """Nested helper to map a regulator."""
        # If the regulator is not controllable, DO NOT MAP.
        if not reg_in.controllable:
            return dict_out, idx_in

        # Create a key for this regulator
        key = equip_key(reg_in)

        # Compute how many bits are needed to represent this
        # regulator's tap positions.
        length = reg_bin_length(reg_in)

        # Map. Track MRID so we can command the regulators later.
        dict_out[key] = {'idx': (idx_in, idx_in + length),
                         'mrid': reg_in.mrid}

        return dict_out, idx_in + length

    def map_cap(cap_in, dict_out, idx_in):
        """Nested helper to map a capacitor."""
        # DO NOT MAP if not controllable.
        if not cap_in.controllable:
            return dict_out, idx_in

        # Create a key.
        key = equip_key(cap_in)

        # At the moment, we're only supporting capacitors with only one
        # switch, so we can just hard-code the length to be one.
        dict_out[key] = {'idx': (idx_in, idx_in + 1), 'mrid': cap_in.mrid}

        return dict_out, idx_in + 1

    # Loop over the regulators.
    for reg_mrid, reg_or_dict in regulators.items():

        if isinstance(reg_or_dict, equipment.RegulatorSinglePhase):
            # Map it!
            out, idx = map_reg(reg_or_dict, out, idx)

        elif isinstance(reg_or_dict, dict):
            # Loop over the phases and map.
            for reg in reg_or_dict.values():
                out, idx = map_reg(reg, out, idx)

    # Loop over the capacitors.
    for cap_mrid, cap_or_dict in capacitors.items():
        if isinstance(cap_or_dict, equipment.CapacitorSinglePhase):
            out, idx = map_cap(cap_or_dict, out, idx)
        elif isinstance(cap_or_dict, dict):
            # Loop over phases.
            for cap in cap_or_dict.values():
                out, idx = map_cap(cap, out, idx)

    # At this point, our idx represents the total length of the
    # chromosome.
    return out, idx


def equip_key(eq):
    """Given an object which inherits from
    equipment.EquipmentSinglePhase, create a useful key."""
    return eq.name + '_' + eq.phase


def reg_bin_length(reg):
    """Determine how many bits are needed to represent a regulator.

    :param reg: regulator.RegulatorSinglePhase object.

    :returns integer representing how many bits are needed to represent
    a regulators tap positions.
    """
    # Use raise_taps and lower_taps from GridLAB-D to compute the number
    # of bits needed.
    return int_bin_length(reg.raise_taps + reg.lower_taps)


def int_bin_length(x):
    """Determine how many bits are needed to represent an integer."""
    # Rely on the fact that Python's "bin" method prepends the string
    # with "0b": https://docs.python.org/3/library/functions.html#bin
    return len(bin(x)[2:])


def evaluate(individual):
    """Evaluate the fitness of an individual.

    In our case, this means to:
    1) Translate chromosome into regulator and capacitor positions.
    2) Update a GridLAB-D model with the aforementioned positions.
    3) Run the GridLAB-D model.
    4) Use the results of the GridLAB-D model run to compute the
        individual's fitness.
    """
    pass


def main(weight_dict, ):
    """Function to run the GA in its entirety.

    :param weight_dict: Dictionary of weights for determining an
        individual's overall fitness.
    """

    # We're minimizing penalties. Get a deap creator for fitness
    # minimization.
    creator.create("FitnessMin", base.Fitness,
                   weights=tuple(weight_dict.items()))

    # To keep individuals simple, they'll just be arrays of 0's and 1's.
    # The evaluate function will handle translating these arrays into
    # usable information. Use the "H" type code for the unsigned shorts.
    # https://docs.python.org/3.7/library/array.html
    creator.create("Individual", array.array, typecode="H")

    # Initialize our toolbox. Note that toolboxes start with clone and
    # map methods.
    # https://deap.readthedocs.io/en/master/api/base.html#toolbox
    toolbox = base.Toolbox()

    # Following the deap documentation's examples, create an attribute
    # generator for initializing chromosomes.
    toolbox.register("attr_bool", random.randint, 0, 1)

    # Register tool for initializing individuals.
    # TODO: Add seeding support.
    # https://deap.readthedocs.io/en/master/tutorials/basic/part1.html
    toolbox.register("individual", tools.initRepeat, )
