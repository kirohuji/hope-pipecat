import base64
import mimetypes

from src.bots.summarize import generate_conversation_summary
from src.common.config import DEFAULT_LLM_CONTEXT
from src.common.models import (
    Attachment,
    AttachmentUploadResponse,
    Conversation,
    ConversationCreateModel,
    ConversationModel,
    ConversationUpdateModel,
    Message,
    MessageCreateModel,
    MessageModel,
)
from fastapi import (
    APIRouter,
    BackgroundTasks,
    File,
    HTTPException,
    UploadFile,
    status,
)
from pydantic import ValidationError
from fastapi.responses import StreamingResponse

router = APIRouter(prefix="/conversations")


@router.get("", response_model=list[ConversationModel], name="Get Conversations")
async def get_conversations(
    page: int = 1,
    per_page: int = 10,
    archived: bool = False,
    q: str | None = None,
):
    """
    Retrieve a list of conversations with optional pagination and filtering.

    Args:
        page (int): The page number for pagination. Defaults to 1.
        per_page (int): The number of items per page for pagination. Defaults to 10.
        archived (bool): Filter conversations by archived status. Defaults to False.
        q (str | None): Optional query parameter to search for a conversation by ID.

    Returns:
        list[ConversationModel]: A list of conversation models.

    Raises:
        HTTPException: If the page or per_page is less than 1.
        HTTPException: If a conversation with the specified ID is not found.
    """
    if page < 1:
        raise HTTPException(status_code=400, detail="Page must be greater than 0")
    if per_page < 1:
        raise HTTPException(status_code=400, detail="Per page must be greater than 0")

    if q:
        print(f"Getting conversation by id: {q}")
        conversation = await Conversation.get(q)
        if conversation:
            return [ConversationModel.model_validate(conversation)]
        else:
            raise HTTPException(status_code=404, detail="Conversation not found")

    offset = (page - 1) * per_page
    conversations = await Conversation.find(
        Conversation.archived == archived
    ).sort(-Conversation.updated_at).skip(offset).limit(per_page).to_list()
    return [ConversationModel.model_validate(conv.dict(by_alias=True)) for conv in conversations]


@router.post("", response_model=ConversationModel, status_code=status.HTTP_201_CREATED)
async def create_conversation(conversation: ConversationCreateModel):
    """
    Create a new conversation.

    Args:
        conversation (ConversationCreateModel): The conversation data containing title.

    Returns:
        ConversationModel: The newly created conversation model.
    """
    new_convo = Conversation(title=conversation.title or "New conversation")
    await new_convo.insert()
    if DEFAULT_LLM_CONTEXT:
        for message_data in DEFAULT_LLM_CONTEXT:
            try:
                msg = MessageCreateModel.model_validate(message_data)
                # 自动编号 message_number
                max_msg = await Message.find(Message.conversation_id == new_convo.id).sort(-Message.message_number).first_or_none()
                new_number = (max_msg.message_number if max_msg else 0) + 1
                message_doc = Message(
                    conversation_id=new_convo.id,
                    content=msg.content,
                    message_number=new_number,
                    extra_metadata=msg.extra_metadata,
                )
                await message_doc.insert()
            except ValidationError:
                continue
    return ConversationModel.model_validate(new_convo.dict(by_alias=True))


@router.delete("/{conversation_id}", name="Delete Conversation")
async def delete_conversation(conversation_id: str):
    """
    Delete a conversation by its ID.

    Args:
        conversation_id (str): The unique identifier of the conversation to delete.

    Returns:
        dict: A message confirming successful deletion.

    Raises:
        HTTPException: If the conversation with the specified ID is not found (404).
    """
    conversation = await Conversation.get(conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    await conversation.delete()
    return {"detail": "Conversation deleted successfully"}


@router.put("/{conversation_id}", response_model=ConversationModel, name="Update Conversation")
async def update_conversation(conversation_id: str, conversation_update: ConversationUpdateModel):
    """
    Update a conversation by its ID.

    Args:
        conversation_id (str): The unique identifier of the conversation to update.
        conversation_update (ConversationUpdateModel): The conversation update data.

    Returns:
        ConversationModel: The updated conversation model.

    Raises:
        HTTPException: If the conversation with the specified ID is not found (404).
    """
    conversation = await Conversation.get(conversation_id)
    if not conversation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")
    update_data = conversation_update.model_dump(exclude_unset=True)
    if update_data:
        await Conversation.find_one({"_id": conversation_id}).update({"$set": update_data})
    updated = await Conversation.get(conversation_id)
    return ConversationModel.model_validate(updated.dict(by_alias=True))


@router.get(
    "/{conversation_id}/messages", response_model=dict, name="Get Conversation and Messages"
)
async def get_conversation_messages(
    conversation_id: str,
    background_tasks: BackgroundTasks,
):
    """
    Retrieve a conversation and its associated messages by conversation ID.

    Args:
        conversation_id (str): The unique identifier of the conversation to retrieve.

    Returns:
        dict: A dictionary containing the conversation and a list of its messages.

    Raises:
        HTTPException: If the conversation with the specified ID is not found (404).
    """
    conversation = await Conversation.get(conversation_id)
    if not conversation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")
    messages = await Message.find(Message.conversation_id == conversation_id).sort(Message.message_number).to_list()
    message_count = len(messages)
    # if conversation.title == "New conversation" and message_count > 3:
    #     background_tasks.add_task(generate_conversation_summary, conversation_id, None)
    return {
        "conversation": ConversationModel.model_validate(conversation.dict(by_alias=True)),
        "messages": [MessageModel.model_validate(msg.dict(by_alias=True)) for msg in messages],
    }


@router.post(
    "/{conversation_id}/messages", response_model=MessageModel, status_code=status.HTTP_201_CREATED
)
async def create_message(
    conversation_id: str,
    message: MessageCreateModel,
):
    """
    Create a new message in a specified conversation.

    Args:
        conversation_id (str): The unique identifier of the conversation to add the message to.
        message (MessageCreateModel): The message data containing content and optional metadata.

    Returns:
        MessageModel: The newly created message with all its fields populated.

    Raises:
        HTTPException: If the conversation with the specified ID is not found (404).
    """
    conversation = await Conversation.get(conversation_id)
    if not conversation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")
    max_msg = await Message.find(Message.conversation_id == conversation_id).sort(-Message.message_number).first_or_none()
    new_number = (max_msg.message_number if max_msg else 0) + 1
    new_message = Message(
        conversation_id=conversation_id,
        content=message.content,
        message_number=new_number,
        extra_metadata=message.extra_metadata,
    )
    await new_message.insert()
    return MessageModel.model_validate(new_message.dict(by_alias=True))


@router.post("/upload", response_model=AttachmentUploadResponse)
async def upload_file(file: UploadFile = File(...)):
    """
    Upload a file and create an attachment.

    Args:
        file (UploadFile): The uploaded file.

    Returns:
        AttachmentUploadResponse: The response containing the attachment information.

    Raises:
        HTTPException: If the file is over 20MB.
    """
    try:
        content = await file.read()
        if len(content) > 20 * 1024 * 1024:
            raise HTTPException(status_code=400, detail="File is over 20MB")
        base64_data = base64.b64encode(content).decode("utf-8")
        attachment = Attachment(
            file_data=base64_data,
            file_type=file.content_type or mimetypes.guess_type(file.filename or "")[0],
        )
        await attachment.insert()
        return AttachmentUploadResponse.model_validate(attachment)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
