from app.infra.llm.client import LLMClient


class BaseAgent:
    def __init__(self, llm_client:LLMClient):
        self.llm = llm_client

    def run(self, *args, **kwargs):
        raise NotImplementedError

    def run_prompt(self, *args, **kwargs):
        raise NotImplementedError