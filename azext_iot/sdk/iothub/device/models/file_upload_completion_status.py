# coding=utf-8
# --------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
#
# Code generated by Microsoft (R) AutoRest Code Generator.
# Changes may cause incorrect behavior and will be lost if the code is
# regenerated.
# --------------------------------------------------------------------------

from msrest.serialization import Model


class FileUploadCompletionStatus(Model):
    """FileUploadCompletionStatus.

    :param correlation_id:
    :type correlation_id: str
    :param is_success:
    :type is_success: bool
    :param status_code:
    :type status_code: int
    :param status_description:
    :type status_description: str
    """

    _attribute_map = {
        'correlation_id': {'key': 'correlationId', 'type': 'str'},
        'is_success': {'key': 'isSuccess', 'type': 'bool'},
        'status_code': {'key': 'statusCode', 'type': 'int'},
        'status_description': {'key': 'statusDescription', 'type': 'str'},
    }

    def __init__(self, **kwargs):
        super(FileUploadCompletionStatus, self).__init__(**kwargs)
        self.correlation_id = kwargs.get('correlation_id', None)
        self.is_success = kwargs.get('is_success', None)
        self.status_code = kwargs.get('status_code', None)
        self.status_description = kwargs.get('status_description', None)