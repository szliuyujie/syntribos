# Copyright 2015 Rackspace
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import logging

from oslo_config import cfg
from requests import RequestException as RequestException

from syntribos.clients.http.base_http_client import HTTPClient
import syntribos.extensions.identity.models.v2 as v2
import syntribos.extensions.identity.models.v3 as v3

logging.basicConfig(level=logging.CRITICAL)
LOG = logging.getLogger(__name__)
CONF = cfg.CONF


def authenticate_v2(
    url, username=None, password=None, tenant_name=None,
    tenant_id=None, domain=None, serialize_format="json",
        deserialize_format="json"):

    headers = {}
    kwargs = {}
    password_creds = None
    if url.endswith('/v2.0/'):
        url = '{0}tokens'.format(url)
    elif url.endswith('/v2.0'):
        url = '{0}/tokens'.format(url)
    else:
        url = '{0}/v2.0/tokens'.format(url)
    headers["Content-Type"] = "application/{0}".format(serialize_format)
    headers["Accept"] = "application/{0}".format(deserialize_format)

    kwargs["tenant_name"] = tenant_name
    kwargs["tenant_id"] = tenant_id

    password_creds = v2.PasswordCredentials(
        username=username, password=password)

    request_entity = v2.Auth(
        tenant_name=tenant_name, tenant_id=tenant_id,
        password_creds=password_creds
    )

    data = request_entity.serialize(serialize_format)
    try:
        resp, signals = HTTPClient().request(
            "POST", url, headers=headers,
            data=data)
        r = resp.json()
    except RequestException as e:
        LOG.debug(e)
    else:
        if not r:
            raise Exception("Failed to authenticate")

        if r['access'] is None:
            raise Exception("Failed to parse Auth response Body")
        return r['access']


def authenticate_v2_config(user_section):
    endpoint = CONF.get(user_section).endpoint or CONF.user.endpoint
    password = CONF.get(user_section).password or CONF.user.password
    if not endpoint or not password:
        msg = "Required config parameters not present: {0}".format(
            [x for x in [endpoint, password] if not x])
        raise KeyError(msg)

    return authenticate_v2(
        url=endpoint,
        username=CONF.get(user_section).username or CONF.user.username,
        password=password,
        tenant_name=CONF.get(user_section).tenant_name or
        CONF.user.tenant_name,
        tenant_id=CONF.get(user_section).tenant_id or CONF.user.tenant_id,
        serialize_format=CONF.get(user_section).serialize_format or
        CONF.user.serialize_format,
        deserialize_format=CONF.get(user_section).deserialize_format or
        CONF.user.deserialize_format)


def get_token_v2(user_section='user'):
    access_data = authenticate_v2_config(user_section)
    return access_data['token']['id']


def authenticate_v3(
    url, username=None, password=None, user_id=None, domain_id=None,
        domain_name=None, token=None, serialize_format="json",
        deserialize_format="json"):

    headers = {}
    kwargs = {}
    if url.endswith('/v3/'):
        url = '{0}auth/tokens'.format(url)
    elif url.endswith('/v3'):
        url = '{0}/auth/tokens'.format(url)
    else:
        url = '{0}/v3/auth/tokens'.format(url)
    headers["Content-Type"] = "application/json"
    headers["Accept"] = "application/json"

    if user_id:
        domain = None
        username = None
    else:
        domain = v3.Domain(name=domain_name, id_=domain_id)

    password = v3.Password(user=v3.User(
        name=username, password=password, id_=user_id, domain=domain
    ))

    if token:
        kwargs = {"token": v3.Token(id_=token), "methods": ["token"]}
    else:
        kwargs = {"password": password, "methods": ["password"]}
    request_entity = v3.Auth(identity=v3.Identity(**kwargs))
    data = request_entity.serialize(serialize_format)
    try:
        r, signals = HTTPClient().request(
            "POST", url, headers=headers,
            data=data)
    except RequestException as e:
        LOG.critical(e)
    else:
        if not r:
            raise Exception("Failed to authenticate")
        return r


def authenticate_v3_config(user_section):
    endpoint = CONF.get(user_section).endpoint or CONF.user.endpoint
    if not endpoint:
        raise KeyError("Required config parameters not present: endpoint")
    return authenticate_v3(
        url=endpoint,
        username=CONF.get(user_section).username or CONF.user.username,
        password=CONF.get(user_section).password or CONF.user.password,
        user_id=CONF.get(user_section).user_id or CONF.user.user_id,
        domain_id=CONF.get(user_section).domain_id or CONF.user.domain_id,
        domain_name=CONF.get(user_section).domain_name or
        CONF.user.domain_name,
        token=CONF.get(user_section).token or CONF.user.token)


def get_token_v3(user_section='user'):
    r = authenticate_v3_config(user_section)
    return r.headers["X-Subject-Token"]
