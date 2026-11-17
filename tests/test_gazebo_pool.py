"""Regression checks for compact Gazebo pools and sparse pose updates."""
import xml.etree.ElementTree as ET
from types import SimpleNamespace

import numpy as np
import pytest

from uavsim import gazebo


def make_view(users=2, uavs=1):
    boolean = pytest.importorskip('gz.msgs10.boolean_pb2')
    poses = pytest.importorskip('gz.msgs10.pose_v_pb2')
    factories = pytest.importorskip('gz.msgs10.entity_factory_v_pb2')
    view = object.__new__(gazebo.GazeboView)
    view.Boolean, view.Pose_V = boolean.Boolean, poses.Pose_V
    view.EntityFactory_V = factories.EntityFactory_V
    view.area, view.timeout = 1000, 100
    view.service = f'/world/{gazebo.WORLD}/set_pose_vector'
    view.pool_users, view.pool_uavs = users, uavs
    view.marked = {}
    return view


def test_stationary_users_are_not_resent_and_failed_moves_retry():
    view = make_view()
    calls, accept = [], [True]

    def request(service, msg, *args):
        calls.append(msg)
        return True, SimpleNamespace(data=accept[0])

    view.node = SimpleNamespace(request=request)
    uavs, users = np.zeros((1, 2)), np.zeros((2, 2))
    assert view.update(uavs, users, 100, [0, 0], [0, 2])
    initial = dict(view.marked)
    assert set(initial) == {'mk0_0', 'mk0_1', 'crit1'}
    assert view.update(uavs, users, 100, [0, 0], [0, 2])
    assert view.marked == initial
    assert not any(p.name.startswith(('mk', 'crit', 'imp')) for p in calls[-1].pose)

    # A failed association change must be retried, including hiding the old shirt.
    accept[0] = False
    assert not view.update(uavs, users, 100, [-1, 0], [0, 2])
    assert view.marked == initial
    accept[0] = True
    assert view.update(uavs, users, 100, [-1, 0], [0, 2])
    moved = {p.name: p.position.z for p in calls[-1].pose}
    assert moved['mk0_0'] == gazebo.PARK_Z
    assert moved[f'mk{gazebo.MAX_UAVS}_0'] == gazebo.MARK_Z
    assert 'mk0_0' not in view.marked and 'crit1' in view.marked


def test_growing_pool_retries_rejection_and_never_recreates_existing_models():
    view = make_view()
    existing = set(gazebo._all_markers(2, 1))
    attempts, accept = [], [False]

    def request(service, msg, *args):
        assert service.endswith('/create_multiple')
        names = {ET.fromstring(f.sdf).find('model').get('name') for f in msg.data}
        assert not names & existing
        attempts.append(names)
        if accept[0]:
            existing.update(names)
        return True, SimpleNamespace(data=accept[0])

    view.node = SimpleNamespace(request=request)
    assert not view._ensure_pool(3, 2)
    assert (view.pool_users, view.pool_uavs) == (2, 1)
    accept[0] = True
    assert view._ensure_pool(3, 2)
    assert attempts[0] == attempts[1]
    assert {'mk1_0', 'mk1_2', 'crit2', 'imp2'} <= existing
    assert existing == set(gazebo._all_markers(3, 2))
    assert view._ensure_pool(1, 1) and view._ensure_pool(3, 2)
    assert len(attempts) == 2


def test_rotor_commands_start_and_stop_only_changed_uavs():
    view = make_view()
    view.Double = pytest.importorskip('gz.msgs10.double_pb2').Double
    view._rotor_count, view._rotor_publishers = 1, {}
    messages = []

    def advertise(topic, msg_type):
        return SimpleNamespace(has_connections=lambda: True,
                               publish=lambda msg: messages.append((topic, msg.data)) or True)

    view.node = SimpleNamespace(advertise=advertise)
    view._sync_rotors(3)
    assert len(messages) == 8
    assert {speed for _, speed in messages} == {gazebo.ROTOR_SPEED, -gazebo.ROTOR_SPEED}
    assert all('/uav0/' not in topic for topic, _ in messages)
    view._sync_rotors(3)
    assert len(messages) == 8  # no 20 Hz command spam
    view._sync_rotors(1)
    assert len(messages) == 16 and all(speed == 0 for _, speed in messages[8:])


def test_rotors_retry_transport_discovery_without_losing_a_new_target():
    view = make_view()
    view.Double = pytest.importorskip('gz.msgs10.double_pb2').Double
    view._rotor_count, view._rotor_publishers = 1, {}
    connected, sent = [False], []

    def advertise(topic, msg_type):
        return SimpleNamespace(has_connections=lambda: connected[0],
                               publish=lambda msg: sent.append((topic, msg.data)) or True)

    view.node = SimpleNamespace(advertise=advertise)
    view._sync_rotors(3)
    assert not sent and view._rotor_count == 1
    connected[0] = True
    view._sync_rotors(2)  # configuration changed while discovery was pending
    assert len(sent) == 4 and all('/uav1/' in topic for topic, _ in sent)
    assert view._rotor_count == 2
