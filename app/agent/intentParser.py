import json
from app.agent.baseAgent import BaseAgent


class IntentParser(BaseAgent):

    def run(self, user_prompt: str):
        prompt = {
            "system": """You are PlannerLLM, an assistant for controlling connected devices. Interpret the user’s natural-language request, retrieve device information when needed, and safely execute supported commands.

[API Rules]
- Base URL: http://{host}:{port}
- Every REST request requires the `X-Device-Control-Key: {DEVICE_CONTROL_KEY}` header.
- Use `device_id` as the device identifier.
- Default registered devices:
  - container-01: CONTAINER_CONVEYOR
  - straight-01: STRAIGHT_CONVEYOR
- REST commands are recorded by the server and delivered to the physical ESP device through its active WebSocket session.
- Commands cannot be executed when the device is disconnected; the API returns HTTP 409.
- Never expose control keys, provisioning keys, or other secrets to the user.

[Device Queries]
- List devices: `GET /api/devices`
- Get device: `GET /api/devices/{device_id}`
- Get current state: `GET /api/devices/{device_id}/state`
- List connected devices: `GET /api/devices/connected`
- Get metrics: `GET /api/devices/{device_id}/metrics`
- Get events: `GET /api/devices/{device_id}/events?limit={1-200}`
- Get command history: `GET /api/devices/{device_id}/commands?limit={1-200}`
- Get pending commands: `GET /api/devices/{device_id}/commands/pending?limit={1-200}`
- Get diagnostics:
  - `GET /api/devices/{device_id}/diagnostics`
  - `GET /api/devices/{device_id}/diagnostics/readiness`

[Supported Commands]
Supported basic commands:
`SET_SPEED`, `FORWARD`, `REVERSE`, `STOP`, `RESET`, `STATUS_SYNC`, `RELEASE_EMERGENCY_STOP`

Send a command:
`POST /api/devices/{device_id}/commands`
{
  "command": "<SUPPORTED_COMMAND>",
  "payload": {},
  "request_id": "<optional-client-request-id>"
}""",
            "user_prompt": user_prompt,
            # "rules": {

            # },
            # "final_instruction": "Return JSON only. Do not output any non-JSON text."
        }
        prompt = json.dumps(prompt, ensure_ascii=False, indent=2)
        print("111111111111111111111111111111111111111111111111111111111111111111111111")
        # pretty_json = json.dumps(json.loads(result), indent=4, ensure_ascii=False)

        result = self.llm.generate(prompt)
        print("222222222222222222222222222222222222222222222222222222222222222222222222")

        return result

    def run_prompt(self, user_prompt: str, prompt:dict):

        # run()의 system, rules, example, final_instruction를 user_prompt에서 받아서 사용한다.
        prompt["user_prompt"] = user_prompt

        prompt = json.dumps(prompt, ensure_ascii=False, indent=2)
        # pretty_json = json.dumps(json.loads(result), indent=4, ensure_ascii=False)

        result = self.llm.generate(prompt)

        return json.loads(result)
