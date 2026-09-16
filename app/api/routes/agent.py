from fastapi import APIRouter, Depends, HTTPException
from app.agent.device_read_tools import (
    DEVICE_COMMANDS_BY_TYPE,
    DeviceControlToolExecutor,
    DeviceReadToolExecutor,
    READ_DEVICE_TOOLS,
    SEND_DEVICE_COMMAND_TOOL,
)
from app.api.dependent_manager import (
    get_board_connection_service,
    get_intent_service,
    get_llm_client,
    verify_control_api_key,
)
from app.service.agentService import AgentService
from app.domains.capability_management.application.capability_service import CapabilityManagementService
from app.domains.control_contract.infrastructure.conveyor_repository import ConveyorRepository
from app.infra.db.session import get_db
from pydantic import BaseModel, Field

router = APIRouter()


class PlanRequest(BaseModel):
    instruction: str

class PlanPromptRequest(BaseModel):
    instruction: str
    prompt: dict


class ReadChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4_000)


class ReadChatResponse(BaseModel):
    answer: str
    tools_used: list[str]


class ControlChatRequest(ReadChatRequest):
    confirmed: bool = False


class AgentInteractionEventRequest(BaseModel):
    interaction_type: str = Field(min_length=1, max_length=64)
    message: str = Field(min_length=1, max_length=4_000)


READ_ONLY_AGENT_INSTRUCTIONS = """You are PlannerLLM, a read-only device assistant.
Use the provided tools when device data is needed. You may only inspect data;
never claim to have sent a command, changed a device, or accessed a database
directly. State tool errors plainly and keep the final answer concise."""

CONTROL_AGENT_INSTRUCTIONS = """You are PlannerLLM, a device control assistant.
Use read tools to inspect the target device before a command when useful. If the
send_device_command tool is not available, the user has not confirmed the
physical action: state the target command and ask them to repeat the same
request with confirmed=true. When that tool is available, dispatch only the
command explicitly requested by the user. Never claim completion: a SENT result
only confirms that the server handed the command to the active device session."""


def _is_supported_basic_command(message: str) -> bool:
    """Only force a physical tool call for an explicit, basic command."""
    normalized = message.casefold()
    command_terms = (
        "속도", "speed", "정지", "stop", "시작", "start", "전진", "forward",
        "후진", "reverse", "리셋", "reset", "동기화", "sync", "비상", "emergency",
        "색상", "컬러", "color", "복귀", "return", "적재함", "box",
    )
    return any(term in normalized for term in command_terms)


@router.post("/plan")
def plan(req: PlanRequest, service: AgentService = Depends(get_intent_service)):
    return service.generate_plan(req.instruction)

@router.post("/plan-prompt")
def plan_prompt(req: PlanPromptRequest, service: AgentService = Depends(get_intent_service)):
    return service.generate_plan_prompt(req.instruction, req.prompt)


@router.post(
    "/api/agent/read",
    response_model=ReadChatResponse,
    dependencies=[Depends(verify_control_api_key)],
)
def read_agent_chat(
    req: ReadChatRequest,
    db=Depends(get_db),
    control_service=Depends(get_board_connection_service),
):
    """Answer device questions through read-only, allow-listed tools."""
    repository = ConveyorRepository(db)
    executor = DeviceReadToolExecutor(
        control_service=control_service,
        capability_service=CapabilityManagementService(repository),
    )
    interaction = repository.create_agent_interaction("READ_QUESTION", req.message)
    try:
        answer, tools_used = get_llm_client().generate_with_tools(
            user_prompt=req.message,
            system_prompt=READ_ONLY_AGENT_INSTRUCTIONS,
            tools=READ_DEVICE_TOOLS,
            execute_tool=executor.execute,
        )
    except Exception as exc:
        repository.complete_agent_interaction(
            interaction.id, status="FAILED", error_message=str(exc),
        )
        raise
    repository.complete_agent_interaction(
        interaction.id, status="COMPLETED", tools_used=tools_used, response_text=answer,
    )
    return ReadChatResponse(answer=answer, tools_used=tools_used)


@router.post(
    "/api/agent/control",
    response_model=ReadChatResponse,
    dependencies=[Depends(verify_control_api_key)],
)
def control_agent_chat(
    req: ControlChatRequest,
    db=Depends(get_db),
    control_service=Depends(get_board_connection_service),
):
    """Execute one user-confirmed basic command through the tool-calling loop."""
    repository = ConveyorRepository(db)
    executor = DeviceControlToolExecutor(
        control_service=control_service,
        capability_service=CapabilityManagementService(repository),
    )
    if req.confirmed and _is_supported_basic_command(req.message):
        device_catalog = "\n".join(
            f"- device_id={board.id}; name={board.name}; type={board.board_type}; "
            f"allowed_commands={sorted(DEVICE_COMMANDS_BY_TYPE.get(board.board_type, set()))}"
            for board in repository.list_boards()
        )
        system_prompt = f"""{CONTROL_AGENT_INSTRUCTIONS}

The user has already confirmed this physical action. You MUST call
send_device_command exactly once now; do not ask for confirmation again.
Use one of these exact registered device IDs, matching the Korean device name
in the request. For 'AGV', select the board whose type is AGV.
Registered devices:
{device_catalog}"""
        tools = [SEND_DEVICE_COMMAND_TOOL]
        initial_tool_choice = {
            "type": "function",
            "function": {"name": "send_device_command"},
        }
    else:
        system_prompt = CONTROL_AGENT_INSTRUCTIONS
        tools = READ_DEVICE_TOOLS
        initial_tool_choice = "auto"

    interaction = repository.create_agent_interaction(
        "CONTROL_REQUEST", req.message, confirmed=req.confirmed,
    )
    try:
        answer, tools_used = get_llm_client().generate_with_tools(
            user_prompt=req.message,
            system_prompt=system_prompt,
            tools=tools,
            execute_tool=executor.execute,
            initial_tool_choice=initial_tool_choice,
        )
    except Exception as exc:
        repository.complete_agent_interaction(
            interaction.id, status="FAILED", error_message=str(exc),
        )
        raise
    command_ids = [
        result["data"]["command_id"]
        for result in executor.command_results
        if result.get("ok") and result.get("data", {}).get("command_id")
    ]
    repository.complete_agent_interaction(
        interaction.id,
        status="COMMAND_SENT" if command_ids else "COMPLETED",
        tools_used=tools_used,
        command_ids=command_ids,
        response_text=answer,
    )
    return ReadChatResponse(answer=answer, tools_used=tools_used)


@router.post(
    "/api/agent/events",
    dependencies=[Depends(verify_control_api_key)],
)
def record_agent_client_event(
    req: AgentInteractionEventRequest,
    db=Depends(get_db),
):
    """Persist UI-only actions such as confirmation prompts and cancellations."""
    allowed_types = {"CONTROL_CONFIRMATION_REQUESTED", "CONTROL_CANCELLED"}
    if req.interaction_type not in allowed_types:
        raise HTTPException(status_code=422, detail="Unsupported interaction type")
    repository = ConveyorRepository(db)
    interaction = repository.create_agent_interaction(req.interaction_type, req.message)
    repository.complete_agent_interaction(interaction.id, status="COMPLETED")
    return {"id": interaction.id, "status": "COMPLETED"}
