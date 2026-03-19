# -*- coding: utf-8 -*-
"""
Shared utilities for erelbi.sangfor_scp Ansible collection.

Provides:
  - SCP_AUTH_ARGSPEC  : common auth argument spec merged into every module
  - scp_argument_spec : builds merged argspec
  - get_client        : constructs SCPClient from module params or env vars
  - handle_scp_error  : converts SCPError subclasses to module.fail_json
  - wait_for_task     : polls task completion, fails on error/timeout
"""
from __future__ import absolute_import, division, print_function
__metaclass__ = type

import os

try:
    from sangfor_scp import SCPClient
    from sangfor_scp.exceptions import (
        SCPError,
        SCPAuthError,
        SCPForbiddenError,
        SCPNotFoundError,
        SCPConflictError,
        SCPRateLimitError,
        SCPBadRequestError,
        SCPServerError,
        SCPTaskError,
        SCPTimeoutError,
    )
    HAS_SANGFOR_SCP = True
    SANGFOR_SCP_IMPORT_ERROR = None
except ImportError as e:
    HAS_SANGFOR_SCP = False
    SANGFOR_SCP_IMPORT_ERROR = str(e)
    SCPClient = None
    SCPError = Exception
    SCPAuthError = Exception
    SCPForbiddenError = Exception
    SCPNotFoundError = Exception
    SCPConflictError = Exception
    SCPRateLimitError = Exception
    SCPBadRequestError = Exception
    SCPServerError = Exception
    SCPTaskError = Exception
    SCPTimeoutError = Exception


SCP_AUTH_ARGSPEC = dict(
    scp_host=dict(type='str', required=False, default=None),
    scp_access_key=dict(type='str', required=False, default=None, no_log=True),
    scp_secret_key=dict(type='str', required=False, default=None, no_log=True),
    scp_region=dict(type='str', required=False, default=None),
    scp_username=dict(type='str', required=False, default=None),
    scp_password=dict(type='str', required=False, default=None, no_log=True),
    scp_verify_ssl=dict(type='bool', required=False, default=False),
    scp_timeout=dict(type='int', required=False, default=30),
)


def scp_argument_spec(**extra):
    """Returns SCP_AUTH_ARGSPEC merged with extra keys."""
    spec = dict(SCP_AUTH_ARGSPEC)
    spec.update(extra)
    return spec


def get_client(module):
    """
    Build SCPClient from module params, falling back to environment variables.

    Environment variables:
      SCP_HOST, SCP_ACCESS_KEY, SCP_SECRET_KEY, SCP_REGION
      SCP_USERNAME, SCP_PASSWORD

    Calls module.fail_json on missing credentials or auth error.
    Returns: SCPClient instance
    """
    if not HAS_SANGFOR_SCP:
        module.fail_json(
            msg="The sangfor-scp Python library is required. "
                "Install with: pip install sangfor-scp",
            exception=SANGFOR_SCP_IMPORT_ERROR,
        )

    p = module.params

    host = p.get('scp_host') or os.environ.get('SCP_HOST')
    if not host:
        module.fail_json(msg="scp_host is required (or set SCP_HOST env var)")

    access_key = p.get('scp_access_key') or os.environ.get('SCP_ACCESS_KEY')
    secret_key = p.get('scp_secret_key') or os.environ.get('SCP_SECRET_KEY')
    region = p.get('scp_region') or os.environ.get('SCP_REGION')
    username = p.get('scp_username') or os.environ.get('SCP_USERNAME')
    password = p.get('scp_password') or os.environ.get('SCP_PASSWORD')
    verify_ssl = p.get('scp_verify_ssl', False)
    timeout = p.get('scp_timeout', 30)

    if not ((access_key and secret_key) or (username and password)):
        module.fail_json(
            msg="Either (scp_access_key + scp_secret_key) or "
                "(scp_username + scp_password) must be provided."
        )

    if access_key and secret_key and not region:
        module.fail_json(
            msg="scp_region is required when using EC2 authentication "
                "(scp_access_key + scp_secret_key). Set it via the scp_region "
                "parameter or the SCP_REGION environment variable."
        )

    try:
        kwargs = dict(
            host=host,
            verify_ssl=verify_ssl,
            timeout=timeout,
        )
        if access_key and secret_key:
            kwargs['access_key'] = access_key
            kwargs['secret_key'] = secret_key
            kwargs['region'] = region
        else:
            kwargs['username'] = username
            kwargs['password'] = password

        return SCPClient(**kwargs)

    except SCPAuthError as e:
        module.fail_json(msg="SCP authentication failed: {0}".format(str(e)))
    except Exception as e:
        module.fail_json(msg="Failed to connect to SCP: {0}".format(str(e)))


def handle_scp_error(module, exc, **extra):
    """
    Converts SCPError subclasses to module.fail_json calls.
    Pass extra kwargs to include in the failure output.
    """
    kwargs = dict(extra)

    if isinstance(exc, SCPNotFoundError):
        kwargs['msg'] = "Resource not found: {0}".format(exc.message or str(exc))
    elif isinstance(exc, SCPForbiddenError):
        kwargs['msg'] = "Permission denied: {0}".format(exc.message or str(exc))
    elif isinstance(exc, SCPAuthError):
        kwargs['msg'] = "Authentication error: {0}".format(exc.message or str(exc))
    elif isinstance(exc, SCPConflictError):
        kwargs['msg'] = "Conflict: {0}".format(exc.message or str(exc))
    elif isinstance(exc, SCPRateLimitError):
        kwargs['msg'] = "Rate limit exceeded: {0}".format(exc.message or str(exc))
    elif isinstance(exc, SCPBadRequestError):
        kwargs['msg'] = "Bad request: {0}".format(exc.message or str(exc))
    elif isinstance(exc, SCPServerError):
        kwargs['msg'] = "SCP server error: {0}".format(exc.message or str(exc))
    elif isinstance(exc, SCPTaskError):
        kwargs['msg'] = "Async task failed: {0}".format(exc.message or str(exc))
        kwargs['task_id'] = getattr(exc, 'task_id', '')
        kwargs['task_data'] = getattr(exc, 'task_data', {})
    elif isinstance(exc, SCPTimeoutError):
        kwargs['msg'] = "Task timed out: {0}".format(exc.message or str(exc))
        kwargs['task_id'] = getattr(exc, 'task_id', '')
        kwargs['timeout'] = getattr(exc, 'timeout', 0)
    else:
        kwargs['msg'] = "SCP error: {0}".format(str(exc))

    if hasattr(exc, 'status_code') and exc.status_code:
        kwargs['http_status'] = exc.status_code
    if hasattr(exc, 'errcode') and exc.errcode:
        kwargs['errcode'] = exc.errcode

    module.fail_json(**kwargs)


def wait_for_task(module, client, task_id, timeout=300):
    """
    Polls task until completion. Calls module.fail_json on failure/timeout.
    Returns task dict on success.
    """
    if not task_id:
        module.fail_json(msg="No task_id returned from SCP API")
    try:
        return client.tasks.wait(task_id, timeout=timeout)
    except SCPTaskError as e:
        module.fail_json(
            msg="Task failed: {0}".format(e.message or str(e)),
            task_id=e.task_id,
            task_data=e.task_data,
        )
    except SCPTimeoutError as e:
        module.fail_json(
            msg="Task timed out after {0}s".format(e.timeout),
            task_id=e.task_id,
        )
    except SCPError as e:
        handle_scp_error(module, e)
