# coding=utf-8
# --------------------------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for license information.
# --------------------------------------------------------------------------------------------

from azext_iot.common.shared import EntityStatusType, AttestationType, AllocationType, ReprovisionType
from azext_iot.common.utility import generate_key
from azext_iot.tests.dps import (
    API_VERSION,
    CERT_PATH,
    DATAPLANE_AUTH_TYPES,
    WEBHOOK_URL,
    IoTDPSLiveScenarioTest
)

test_endorsement_key = (
    "AToAAQALAAMAsgAgg3GXZ0SEs/gakMyNRqXXJP1S124GUgtk8qHaGzMUaaoABgCAAEMAEAgAAAAAAAEAibym9HQP9vxCGF5dVc1Q"
    "QsAGe021aUGJzNol1/gycBx3jFsTpwmWbISRwnFvflWd0w2Mc44FAAZNaJOAAxwZvG8GvyLlHh6fGKdh+mSBL4iLH2bZ4Ry22cB3"
    "CJVjXmdGoz9Y/j3/NwLndBxQC+baNvzvyVQZ4/A2YL7vzIIj2ik4y+ve9ir7U0GbNdnxskqK1KFIITVVtkTIYyyFTIR0BySjPrRI"
    "Dj7r7Mh5uF9HBppGKQCBoVSVV8dI91lNazmSdpGWyqCkO7iM4VvUMv2HT/ym53aYlUrau+Qq87Tu+uQipWYgRdF11KDfcpMHqqzB"
    "QQ1NpOJVhrsTrhyJzO7KNw=="
)


class TestDPSEnrollments(IoTDPSLiveScenarioTest):
    def __init__(self, test_method):
        super(TestDPSEnrollments, self).__init__(test_method)

    def test_dps_compute_device_key(self):
        offline_device_key = self.cmd(
            'az iot dps compute-device-key --key "{}" '
            "--registration-id myarbitrarydeviceId".format(test_endorsement_key)
        ).output
        offline_device_key = offline_device_key.strip("\"'\n")
        assert offline_device_key == "cT/EXZvsplPEpT//p98Pc6sKh8mY3kYgSxavHwMkl7w="

    def test_dps_enrollment_tpm_lifecycle(self):
        attestation_type = AttestationType.tpm.value
        for auth_phase in DATAPLANE_AUTH_TYPES:
            enrollment_id = self.generate_enrollment_names()[0]
            device_id = self.generate_device_names()[0]

            enrollment = self.cmd(
                self.set_cmd_auth_type(
                    "iot dps enrollment create --enrollment-id {} --attestation-type {}"
                    " -g {} --dps-name {} --endorsement-key {}"
                    " --provisioning-status {} --device-id {} --initial-twin-tags {}"
                    " --initial-twin-properties {} --device-information {} "
                    "--allocation-policy {} --iot-hubs {}".format(
                        enrollment_id,
                        attestation_type,
                        self.entity_rg,
                        self.entity_dps_name,
                        test_endorsement_key,
                        EntityStatusType.enabled.value,
                        device_id,
                        '"{generic_dict}"',
                        '"{generic_dict}"',
                        '"{generic_dict}"',
                        AllocationType.static.value,
                        self.hub_host_name,
                    ),
                    auth_type=auth_phase
                ),
                checks=[
                    self.check("attestation.type", attestation_type),
                    self.check("registrationId", enrollment_id),
                    self.check("provisioningStatus", EntityStatusType.enabled.value),
                    self.check("deviceId", device_id),
                    self.check("allocationPolicy", AllocationType.static.value),
                    self.check("iotHubs", self.hub_host_name.split()),
                    self.check("initialTwin.tags", self.kwargs["generic_dict"]),
                    self.check("optionalDeviceInformation", self.kwargs["generic_dict"]),
                    self.check(
                        "initialTwin.properties.desired", self.kwargs["generic_dict"]
                    ),
                    self.exists("reprovisionPolicy"),
                    self.check("reprovisionPolicy.migrateDeviceData", True),
                    self.check("reprovisionPolicy.updateHubAssignment", True),
                ],
            ).get_output_in_json()
            etag = enrollment["etag"]

            self.cmd(
                self.set_cmd_auth_type(
                    "iot dps enrollment list -g {} --dps-name {}".format(
                        self.entity_rg, self.entity_dps_name
                    ),
                    auth_type=auth_phase
                ),
                checks=[
                    self.check("length(@)", 1),
                    self.check("[0].registrationId", enrollment_id),
                ],
            )

            self.cmd(
                self.set_cmd_auth_type(
                    "iot dps enrollment show -g {} --dps-name {} --enrollment-id {}".format(
                        self.entity_rg, self.entity_dps_name, enrollment_id
                    ),
                    auth_type=auth_phase
                ),
                checks=[self.check("registrationId", enrollment_id)],
            )

            self.cmd(
                self.set_cmd_auth_type(
                    "iot dps enrollment show -g {} --dps-name {} --enrollment-id {} --show-keys".format(
                        self.entity_rg, self.entity_dps_name, enrollment_id
                    ),
                    auth_type=auth_phase
                ),
                checks=[
                    self.check("registrationId", enrollment_id),
                    self.check("attestation.type", attestation_type),
                    self.exists("attestation.{}".format(attestation_type)),
                ],
            )

            self.cmd(
                self.set_cmd_auth_type(
                    "iot dps enrollment update -g {} --dps-name {} --enrollment-id {}"
                    " --provisioning-status {} --etag {} --info {}".format(
                        self.entity_rg,
                        self.entity_dps_name,
                        enrollment_id,
                        EntityStatusType.disabled.value,
                        etag,
                        '""'
                    ),
                    auth_type=auth_phase
                ),
                checks=[
                    self.check("attestation.type", attestation_type),
                    self.check("registrationId", enrollment_id),
                    self.check("provisioningStatus", EntityStatusType.disabled.value),
                    self.check("deviceId", device_id),
                    self.check("allocationPolicy", AllocationType.static.value),
                    self.check("iotHubs", self.hub_host_name.split()),
                    self.exists("initialTwin.tags"),
                    self.exists("initialTwin.properties.desired"),
                    self.exists("optionalDeviceInformation"),
                ],
            )

            self.cmd(
                self.set_cmd_auth_type(
                    "iot dps enrollment delete -g {} --dps-name {} --enrollment-id {}".format(
                        self.entity_rg, self.entity_dps_name, enrollment_id
                    ),
                    auth_type=auth_phase
                ),
            )

    def test_dps_enrollment_x509_lifecycle(self):
        attestation_type = AttestationType.x509.value
        for auth_phase in DATAPLANE_AUTH_TYPES:
            enrollment_id = self.generate_enrollment_names()[0]
            device_id = self.generate_device_names()[0]

            etag = self.cmd(
                self.set_cmd_auth_type(
                    "iot dps enrollment create --enrollment-id {} --attestation-type {}"
                    " -g {} --dps-name {} --cp {} --scp {}"
                    " --provisioning-status {} --device-id {}"
                    " --initial-twin-tags {} --initial-twin-properties {}"
                    " --allocation-policy {} --iot-hubs {}".format(
                        enrollment_id,
                        attestation_type,
                        self.entity_rg,
                        self.entity_dps_name,
                        CERT_PATH,
                        CERT_PATH,
                        EntityStatusType.enabled.value,
                        device_id,
                        '"{generic_dict}"',
                        '"{generic_dict}"',
                        AllocationType.hashed.value,
                        self.hub_host_name,
                    ),
                    auth_type=auth_phase
                ),
                checks=[
                    self.check("attestation.type", attestation_type),
                    self.check("registrationId", enrollment_id),
                    self.check("provisioningStatus", EntityStatusType.enabled.value),
                    self.check("deviceId", device_id),
                    self.check("allocationPolicy", AllocationType.hashed.value),
                    self.check("iotHubs", self.hub_host_name.split()),
                    self.check("initialTwin.tags", self.kwargs["generic_dict"]),
                    self.check(
                        "initialTwin.properties.desired", self.kwargs["generic_dict"]
                    ),
                    self.exists("reprovisionPolicy"),
                    self.check("reprovisionPolicy.migrateDeviceData", True),
                    self.check("reprovisionPolicy.updateHubAssignment", True),
                ],
            ).get_output_in_json()["etag"]

            self.cmd(
                self.set_cmd_auth_type(
                    "iot dps enrollment list -g {} --dps-name {}".format(self.entity_rg, self.entity_dps_name),
                    auth_type=auth_phase
                ),
                checks=[
                    self.check("length(@)", 1),
                    self.check("[0].registrationId", enrollment_id),
                ],
            )

            self.cmd(
                self.set_cmd_auth_type(
                    "iot dps enrollment show -g {} --dps-name {} --enrollment-id {}".format(
                        self.entity_rg, self.entity_dps_name, enrollment_id
                    ),
                    auth_type=auth_phase
                ),
                checks=[self.check("registrationId", enrollment_id)],
            )

            self.cmd(
                self.set_cmd_auth_type(
                    "iot dps enrollment update -g {} --dps-name {} --enrollment-id {}"
                    " --provisioning-status {} --etag {} --info {} --rc".format(
                        self.entity_rg,
                        self.entity_dps_name,
                        enrollment_id,
                        EntityStatusType.disabled.value,
                        etag,
                        '"{generic_dict}"',
                    ),
                    auth_type=auth_phase
                ),
                checks=[
                    self.check("attestation.type", attestation_type),
                    self.check("registrationId", enrollment_id),
                    self.check("provisioningStatus", EntityStatusType.disabled.value),
                    self.check("deviceId", device_id),
                    self.check("allocationPolicy", AllocationType.hashed.value),
                    self.check("iotHubs", self.hub_host_name.split()),
                    self.exists("initialTwin.tags"),
                    self.exists("initialTwin.properties.desired"),
                    self.check("optionalDeviceInformation", self.kwargs["generic_dict"]),
                    self.check("attestation.type.x509.clientCertificates.primary", None),
                ],
            )

            self.cmd(
                self.set_cmd_auth_type(
                    "iot dps enrollment delete -g {} --dps-name {} --enrollment-id {}".format(
                        self.entity_rg, self.entity_dps_name, enrollment_id
                    ),
                    auth_type=auth_phase
                ),
            )

    def test_dps_enrollment_symmetrickey_lifecycle(self):
        attestation_type = AttestationType.symmetricKey.value
        for auth_phase in DATAPLANE_AUTH_TYPES:
            enrollment_id, enrollment_id2 = self.generate_enrollment_names(count=2)
            primary_key = generate_key()
            secondary_key = generate_key()
            device_id = self.generate_enrollment_names()[0]

            # Use provided keys
            etag = self.cmd(
                self.set_cmd_auth_type(
                    "iot dps enrollment create --enrollment-id {} --attestation-type {}"
                    " -g {} --dps-name {} --pk {} --sk {}"
                    " --provisioning-status {} --device-id {}"
                    " --initial-twin-tags {} --initial-twin-properties {} --device-information {}"
                    " --allocation-policy {} --rp {} --iot-hubs {} --edge-enabled".format(
                        enrollment_id,
                        attestation_type,
                        self.entity_rg,
                        self.entity_dps_name,
                        primary_key,
                        secondary_key,
                        EntityStatusType.enabled.value,
                        device_id,
                        '"{generic_dict}"',
                        '"{generic_dict}"',
                        '"{generic_dict}"',
                        AllocationType.geolatency.value.lower(),
                        ReprovisionType.reprovisionandresetdata.value,
                        self.hub_host_name,
                    ),
                    auth_type=auth_phase
                ),
                checks=[
                    self.check("attestation.type", attestation_type),
                    self.check("registrationId", enrollment_id),
                    self.check("provisioningStatus", EntityStatusType.enabled.value),
                    self.check("deviceId", device_id),
                    self.check("allocationPolicy", AllocationType.geolatency.value),
                    self.check("iotHubs", self.hub_host_name.split()),
                    self.check("initialTwin.tags", self.kwargs["generic_dict"]),
                    self.check("optionalDeviceInformation", self.kwargs["generic_dict"]),
                    self.check(
                        "initialTwin.properties.desired", self.kwargs["generic_dict"]
                    ),
                    self.exists("reprovisionPolicy"),
                    self.check("reprovisionPolicy.migrateDeviceData", False),
                    self.check("reprovisionPolicy.updateHubAssignment", True),
                    self.check("capabilities.iotEdge", True),
                ],
            ).get_output_in_json()["etag"]

            self.cmd(
                self.set_cmd_auth_type(
                    "iot dps enrollment list -g {} --dps-name {}".format(self.entity_rg, self.entity_dps_name),
                    auth_type=auth_phase
                ),
                checks=[
                    self.check("length(@)", 1),
                    self.check("[0].registrationId", enrollment_id),
                ],
            )

            self.cmd(
                self.set_cmd_auth_type(
                    "iot dps enrollment show -g {} --dps-name {} --enrollment-id {}".format(
                        self.entity_rg, self.entity_dps_name, enrollment_id
                    ),
                    auth_type=auth_phase
                ),
                checks=[self.check("registrationId", enrollment_id)],
            )

            self.cmd(
                self.set_cmd_auth_type(
                    "iot dps enrollment update -g {} --dps-name {} --enrollment-id {}"
                    " --provisioning-status {} --etag {} --edge-enabled False"
                    " --allocation-policy {} --webhook-url {} --api-version {}".format(
                        self.entity_rg,
                        self.entity_dps_name,
                        enrollment_id,
                        EntityStatusType.disabled.value,
                        etag,
                        AllocationType.custom.value,
                        WEBHOOK_URL,
                        API_VERSION,
                    ),
                    auth_type=auth_phase
                ),
                checks=[
                    self.check("attestation.type", attestation_type),
                    self.check("registrationId", enrollment_id),
                    self.check("provisioningStatus", EntityStatusType.disabled.value),
                    self.check("deviceId", device_id),
                    self.check("allocationPolicy", "custom"),
                    self.check("customAllocationDefinition.webhookUrl", WEBHOOK_URL),
                    self.check("customAllocationDefinition.apiVersion", API_VERSION),
                    self.check("iotHubs", None),
                    self.exists("initialTwin.tags"),
                    self.exists("initialTwin.properties.desired"),
                    self.check("attestation.symmetricKey.primaryKey", primary_key),
                    self.check("capabilities.iotEdge", False),
                ],
            )

            # Use service generated keys
            self.cmd(
                self.set_cmd_auth_type(
                    "iot dps enrollment create --enrollment-id {} --attestation-type {}"
                    " -g {} --dps-name {} --allocation-policy {} --webhook-url {} --api-version {}".format(
                        enrollment_id2,
                        attestation_type,
                        self.entity_rg,
                        self.entity_dps_name,
                        AllocationType.custom.value,
                        WEBHOOK_URL,
                        API_VERSION,
                    ),
                    auth_type=auth_phase
                ),
                checks=[
                    self.check("attestation.type", attestation_type),
                    self.check("registrationId", enrollment_id2),
                    self.check("allocationPolicy", "custom"),
                    self.check("customAllocationDefinition.webhookUrl", WEBHOOK_URL),
                    self.check("customAllocationDefinition.apiVersion", API_VERSION),
                ],
            )

            self.cmd(
                self.set_cmd_auth_type(
                    "iot dps enrollment delete -g {} --dps-name {} --enrollment-id {}".format(
                        self.entity_rg, self.entity_dps_name, enrollment_id
                    ),
                    auth_type=auth_phase
                ),
            )
            self.cmd(
                self.set_cmd_auth_type(
                    "iot dps enrollment delete -g {} --dps-name {} --enrollment-id {}".format(
                        self.entity_rg, self.entity_dps_name, enrollment_id2
                    ),
                    auth_type=auth_phase
                ),
            )

    def test_dps_enrollment_group_x509_lifecycle(self):
        for auth_phase in DATAPLANE_AUTH_TYPES:
            enrollment_id = self.generate_enrollment_names(group=True)[0]
            etag = self.cmd(
                self.set_cmd_auth_type(
                    "iot dps enrollment-group create --enrollment-id {} -g {} --dps-name {}"
                    " --cp {} --scp {} --provisioning-status {} --allocation-policy {}"
                    " --iot-hubs {} --edge-enabled".format(
                        enrollment_id,
                        self.entity_rg,
                        self.entity_dps_name,
                        CERT_PATH,
                        CERT_PATH,
                        EntityStatusType.enabled.value,
                        AllocationType.geolatency.value,
                        self.hub_host_name,
                    ),
                    auth_type=auth_phase
                ),
                checks=[
                    self.check("enrollmentGroupId", enrollment_id),
                    self.check("provisioningStatus", EntityStatusType.enabled.value),
                    self.exists("reprovisionPolicy"),
                    self.check("allocationPolicy", AllocationType.geolatency.value),
                    self.check("iotHubs", self.hub_host_name.split()),
                    self.check("reprovisionPolicy.migrateDeviceData", True),
                    self.check("reprovisionPolicy.updateHubAssignment", True),
                    self.check("capabilities.iotEdge", True),
                ],
            ).get_output_in_json()["etag"]

            self.cmd(
                self.set_cmd_auth_type(
                    "iot dps enrollment-group list -g {} --dps-name {}".format(self.entity_rg, self.entity_dps_name),
                    auth_type=auth_phase
                ),
                checks=[
                    self.check("length(@)", 1),
                    self.check("[0].enrollmentGroupId", enrollment_id),
                ],
            )

            self.cmd(
                self.set_cmd_auth_type(
                    "iot dps enrollment-group show -g {} --dps-name {} --enrollment-id {}".format(
                        self.entity_rg, self.entity_dps_name, enrollment_id
                    ),
                    auth_type=auth_phase
                ),
                checks=[self.check("enrollmentGroupId", enrollment_id)],
            )

            self.cmd(
                self.set_cmd_auth_type(
                    "iot dps enrollment-group show -g {} --dps-name {} --enrollment-id {} --show-keys".format(
                        self.entity_rg, self.entity_dps_name, enrollment_id
                    ),
                    auth_type=auth_phase
                ),
                checks=[
                    self.check("enrollmentGroupId", enrollment_id),
                    self.exists("attestation.x509"),
                ],
            )

            # Compute Device Key only works for symmetric key enrollment groups
            self.cmd(
                self.set_cmd_auth_type(
                    'az iot dps compute-device-key -g {} --dps-name {} --enrollment-id {} '
                    "--registration-id myarbitrarydeviceId".format(
                        self.entity_rg, self.entity_dps_name, enrollment_id
                    ),
                    auth_type=auth_phase
                ),
                expect_failure=True
            )

            etag = self.cmd(
                self.set_cmd_auth_type(
                    "iot dps enrollment-group update -g {} --dps-name {} --enrollment-id {}"
                    " --provisioning-status {} --rsc --etag {} --rp {} --allocation-policy {}"
                    " --edge-enabled False --scp {}".format(
                        self.entity_rg,
                        self.entity_dps_name,
                        enrollment_id,
                        EntityStatusType.disabled.value,
                        etag,
                        ReprovisionType.never.value,
                        AllocationType.hashed.value,
                        CERT_PATH,
                    ),
                    auth_type=auth_phase
                ),
                checks=[
                    self.check("attestation.type", AttestationType.x509.value),
                    self.check("enrollmentGroupId", enrollment_id),
                    self.check("provisioningStatus", EntityStatusType.disabled.value),
                    self.check("attestation.type.x509.clientCertificates.secondary", None),
                    self.exists("reprovisionPolicy"),
                    self.check("allocationPolicy", AllocationType.hashed.value),
                    self.check("reprovisionPolicy.migrateDeviceData", False),
                    self.check("reprovisionPolicy.updateHubAssignment", False),
                    self.check("capabilities.iotEdge", False),
                ],
            ).get_output_in_json()["etag"]

            self.cmd(
                self.set_cmd_auth_type(
                    "iot dps registration list -g {} --dps-name {} --enrollment-id {}".format(
                        self.entity_rg, self.entity_dps_name, enrollment_id
                    ),
                    auth_type=auth_phase
                ),
                checks=[self.check("length(@)", 0)],
            )

            cert_name = self.create_random_name("certificate-for-test", length=48)
            cert_etag = self.cmd(
                "iot dps certificate create -g {} --dps-name {} --name {} --p {}".format(
                    self.entity_rg, self.entity_dps_name, cert_name, CERT_PATH
                ),
                checks=[self.check("name", cert_name)],
            ).get_output_in_json()["etag"]

            self.cmd(
                self.set_cmd_auth_type(
                    "iot dps enrollment-group update -g {} --dps-name {} --enrollment-id {}"
                    " --cn {} --etag {} --allocation-policy {} --webhook-url {} --api-version {}".format(
                        self.entity_rg,
                        self.entity_dps_name,
                        enrollment_id,
                        cert_name,
                        etag,
                        AllocationType.custom.value,
                        WEBHOOK_URL,
                        API_VERSION,
                    ),
                    auth_type=auth_phase
                ),
                checks=[
                    self.check("attestation.type", AttestationType.x509.value),
                    self.check("enrollmentGroupId", enrollment_id),
                    self.check("allocationPolicy", "custom"),
                    self.check("customAllocationDefinition.webhookUrl", WEBHOOK_URL),
                    self.check("customAllocationDefinition.apiVersion", API_VERSION),
                    self.check("attestation.x509.caReferences.primary", cert_name),
                    self.check("attestation.x509.caReferences.secondary", None),
                ],
            )

            self.cmd(
                self.set_cmd_auth_type(
                    "iot dps enrollment-group delete -g {} --dps-name {} --enrollment-id {}".format(
                        self.entity_rg, self.entity_dps_name, enrollment_id
                    ),
                    auth_type=auth_phase
                ),
            )

            self.cmd(
                "iot dps certificate delete -g {} --dps-name {} --name {} --etag {}".format(
                    self.entity_rg, self.entity_dps_name, cert_name, cert_etag
                ),
            )

    def test_dps_enrollment_group_symmetrickey_lifecycle(self):
        attestation_type = AttestationType.symmetricKey.value
        for auth_phase in DATAPLANE_AUTH_TYPES:
            enrollment_id, enrollment_id2 = self.generate_enrollment_names(count=2, group=True)
            primary_key = generate_key()
            secondary_key = generate_key()

            etag = self.cmd(
                self.set_cmd_auth_type(
                    "iot dps enrollment-group create --enrollment-id {}"
                    " -g {} --dps-name {} --pk {} --sk {} --provisioning-status {}"
                    " --initial-twin-tags {} --initial-twin-properties {}"
                    " --allocation-policy {} --rp {} --iot-hubs {} --edge-enabled".format(
                        enrollment_id,
                        self.entity_rg,
                        self.entity_dps_name,
                        primary_key,
                        secondary_key,
                        EntityStatusType.enabled.value,
                        '"{generic_dict}"',
                        '"{generic_dict}"',
                        AllocationType.geolatency.value,
                        ReprovisionType.reprovisionandresetdata.value,
                        self.hub_host_name,
                    ),
                    auth_type=auth_phase
                ),
                checks=[
                    self.check("enrollmentGroupId", enrollment_id),
                    self.check("provisioningStatus", EntityStatusType.enabled.value),
                    self.check("allocationPolicy", AllocationType.geolatency.value),
                    self.check("iotHubs", self.hub_host_name.split()),
                    self.check("initialTwin.tags", self.kwargs["generic_dict"]),
                    self.check(
                        "initialTwin.properties.desired", self.kwargs["generic_dict"]
                    ),
                    self.exists("reprovisionPolicy"),
                    self.check("reprovisionPolicy.migrateDeviceData", False),
                    self.check("reprovisionPolicy.updateHubAssignment", True),
                    self.check("capabilities.iotEdge", True),
                ],
            ).get_output_in_json()["etag"]

            self.cmd(
                self.set_cmd_auth_type(
                    "iot dps enrollment-group list -g {} --dps-name {}".format(self.entity_rg, self.entity_dps_name),
                    auth_type=auth_phase
                ),
                checks=[
                    self.check("length(@)", 1),
                    self.check("[0].enrollmentGroupId", enrollment_id),
                ],
            )

            self.cmd(
                self.set_cmd_auth_type(
                    "iot dps enrollment-group show -g {} --dps-name {} --enrollment-id {}".format(
                        self.entity_rg, self.entity_dps_name, enrollment_id
                    ),
                    auth_type=auth_phase
                ),
                checks=[self.check("enrollmentGroupId", enrollment_id)],
            )

            self.cmd(
                self.set_cmd_auth_type(
                    "iot dps enrollment-group update -g {} --dps-name {} --enrollment-id {}"
                    " --provisioning-status {} --etag {} --edge-enabled False"
                    " --allocation-policy {} --webhook-url {} --api-version {}".format(
                        self.entity_rg,
                        self.entity_dps_name,
                        enrollment_id,
                        EntityStatusType.disabled.value,
                        etag,
                        AllocationType.custom.value,
                        WEBHOOK_URL,
                        API_VERSION,
                    ),
                    auth_type=auth_phase
                ),
                checks=[
                    self.check("enrollmentGroupId", enrollment_id),
                    self.check("provisioningStatus", EntityStatusType.disabled.value),
                    self.check("allocationPolicy", "custom"),
                    self.check("customAllocationDefinition.webhookUrl", WEBHOOK_URL),
                    self.check("customAllocationDefinition.apiVersion", API_VERSION),
                    self.check("iotHubs", None),
                    self.exists("initialTwin.tags"),
                    self.exists("initialTwin.properties.desired"),
                    self.check("attestation.symmetricKey.primaryKey", primary_key),
                    self.check("capabilities.iotEdge", False),
                ],
            )

            # Use service generated keys
            etag = self.cmd(
                self.set_cmd_auth_type(
                    "iot dps enrollment-group create -g {} --dps-name {} --enrollment-id {}".format(
                        self.entity_rg, self.entity_dps_name, enrollment_id2
                    ),
                    auth_type=auth_phase
                ),
                checks=[
                    self.check("enrollmentGroupId", enrollment_id2),
                    self.check("attestation.type", attestation_type),
                ],
            ).get_output_in_json()["etag"]

            self.cmd(
                self.set_cmd_auth_type(
                    "iot dps enrollment-group list -g {} --dps-name {}".format(self.entity_rg, self.entity_dps_name),
                    auth_type=auth_phase
                ),
                checks=[
                    self.check("length(@)", 2)
                ],
            )

            self.cmd(
                self.set_cmd_auth_type(
                    "iot dps enrollment-group show -g {} --dps-name {} --enrollment-id {}".format(
                        self.entity_rg, self.entity_dps_name, enrollment_id2
                    ),
                    auth_type=auth_phase
                ),
                checks=[self.check("enrollmentGroupId", enrollment_id2)],
            )

            keys = self.cmd(
                self.set_cmd_auth_type(
                    "iot dps enrollment-group show -g {} --dps-name {} --enrollment-id {} --show-keys".format(
                        self.entity_rg, self.entity_dps_name, enrollment_id2
                    ),
                    auth_type=auth_phase
                ),
                checks=[
                    self.check("enrollmentGroupId", enrollment_id2),
                    self.exists("attestation.symmetricKey"),
                ],
            ).get_output_in_json()["attestation"]["symmetricKey"]

            # Compute Device Key tests
            online_device_key = self.cmd(
                self.set_cmd_auth_type(
                    'az iot dps compute-device-key -g {} --dps-name {} --enrollment-id {} '
                    "--registration-id myarbitrarydeviceId".format(
                        self.entity_rg, self.entity_dps_name, enrollment_id2
                    ),
                    auth_type=auth_phase
                ),
            ).output

            offline_device_key = self.cmd(
                'az iot dps compute-device-key --key "{}" '
                "--registration-id myarbitrarydeviceId".format(keys["primaryKey"])
            ).output
            assert offline_device_key == online_device_key

            # Compute Device Key uses primary key
            offline_device_key = self.cmd(
                'az iot dps compute-device-key --key "{}" '
                "--registration-id myarbitrarydeviceId".format(keys["secondaryKey"])
            ).output
            assert offline_device_key != online_device_key

            etag = self.cmd(
                self.set_cmd_auth_type(
                    "iot dps enrollment-group update -g {} --dps-name {} --enrollment-id {}"
                    " --pk {} --sk {} --etag {}".format(
                        self.entity_rg,
                        self.entity_dps_name,
                        enrollment_id2,
                        keys["secondaryKey"],
                        keys["primaryKey"],
                        etag
                    ),
                    auth_type=auth_phase
                ),
                checks=[
                    self.check("enrollmentGroupId", enrollment_id2),
                    self.check("attestation.type", attestation_type),
                ],
            ).get_output_in_json()["etag"]

            online_device_key = self.cmd(
                self.set_cmd_auth_type(
                    'az iot dps compute-device-key -g {} --dps-name {} --enrollment-id {} '
                    "--registration-id myarbitrarydeviceId".format(
                        self.entity_rg, self.entity_dps_name, enrollment_id2
                    ),
                    auth_type=auth_phase
                ),
            ).output
            assert offline_device_key == online_device_key

            self.cmd(
                self.set_cmd_auth_type(
                    "iot dps enrollment-group delete -g {} --dps-name {} --enrollment-id {}".format(
                        self.entity_rg, self.entity_dps_name, enrollment_id2
                    ),
                    auth_type=auth_phase
                ),
            )

            self.cmd(
                self.set_cmd_auth_type(
                    "iot dps enrollment-group delete -g {} --dps-name {} --enrollment-id {}".format(
                        self.entity_rg, self.entity_dps_name, enrollment_id
                    ),
                    auth_type=auth_phase
                ),
            )

    def test_dps_enrollment_twin_array(self):
        attestation_type = AttestationType.x509.value
        for auth_phase in DATAPLANE_AUTH_TYPES:
            # test twin array in enrollment
            device_id = self.generate_device_names()[0]
            enrollment_id = self.generate_enrollment_names()[0]

            self.cmd(
                self.set_cmd_auth_type(
                    "iot dps enrollment create --enrollment-id {} --attestation-type {}"
                    " -g {} --dps-name {} --cp {} --scp {}"
                    " --provisioning-status {} --device-id {}"
                    " --initial-twin-tags {} --initial-twin-properties {} --device-information {}"
                    " --allocation-policy {} --iot-hubs {}".format(
                        enrollment_id,
                        attestation_type,
                        self.entity_rg,
                        self.entity_dps_name,
                        CERT_PATH,
                        CERT_PATH,
                        EntityStatusType.enabled.value,
                        device_id,
                        '"{generic_dict}"',
                        '"{twin_array_dict}"',
                        '"{generic_dict}"',
                        AllocationType.hashed.value,
                        self.hub_host_name,
                    ),
                    auth_type=auth_phase
                ),
                checks=[
                    self.check("attestation.type", attestation_type),
                    self.check("registrationId", enrollment_id),
                    self.check("provisioningStatus", EntityStatusType.enabled.value),
                    self.check("deviceId", device_id),
                    self.check("allocationPolicy", AllocationType.hashed.value),
                    self.check("iotHubs", self.hub_host_name.split()),
                    self.check("initialTwin.tags", self.kwargs["generic_dict"]),
                    self.check("optionalDeviceInformation", self.kwargs["generic_dict"]),
                    self.check(
                        "initialTwin.properties.desired", self.kwargs["twin_array_dict"]
                    ),
                    self.exists("reprovisionPolicy"),
                    self.check("reprovisionPolicy.migrateDeviceData", True),
                    self.check("reprovisionPolicy.updateHubAssignment", True),
                ],
            )

            self.cmd(
                self.set_cmd_auth_type(
                    "iot dps enrollment delete -g {} --dps-name {} --enrollment-id {}".format(
                        self.entity_rg, self.entity_dps_name, enrollment_id
                    ),
                    auth_type=auth_phase
                ),
            )

            # test twin array in enrollment group
            enrollment_group_id = self.generate_enrollment_names(group=True)[0]

            self.cmd(
                self.set_cmd_auth_type(
                    "iot dps enrollment-group create --enrollment-id {} -g {} --dps-name {}"
                    " --cp {} --scp {} --provisioning-status {} --allocation-policy {}"
                    " --iot-hubs {} --edge-enabled --props {}".format(
                        enrollment_group_id,
                        self.entity_rg,
                        self.entity_dps_name,
                        CERT_PATH,
                        CERT_PATH,
                        EntityStatusType.enabled.value,
                        AllocationType.geolatency.value,
                        self.hub_host_name,
                        '"{twin_array_dict}"',
                    ),
                    auth_type=auth_phase
                ),
                checks=[
                    self.check("enrollmentGroupId", enrollment_group_id),
                    self.check("provisioningStatus", EntityStatusType.enabled.value),
                    self.exists("reprovisionPolicy"),
                    self.check("allocationPolicy", AllocationType.geolatency.value),
                    self.check("iotHubs", self.hub_host_name.split()),
                    self.check(
                        "initialTwin.properties.desired", self.kwargs["twin_array_dict"]
                    ),
                    self.check("reprovisionPolicy.migrateDeviceData", True),
                    self.check("reprovisionPolicy.updateHubAssignment", True),
                    self.check("capabilities.iotEdge", True),
                ],
            )

            self.cmd(
                self.set_cmd_auth_type(
                    "iot dps enrollment-group delete -g {} --dps-name {} --enrollment-id {}".format(
                        self.entity_rg, self.entity_dps_name, enrollment_group_id
                    ),
                    auth_type=auth_phase
                ),
            )
