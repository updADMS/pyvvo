"""Module for interfacing with the GridAPPS-D platform.

Note this module depends on the GridAPPS-D platform being up and
running.
"""
from gridappsd import GridAPPSD, topics
from gridappsd.difference_builder import DifferenceBuilder as DiffBuilder
from gridappsd import utils as gad_utils

import simplejson as json
import os
import logging
import re
from datetime import datetime
import copy
from pyvvo import utils
from pyvvo import timeseries

# Setup log.
LOG = logging.getLogger(__name__)

# Use this date format for logging.
DATE_FORMAT = '%Y-%m-%d %H:%M:%S'

# Compile regular expressions for fixing bad json return.
# TODO: remove when the platform is fixed.
REGEX_1 = re.compile(r'^\s*\{\s*"data"\s*:\s*')
REGEX_2 = re.compile(r'\s*,\s*"responseComplete".+$')


def get_platform_env_var():
    """Helper to get the 'platform' environment variable."""
    # Assign platform input.
    try:
        platform = os.environ['platform']
    except KeyError:
        m = ("Within the pyvvo Docker container, the 'platform' "
             "environment variable must be set. It should be '0' "
             "or '1' indicating whether or not the container is "
             "inside the platform's docker-compose network.")
        raise KeyError(m)
    else:
        if (platform != '0') and (platform != '1'):
            m = ("The 'platform' environment variable must be '0' or"
                 "'1.' It currently evaluates to {}").format(platform)
            raise ValueError(m)

    LOG.debug("Retrieved 'platform' environment variable.")
    return platform


def get_gad_object(**kwargs):
    """Helper to get a GridAPPSD object.

    :param **kwargs: Passed directly to the GridAPPSD constructor.
    """
    # Get platform address
    address = get_gad_address()

    # TODO: handle connection failures?
    # TODO: flexibility for different username/password?
    gad = GridAPPSD(address=address, username=gad_utils.get_gridappsd_user(),
                    password=gad_utils.get_gridappsd_pass(), **kwargs)

    LOG.debug('GridAPPSD object created and connected to the platform.')
    return gad


def get_gad_address():
    """Helper to get GRIDAPPS-D address.

    The address is different depending on whether we're operating
    inside or outside the platform.

    TODO: logging
    """
    # Determine whether or not we're running in the platform.
    platform = get_platform_env_var()

    if platform == '1':
        # We're in the platform. Use the API helper.
        address = gad_utils.get_gridappsd_address()
    elif platform == '0':
        # We're not in the platform. Use the local IP address and get
        # the port from the environment.
        try:
            address = (os.environ['host_ip'], os.environ['GRIDAPPSD_PORT'])
        except KeyError:
            # Environment variables not properly set.
            m = ("If running outside the platform ('platform' input is '0'), "
                 + "the environment variables 'host_ip' and 'GRIDAPPSD_PORT' "
                 + "must be set.")
            raise KeyError(m)
    else:
        m = "The 'platform' input must be either '0' or '1.'"
        if isinstance(platform, str):
            raise ValueError(m)
        else:
            raise TypeError(m)

    LOG.debug('GridAPPS-D address obtained.')
    return address


def filter_output_by_mrid(message, mrids):
    """Given an output message from the simulator, return only the
    measurements with mrid's that we care about.

    :param message: dictionary, message from simulator subscription.
    :param mrids: list of mrids corresponding to measurements to keep.
        NOTE: This list is assumed to be a list of strings.
    :returns list of measurements from message which correspond to the
        mrids in the mrids input.
    """
    # Simply type checks.
    if not isinstance(message, dict):
        raise TypeError('message must be a dictionary!')

    if not isinstance(mrids, list):
        raise TypeError('mrids must be a list!')

    # We'll return a simple list of measurements.
    out = []

    # Create a copy of the inputs mrids. Creating a copy so that we can
    # remove objects and thus shrink our list as we iterate to reduce
    # searching.
    mrids_c = copy.copy(mrids)

    # Iterate over the message measurements.
    for meas in message['message']['measurements']:

        # If there are no more mrids in our copy, exit the loop.
        if len(mrids_c) == 0:
            break

        # Attempt to delete the mrid for this measurement from our list
        # of mrids.
        try:
            mrids_c.remove(meas['measurement_mrid'])
        except ValueError:
            # We don't care about this MRID. Move to next object.
            continue

        # If we're here, we want to keep this measurement.
        out.append(meas)

    # If we don't get what we wanted, raise an exception.
    # In the future, we may not want this to be an exception.
    if len(mrids_c) != 0:
        m = '{} mrids were found in the given message!'.format(len(mrids_c))
        raise ValueError(m)

    # All done, return.
    return out


class PlatformManager:
    """Class for interfacing with the GridAPPS-D platform API.

    Note that this class is really intended for subscribing, etc. For
    querying the Blazegraph database (with SPARQL queries), see
    sparql.py
    """

    def __init__(self, timeout=30):
        """Gather environment variables, etc.

        :param timeout: Timeout for GridAPPS-D API requests.
        """
        # Setup logging.
        self.log = logging.getLogger(__name__)

        # Assign timeout.
        self.timeout = timeout

        # Get GridAPPSD object.
        self.gad = get_gad_object()

        self.log.info('Connected to GridAPPS-D platform.')

        # Initialize property for holding a simulation ID.
        self._sim_id = None

        # # Get information on available models.
        # self.platform_model_info = self.gad_object.query_model_info()
        #
        # # Ensure the query succeeded.
        # if not self.platform_model_info['responseComplete']:
        #     # TODO: Try again?
        #     # TODO: Exception handling, etc.
        #     raise UserWarning('GridAPPS-D query failed.')
        #
        # # Assign model name.
        # self.model_name = model_name
        # # Get the ID for the given model name.
        # self.model_id = self._get_model_id(self.model_name)

        pass

    @property
    def sim_id(self):
        return self._sim_id

    @sim_id.setter
    def sim_id(self, value):
        self._sim_id = value

    def send_command(self, object_ids, attributes, forward_values,
                     reverse_values, sim_id=None):
        """Function for sending a command into a running simulation.
        This is partly a wrapper to DifferenceBuilder, but also sends
        the command into the simulation.

        Note all parameters below must be 1:1. In other words,
        object_id[3] should correspond to attribute[3].

        :param object_ids: List of mrids of objects to command.
        :param attributes: List of CIM attributes belonging to the
            objects. These attributes are what we're actually
            commanding/changing.
        :param forward_values: List of new values for attributes.
        :param reverse_values: List of old (current) values for
            attributes.
        :param sim_id: Simulation ID. If None, will attempt to use
            self.sim_id. If self.sim_id is also None, ValueError will
            be raised.
        """
        # Ensure we get lists.
        if ((not isinstance(object_ids, list))
                or (not isinstance(attributes, list))
                or (not isinstance(forward_values, list))
                or (not isinstance(reverse_values, list))):
            m = 'object_ids, attributes, forward_values, and reverse_values '\
                'must all be lists!'
            raise TypeError(m)

        # Ensure lists are the same length.
        if not (len(object_ids)
                == len(attributes)
                == len(forward_values)
                == len(reverse_values)):
            m = 'object_ids, attributes, forward_values, and reverse_values '\
                'must be the same length!'
            raise ValueError(m)

        # Ensure we have a simulation ID.
        if sim_id is None:
            sim_id = self.sim_id

        if sim_id is None:
            m = 'sim_id input is None, and so is self.sim_id. In order to '\
                'send a command, we must have a simulation ID.'
            raise ValueError(m)

        self.log.debug('Input checks complete for send_command.')

        # Initialize difference builder.
        diff_builder = DiffBuilder(simulation_id=sim_id)
        self.log.debug('DifferenceBuilder initialized.')

        # Iterate to build add differences.
        for k in range(len(object_ids)):
            diff_builder.add_difference(object_id=object_ids[k],
                                        attribute=attributes[k],
                                        forward_value=forward_values[k],
                                        reverse_value=reverse_values[k])

        # Get the message and log it.
        msg = diff_builder.get_message()
        self.log.info('Preparing to send following command: {}'.format(msg))

        # Send command to simulation.
        self.gad.send(topic=topics.fncs_input_topic(sim_id),
                      message=json.dumps(msg))

        # Return the message in case we want to examine it, audit, etc.
        # Mainly useful for testing at this point.
        return msg

    def get_glm(self, model_id):
        """Given a model ID, get a GridLAB-D (.glm) model."""
        payload = {'configurationType': 'GridLAB-D Base GLM',
                   'parameters': {'model_id': model_id}}
        response = self.gad.get_response(topic=topics.CONFIG, message=payload,
                                         timeout=self.timeout)

        self.log.info('GridLAB-D model received from platform.')

        # Fix bad json return.
        # TODO: remove when platform is fixed.
        glm = REGEX_2.sub('', REGEX_1.sub('', response['message']))
        return glm

    def _query_weather(self, start_time, end_time):
        """Private helper for querying weather data."""
        # The weather data API needs microseconds from the epoch as a
        # string. Why this inconsistency? I don't know.
        payload = {'queryMeasurement': 'weather',
                   'queryFilter': {'startTime':
                                       utils.dt_to_us_from_epoch(start_time),
                                   'endTime':
                                       utils.dt_to_us_from_epoch(end_time)},
                   'responseFormat': 'JSON'}

        # TODO: Update gridappsd-python
        topic = '/queue/goss.gridappsd.process.request.data.timeseries'

        data = self.gad.get_response(topic=topic, message=payload,
                                     timeout=self.timeout)

        # Check to see if we actually have any data.
        if data['data'] is None:
            raise QueryReturnEmptyError(topic=topic, query=payload)

        return data

    def get_weather(self, start_time, end_time):
        """Helper for querying weather data.

        :param start_time: datetime.datetime object denoting the
            beginning time of weather data to pull.
        :param end_time: "..." end time "..."
        """
        # Check inputs:
        if (not isinstance(start_time, datetime)) \
                or (not isinstance(end_time, datetime)):
            m = 'start_time and end_time must both be datetime.datetime!'
            raise TypeError(m)

        # Query the platform to get the weather data.
        data = self._query_weather(start_time=start_time, end_time=end_time)

        # Parse the weather data.
        data_df = timeseries.parse_weather(data)

        self.log.info(
            'Weather data for {} through {} pulled and parsed.'.format(
                start_time.strftime(DATE_FORMAT),
                end_time.strftime(DATE_FORMAT)
            )
        )
        return data_df


        # Run simulation.
        sim_id = self.gad.get_response(topic=topics.REQUEST_SIMULATION,
                                       message=json.dumps(sim_request))

        return sim_id


class Error(Exception):
    """Base class for exceptions in this module."""
    pass


class QueryReturnEmptyError(Error):
    """Raised if a platform query for data returns empty.

    Attributes:
        topic -- Topic query was executed on.
        query -- Given query.
        message -- explanation of the error.
    """

    def __init__(self, topic, query):
        self.topic = topic
        self.query = query
        self.message = 'Query on topic {} returned no data! Query: {}'.format(
            self.topic, self.query
        )


    # def _parse_simulation_request(self, *args, **kwargs):
    #     """Parse request to start a simulation."""
    #     print('_parse_simulation_request has been called!', flush=True)
    #     pass
    #
    # def _get_model_id(self, model_name):
    #     """Given a model's name, get it's ID."""
    #     # Loop over the models until we find our model_name, and get its ID.
    #     model_id = None
    #     for model in self.platform_model_info['data']['models']:
    #         if model['modelName'] == model_name:
    #             model_id = model['modelId']
    #
    #     # Raise exception if the model_id could not be found.
    #     # TODO: Exception management.
    #     if model_id is None:
    #         m = 'Could not find the model ID for {}.'.format(model_name)
    #         raise UserWarning(m)
    #
    #     return model_id
#
#
# if __name__ == '__main__':
#     # Get host IP address. NOTE: This environment variable must be set
#     # when pyvvo is not being run from within the GridAPPS-D platform
#     # via docker-compose.
#     HOST_IP = os.environ['host_ip']
#     PLATFORM = os.environ['platform']
#
#     # Get information related to the platform.
#     PORT = os.environ['GRIDAPPSD_PORT']
#
#     # Create a PlatformManager object, which connects to the platform.
#     mgr = PlatformManager(platform=PLATFORM, model_name='ieee8500')
#
#     # Get model information.
#     info = mgr.gad.query_model_info()
#
#
#     print('stuff cause debugger is being shitty.')
#     # Get the platform status.
#     # msg = mgr.gad.get_platform_status()
#
#     # Request a simulation.
#     # sim_topic = gad_utils.REQUEST_SIMULATION
#     # print('yay')
#
#     pass
