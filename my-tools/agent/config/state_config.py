from typing import Annotated, Required, TypedDict
from deepagents._messages_reducer import _messages_delta_reducer
from langgraph.channels.delta import DeltaChannel
from langchain_core.messages import AnyMessage

class MessagesState(TypedDict):
    messages: Required[Annotated[list[AnyMessage], DeltaChannel(_messages_delta_reducer, snapshot_frequency=50)]]