class ControlContractError(Exception):
    status_code = 500

    def __init__(self, detail: str):
        super().__init__(detail)
        self.detail = detail


class DeviceNotFoundError(ControlContractError):
    status_code = 404


class DeviceStateNotFoundError(ControlContractError):
    status_code = 404


class DeviceMetricNotFoundError(ControlContractError):
    status_code = 404


class DeviceDisabledError(ControlContractError):
    status_code = 409


class DeviceTypeMismatchError(ControlContractError):
    status_code = 400


class DeviceNotConnectedError(ControlContractError):
    status_code = 409


class DeviceCommandNotFoundError(ControlContractError):
    status_code = 404


class EmergencyStoppedError(ControlContractError):
    status_code = 409


class CommandDispatchError(ControlContractError):
    status_code = 500
