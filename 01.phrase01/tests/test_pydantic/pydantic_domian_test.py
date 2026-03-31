from pydantic import BaseModel, Field
class ToolCall(BaseModel): 
    name: str 
    args: dict = Field(default_factory=dict)
tool = ToolCall(name="123", args={"city": "Beijing"})


class UserConfig(BaseModel):
    usr_id: int
    perferences: list[str]
    temperature: float
config = UserConfig(usr_id=123, perferences=['fff','qw'], temperature=0.32)
print(config.model_dump_json())
print(tool.model_dump_json())