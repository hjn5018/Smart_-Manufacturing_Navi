from app.agent.baseAgent import BaseAgent


class AgentService:
    def __init__(self, agent: BaseAgent):
        self.agent = agent

    def generate_plan(self, instruction:str):
        return self.agent.run(instruction)

    def generate_plan_prompt(self, instruction:str, prompt:dict):
        return self.agent.run_prompt(instruction, prompt)
