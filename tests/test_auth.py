#!/usr/bin/env python
# -*- coding: UTF-8 -*-

# HFOS - Hackerfleet Operating System
# ===================================
# Copyright (C) 2011-2017 Heiko 'riot' Weinen <riot@c-base.org> and others.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

__author__ = "Heiko 'riot' Weinen"
__license__ = "GPLv3"

"""
Hackerfleet Operating System - Backend

Test HFOS Auth
==============



"""

from circuits import Manager, Event
from circuits.net.events import write, read
from json import loads, dumps
import pytest
from uuid import uuid4
from hfos.ui.auth import Authenticator
from hfos.events.client import authenticationrequest, authentication
from hfos.tools import std_uuid
from hfos.database import objectmodels
import hfos.logger as logger

from pprint import pprint

m = Manager()

auth = Authenticator()
auth.register(m)


def test_instantiate():
    """Tests correct instantiation"""

    assert type(auth) == Authenticator


def transmit(event_in, channel_in, event_out, channel_out):
    waiter = pytest.WaitEvent(m, event_in, channel_in)

    m.fire(event_out, channel_out)

    result = waiter.wait()

    return result


def test_invalid_user_auth():
    log = logger.LiveLog
    logger.live = True

    m.start()

    client_uuid = std_uuid()
    event = authenticationrequest(
        username='test',
        password='test',
        clientuuid=client_uuid,
        requestedclientuuid=client_uuid,
        sock=None,
        auto=False
    )

    result = transmit('authentication', 'auth', event, 'auth')

    assert result is None
    assert "No userobject due to error" in str(log)


def test_createuser():
    class createuser_event():
        def __init__(self):
            self.username = 'test_user'
            self.password = 'test_password'
            self.clientuuid = std_uuid()
            self.sock = None

    m.start()

    waiter = pytest.WaitEvent(m, 'authentication', 'auth')

    auth.createuser(createuser_event())

    result = waiter.wait()

    assert type(result) == authentication
