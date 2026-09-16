import unittest
from types import SimpleNamespace

from app.agent.device_read_tools import DeviceControlToolExecutor, DeviceReadToolExecutor


class FakeRepository:
    def list_boards(self):
        return [
            SimpleNamespace(
                id="straight-01",
                board_type="STRAIGHT_CONVEYOR",
                name="Straight conveyor",
                enabled=True,
            )
        ]

    def find_board(self, device_id):
        return next((board for board in self.list_boards() if board.id == device_id), None)


class FakeControlService:
    repository = FakeRepository()

    def get_status(self, device_id):
        if device_id != "straight-01":
            raise ValueError("Device not found")
        return {"board_id": device_id, "connected": True, "running": False}

    def get_diagnostics(self, device_id):
        return {"board_id": device_id, "ready": True, "checks": {"board_exists": True}}

    async def dispatch_command(self, device_id, command, payload):
        return {"command_id": "cmd-test", "board_id": device_id, "command": command, "status": "SENT"}


class FakeCapabilityService:
    def list_capabilities(self, device_id):
        return [
            SimpleNamespace(
                capability_code="COLOR_CLASSIFICATION",
                enabled=True,
                commands_json=["SORT_COLOR"],
                payload_schema_json={"required": ["color"]},
            )
        ]


class DeviceReadToolExecutorTests(unittest.TestCase):
    def setUp(self):
        self.executor = DeviceReadToolExecutor(FakeControlService(), FakeCapabilityService())

    def test_list_devices_returns_only_safe_device_fields(self):
        result = self.executor.execute("list_devices", "{}")

        self.assertTrue(result["ok"])
        self.assertEqual(result["data"][0]["device_id"], "straight-01")
        self.assertNotIn("DATABASE_URL", str(result))

    def test_state_tool_parses_json_arguments(self):
        result = self.executor.execute("get_device_state", '{"device_id":"straight-01"}')

        self.assertEqual(result, {
            "ok": True,
            "data": {"board_id": "straight-01", "connected": True, "running": False},
        })

    def test_write_or_unknown_tools_are_rejected(self):
        result = self.executor.execute("send_device_command", '{"device_id":"straight-01"}')

        self.assertFalse(result["ok"])
        self.assertIn("unsupported read tool", result["error"])

    def test_control_tool_dispatches_valid_confirmed_command(self):
        executor = DeviceControlToolExecutor(FakeControlService(), FakeCapabilityService())
        result = executor.execute(
            "send_device_command",
            '{"device_id":"straight-01","command":"SET_SPEED","payload":{"speed":80}}',
        )

        self.assertTrue(result["ok"])
        self.assertEqual(result["data"]["command"], "SET_SPEED")

    def test_control_tool_rejects_invalid_speed(self):
        executor = DeviceControlToolExecutor(FakeControlService(), FakeCapabilityService())
        result = executor.execute(
            "send_device_command",
            '{"device_id":"straight-01","command":"SET_SPEED","payload":{"speed":999}}',
        )

        self.assertFalse(result["ok"])
        self.assertIn("speed between 0 and 255", result["error"])


if __name__ == "__main__":
    unittest.main()
