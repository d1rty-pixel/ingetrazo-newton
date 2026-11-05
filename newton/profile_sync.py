"""Explicit profile associations and atomic, undoable updates of linked bodies."""
import copy
import hashlib
import json
from core.history import CompoundCommand
from . import profiles
from .model import KEY,settings,Configure,reference_id
from .worker import joint_settings,resolve_couplings


def fingerprint(profile):
    p = profiles.validate(profile)
    joint = p['joint']
    if joint and joint['limit_hardness']==1:
        # Signatures stored before the setting existed stay valid for the default.
        joint = {k:v for k,v in joint.items() if k!='limit_hardness'}
    payload = json.dumps([p['body'],joint],sort_keys=True,allow_nan=False)
    return hashlib.sha256(payload.encode()).hexdigest()


def link(profile):
    return dict(id=profile['id'],signature=fingerprint(profile))


def association_values(group,profile):
    values = dict(profile_link=link(profile))
    if KEY not in (group.ext or {}):
        values['mode'] = 'ignore' if group.billboard else 'static'
    return values


def status(group,profile):
    association = settings(group).get('profile_link') or {}
    if profile is None:return 'Missing profile'
    if association.get('signature')!=fingerprint(profile):return 'Profile changed'
    if fingerprint(profiles.from_group(group,'Body'))!=fingerprint(profile):return 'Local changes'
    return 'In sync'


def command(scene,updates):
    """Validate the complete projected mechanism before changing any object.

    updates maps body IDs to profiles. Spatial frames, names and links remain
    body-owned. New axes require explicit placement in the sidebar instead.
    """
    commands = [];projected = {}
    for group in scene.groups:
        cfg = copy.deepcopy(settings(group))
        if group.uid in updates:
            p = profiles.validate(updates[group.uid]);old = cfg.get('joint')
            if p['body']['shape']=='compound' and not group.children:
                raise ValueError('Compound collision needs child groups or components.')
            if p['joint'] and not old:
                raise ValueError('Place an axis on each linked body before syncing this profile.')
            if p['joint'] and cfg.get('flexible'):
                raise ValueError('Flexible bodies cannot also have a motion axis.')
            joint = joint_settings(dict(old,**p['joint'])) if p['joint'] else None
            values = dict(p['body'],joint=joint,reference=reference_id(group),profile_link=link(p))
            cfg.update(values);commands.append(Configure([group],values,partial=True))
        projected[group.uid] = cfg
    if set(updates)-set(projected):raise ValueError('Document changed.')
    removed = {uid for uid,cfg in projected.items() if not cfg.get('joint') or cfg['mode']!='dynamic'}
    joints = {}
    for group in scene.groups:
        cfg = projected[group.uid];joint = cfg.get('joint')
        if not joint or cfg['mode']!='dynamic':continue
        if (joint.get('coupling') or {}).get('master') in removed:
            joint = dict(joint,coupling=None)
            commands.append(Configure([group],dict(joint=joint),partial=True))
        joints[group.uid] = joint_settings(joint)
    resolve_couplings(joints)
    return CompoundCommand(commands) if commands else None


def execute(panel,cmd):
    if cmd:
        panel.app.viewport.history.execute(cmd)
        panel.app.viewport.notify_scene_changed();panel.refresh()
