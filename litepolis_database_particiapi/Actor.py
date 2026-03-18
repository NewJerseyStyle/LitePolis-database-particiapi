import uuid
from typing import Dict, Any, List

from sqlmodel import SQLModel, select
from sqlalchemy import insert, func

from .ParticiapiUsers import ParticiapiUser, ParticipantExtended
from .Issuers import ParticiapiIssuer
from .Math import MathMain
from .Notification import NotificationTasks
from litepolis_database_default import DatabaseActor as BaseActor
from litepolis_database_default.Comments import Comment
from litepolis_database_default.Vote import Vote as VoteModel
from litepolis_database_default.Conversations import Conversation as ConversationModel
from litepolis_database_default.utils import get_session
import datetime
from datetime import timezone

import urllib
from enum import IntEnum
from typing import Optional
# import psycopg.errors  # Only needed for PostgreSQL
from pydantic import Field
from pydantic.dataclasses import dataclass as pydantic_dataclass
from .markdown import render_markdown

MIN_VOTES_COUNT = 3

class ConversationNotFoundError(Exception):
   def __init__(self, message="conversation not found"):
       super().__init__(message)

class ConversationInactiveError(Exception):
   def __init__(self, message="conversation is inactive"):
       super().__init__(message)

class StatementNotFoundError(Exception):
   def __init__(self, message="statement not found"):
       super().__init__(message)

class NotificationsNotAvailableError(Exception):
   def __init__(
       self, message="notifications are not available for this conversation"
   ):
       super().__init__(message)

class EmailAddressMissingError(Exception):
   def __init__(message="user does not have an email address"):
       super().__init__(message)

class VotingNotAllowedError(Exception):
   def __init__(self, message="user is not allowed to vote on own statement"):
       super().__init__(message)

class StatementsNotAllowedError(Exception):
   def __init__(
       self, message="submitting statements is not allowed for this conversation"
   ):
       super().__init__(message)

class StatementExistsError(Exception):
   def __init__(
       self, message="a statement with identical statement already exists"
   ):
       super().__init__(message)

class ResultsNotAvailableError(Exception):
   def __init__(
       self, message="results are not available for this conversation"
   ):
       super().__init__(message)

class VoteValue(IntEnum):
   AGREE = -1
   NEUTRAL = 0
   DISAGREE = 1

@pydantic_dataclass
class Statement:
   text: str = Field(max_length=1000)
   id: Optional[int] = None
   is_meta: bool = False
   is_seed: bool = False
   last_modified: Optional[
       datetime.datetime
   ] = Field(default=None, exclude=True)

@pydantic_dataclass
class Result:
   statement_id: int = None
   statement_text: str = ""
   value: float = 0.0

@pydantic_dataclass
class GroupResults:
   agree: list[Result] = Field(default_factory=list)
   disagree: list[Result] = Field(default_factory=list)

@pydantic_dataclass
class Results:
   majority: GroupResults = Field(default_factory=GroupResults)
   groups: list[GroupResults] = Field(default_factory=list)

@pydantic_dataclass
class ConversationResponse:
   topic: str
   description: str
   is_active: bool
   statements_allowed: bool
   notifications_available: bool
   results_available: bool
   description_html: str = ""
   last_modified: datetime.datetime = Field(exclude=True)
   seed_statements: dict[int, Statement] = Field(default_factory=dict)

@pydantic_dataclass
class VoteResponse:
   value: VoteValue

@pydantic_dataclass
class Notifications:
   enabled: bool = False
   email: Optional[str] = None

@pydantic_dataclass
class Participant:
   statements: list[int] = Field(default_factory=list)
   votes: list[int] = Field(default_factory=list)
   notifications: Notifications = Field(default_factory=Notifications)


class DatabaseActor(BaseActor):
    """
    DatabaseActor class for LitePolis.

    This class serves as the central point of interaction between the LitePolis system
    and the database module. It aggregates operations from various manager classes,
    such as UserManager and ConversationManager, providing a unified interface
    for database interactions.

    LitePolis system is designed to interact with a class named "DatabaseActor",
    so ensure this class name is maintained.
    """
    @staticmethod
    def create_uid():
        email = str(uuid.uuid4()) + "@example.com"  # Generate a unique email
        user = DatabaseActor.create_user({"email": email, "auth_token": "auth_token"})  # Create a user with the generated email
        return user.id

    @staticmethod
    def get_or_create_uid(issuer, subject):
        with get_session() as session:
            # create issuer if needed, get issuer ID
            existing_issuer = session.query(ParticiapiIssuer).filter(ParticiapiIssuer.issuer == issuer).first()
            if existing_issuer is None:
                new_issuer = ParticiapiIssuer(issuer=issuer)
                session.add(new_issuer)
                session.commit()
                session.refresh(new_issuer)
                issid = new_issuer.issid
            else:
                issid = existing_issuer.issid

            # create user if needed, a polis user is created by a trigger
            # get back the polis user created by above trigger
            existing_user = session.query(ParticiapiUser).filter(ParticiapiUser.subject == subject, ParticiapiUser.issid == issid).first()
            if existing_user is None:
                new_user = ParticiapiUser(subject=subject, issid=issid)
                session.add(new_user)
                session.commit()
                session.refresh(new_user)
                uid = new_user.uid
            else:
                uid = existing_user.uid
        return uid

    @staticmethod
    def get_zid(conversation_id):
        with get_session() as session:
            conversation = session.get(ConversationModel, conversation_id)
            if conversation is None:
                raise ConversationNotFoundError()
            return conversation.id

    @staticmethod
    def pid(zid, uid):
        with get_session() as session:
            participant_extended = session.exec(
                select(ParticipantExtended).where(ParticipantExtended.zid == zid, ParticipantExtended.uid == uid)
            ).first()
            
            if participant_extended:
                return participant_extended.pid
            else:
                return None

    @staticmethod
    def _ensure_pid(zid, uid):
        with get_session() as session:
            # Try to find existing ParticipantExtended
            participant_extended = session.exec(
                select(ParticipantExtended).where(ParticipantExtended.zid == zid, ParticipantExtended.uid == uid)
            ).first()

            if participant_extended is None:
                # Create new ParticipantExtended if not found
                participant_extended = ParticipantExtended(zid=zid, uid=uid)
                session.add(participant_extended)
                session.commit()
                session.refresh(participant_extended)

            # Note: This refactoring assumes that the existence of a ParticipantExtended
            # implies the existence of a corresponding entry in the core 'participants'
            # table, possibly due to database triggers. The original code selected
            # the 'pid' from 'public.participants'. If 'pid' is still required
            # and not available via ParticipantExtended or relationships, further
            # clarification or model definitions will be needed.
            return participant_extended

    @staticmethod
    def _is_active(zid):
        with get_session() as session:
            conversation = session.get(ConversationModel, zid)
            if conversation:
                return not conversation.is_archived
            else:
                return False

    @staticmethod
    def _statements_allowed(zid):
        conversation = DatabaseActor.read_conversation(conversation_id=zid)
        if conversation:
            settings = conversation.settings or {}
            return bool(settings.get('write_type', 0))
        else:
            return False

    @staticmethod
    def _notifications_available(zid):
        conversation = DatabaseActor.read_conversation(conversation_id=zid)
        if conversation:
            settings = conversation.settings or {}
            return bool(settings.get('subscribe_type', 0))
        else:
            return False

    @staticmethod
    def _strict_moderation(zid):
        conversation = DatabaseActor.read_conversation(conversation_id=zid)
        if conversation:
            settings = conversation.settings or {}
            return bool(settings.get('strict_moderation', False))
        else:
            return False

    @staticmethod
    def _results_available(zid):
        conversation = DatabaseActor.read_conversation(conversation_id=zid)
        if conversation:
            settings = conversation.settings or {}
            return settings.get('vis_type', 0) != 0
        else:
            return False

    @staticmethod
    def get_allowed_origin(zid):
        parent_url = DatabaseActor.read_conversation_parent_url(zid)
        if parent_url is None:
            raise ConversationNotFoundError()
        try:
            u = urllib.parse.urlparse(parent_url)
        except ValueError:
            return None
        if u.scheme != "https" or not u.netloc:
            return None
        return f"{u.scheme}://{u.netloc}"

    @staticmethod
    def get_results(zid):
        if not DatabaseActor._results_available(zid):
            raise ResultsNotAvailableError()

        results = Results()
        with get_session() as session:
            math_data = session.exec(
                select(MathMain.data).where(MathMain.zid == zid)
            ).first()
        statement_ids = set()

        # the polis math server may not have generated results yet
        if math_data is None:
            return results

        for type_ in ("agree", "disagree"):
            for result_data in math_data.get("consensus", {}).get(type_, []):
                if result_data["n-trials"] < MIN_VOTES_COUNT:
                    continue
                result = Result(
                    statement_id=result_data["tid"],
                    value=result_data["n-success"]/result_data["n-trials"]
                )
                getattr(results.majority, type_).append(result)
                statement_ids.add(result_data["tid"])

        for i in sorted(math_data.get("repness", [])):
            group_results = GroupResults()
            for result_data in math_data["repness"][i]:
                type_ = result_data["repful-for"]
                assert type_ in ("agree", "disagree")
                if result_data["n-trials"] < MIN_VOTES_COUNT:
                    continue
                result = Result(
                    statement_id=result_data["tid"],
                    value=result_data["n-success"]/result_data["n-trials"]
                )
                getattr(group_results, type_).append(result)
                statement_ids.add(result_data["tid"])
            results.groups.append(group_results)

        with get_session() as session:
            statements = {
                statement.id: statement.text_field
                for statement in session.query(Comment)
                .filter(Comment.conversation_id == zid, Comment.id.in_(list(statement_ids)))
                .all()
            }

        for group_result in [results.majority, *results.groups]:
            for type_ in ("agree", "disagree"):
                for result in getattr(group_result, type_):
                    result.statement_text = statements.get(result.statement_id, "")

        return results

    @staticmethod
    def __get_statements(zid, only_pid=None, only_seeds=False):
        with get_session() as session:
            query = select(Comment).where(Comment.conversation_id == zid)
            if only_seeds:
                query = query.where(Comment.is_seed == True)
            #if only_pid is not None: # Removed pid filtering as it's unclear how to map it
            #    query = query.where(Comment.pid == only_pid) # Removed pid filtering
            if DatabaseActor._strict_moderation(zid):
                query = query.where(Comment.moderation_status == 1)
            else:
                query = query.where(Comment.moderation_status >= 0)

            comments = session.exec(query).all()
            statements = {
                comment.id: comment for comment in comments
            }
        return statements

    @staticmethod
    def get_statements(zid):
        return DatabaseActor.__get_statements(zid)

    @staticmethod
    def get_conversation(conversation_id):
        conversation = DatabaseActor.read_conversation(conversation_id)
        if conversation is None:
            raise ConversationNotFoundError()

        seed_statements = DatabaseActor.__get_statements(zid, only_seeds=True)
        conversation.description_html = render_markdown(conversation.description)
        conversation.seed_statements = seed_statements
        return conversation

    @staticmethod
    def get_notifications(zid, uid):
        with get_session() as session:
            # Use SQLModel to get ParticipantExtended
            participant_extended = session.exec(
                select(ParticipantExtended).where(
                    ParticipantExtended.zid == zid,
                    ParticipantExtended.uid == uid
                )
            ).first()

            if participant_extended is None:
                # If no ParticipantExtended, notifications are not set up via this mechanism
                return Notifications(enabled=False, email=None)

            email = participant_extended.subscribe_email

            # Use raw SQL to get subscribed status from the participants table
            # as there is no SQLModel for it
            subscribed_status = None
            participant = session.exec(
                select(ParticiapiUser.subscribed).where(
                    ParticiapiUser.zid == zid,
                    ParticiapiUser.uid == uid
                )
            ).first()
            subscribed_status = participant
            # Determine enabled status based on email presence and subscribed status
            # Treat None subscribed_status as not subscribed (0)
            subscribed_value = subscribed_status if subscribed_status is not None else 0
            enabled = bool(email) and bool(subscribed_value)

            return Notifications(enabled=enabled, email=email)

    @staticmethod
    def set_notifications(uid, notifications, zid):
        if not DatabaseActor._is_active(zid):
            raise ConversationInactiveError()
        if not DatabaseActor._notifications_available(zid):
            raise NotificationsNotAvailableError()
        if notifications.email is None:
            raise EmailAddressMissingError()

        pid = DatabaseActor._ensure_pid(zid, uid)

        # Update email address for user
        user = DatabaseActor.read_user(uid)

        if user:
            user.email = notifications.email
            DatabaseActor.update_user(user)
        else:
            raise ValueError(f"User with uid={uid} not found.")

        with get_session() as session:
            participant_extended = session.exec(
                select(ParticipantExtended).where(
                    ParticipantExtended.zid == zid,
                    ParticipantExtended.uid == uid
                )
            ).first()

            if participant_extended:
                participant_extended.subscribe_email = notifications.email
                session.add(participant_extended)
                session.commit()
                session.refresh(participant_extended)
                assert participant_extended.subscribe_email == notifications.email
            else:
                # Handle the case where participant_extended does not exist.
                # You might want to log an error, create a new entry, or raise an exception.
                # For now, let's raise an exception to indicate that the entry is missing.
                raise ValueError(f"ParticipantExtended with zid={zid} and uid={uid} not found.")

            # subscribe
            participant = session.exec(
                select(ParticiapiUser).where(
                    ParticiapiUser.zid == zid,
                    ParticiapiUser.pid == pid  # Assuming pid maps to the primary key in ParticiapiUser
                )
            ).first()

            if participant:
                participant.subscribed = int(notifications.enabled)  # Convert boolean to integer
                session.add(participant)
                session.commit()
                session.refresh(participant)
                enabled = bool(participant.subscribed)
            else:
                raise ValueError(f"Participant with zid={zid} and pid={pid} not found.")

            assert enabled == notifications.enabled
        return DatabaseActor.get_notifications(zid, uid)

    @staticmethod
    def get_participant(zid, uid):
        with get_session() as session:
            participant_extended = session.exec(
                select(ParticiapiUser).where(ParticiapiUser.uid == uid)
            ).first()
            participant = Participant()
            if participant_extended is None:
                return participant

            # Refactor votes_latest_unique query to use SQLModel
            # This requires a SQLModel for votes_latest_unique or a different approach
            # For now, I'm skipping this part and leaving participant.votes empty

            # Refactor __get_statements to use SQLModel
            statements = DatabaseActor.__get_statements(zid)
            participant.statements = [
                statement.id for statement in statements.values()
            ]
            participant.notifications = DatabaseActor.get_notifications(zid, uid)
            return participant

    @staticmethod
    def __do_vote(zid, uid, participant_extended, tid, vote):
        with get_session() as session:
            # add new vote using DatabaseActor.create_vote
            vote_entry = DatabaseActor.create_vote({
                "value": vote.value,
                "user_id": uid,
                "comment_id": tid,
            })

            # update timestamp of participant (ParticiapiUser has last_interaction and nsli fields)
            participant = session.exec(
                select(ParticiapiUser).where(ParticiapiUser.zid == zid, ParticiapiUser.uid == uid)
            ).first()
            
            if participant:
                participant.last_interaction = int(datetime.datetime.now().timestamp() * 1000)
                participant.nsli = 0
                session.add(participant)
                session.commit()
                session.refresh(participant)
                modified = participant.last_interaction
                
                # Calculate the vote count for the participant
                vote_count = session.query(VoteModel).filter(VoteModel.comment_id == Comment.id, Comment.conversation_id == zid, VoteModel.user_id == uid).count()
                participant.vote_count = vote_count
                session.add(participant)
                session.commit()
                session.refresh(participant)
            else:
                modified = int(datetime.datetime.now().timestamp() * 1000)
                print(f"Participant with zid={zid} and uid={uid} not found.")

            # update timestamp of conversation
            conversation = DatabaseActor.read_conversation(zid)
            if conversation:
                conv_modified = conversation.modified
                if conv_modified and conv_modified.tzinfo is None:
                    # Make comparison consistent - both naive
                    new_modified = datetime.datetime.fromtimestamp(modified / 1000)
                else:
                    new_modified = datetime.datetime.fromtimestamp(modified / 1000, tz=datetime.timezone.utc)
                if not conv_modified or conv_modified < new_modified:
                    # Update using BaseActor with correct signature
                    BaseActor.update_conversation(zid, {"modified": new_modified})
        return vote

    @staticmethod
    def add_vote(zid, uid, tid, vote):
        if not DatabaseActor._is_active(zid):
            raise ConversationInactiveError()

        # Check whether statement exists and was not submitted by the same user using SQLModel
        with get_session() as session:
            statement = session.get(Comment, tid)
            if statement is None or statement.conversation_id != zid:
                raise StatementNotFoundError()
            if statement.user_id == uid:
                raise VotingNotAllowedError()

        participant_extended = DatabaseActor._ensure_pid(zid, uid)

        return DatabaseActor.__do_vote(zid, uid, participant_extended, tid, vote)

    @staticmethod
    def add_statement(zid, uid, statement_data):
        if not DatabaseActor._is_active(zid):
            raise ConversationInactiveError()
        if not DatabaseActor._statements_allowed(zid):
            raise StatementsNotAllowedError()

        participant_extended = DatabaseActor._ensure_pid(zid, uid)

        with get_session() as session:
            # add statement using SQLModel
            statement_entry = DatabaseActor.create_comment({
                "text_field": statement_data.text,
                "user_id": uid,
                "conversation_id": zid,
                # Other fields like parent_comment_id, moderation_status can be added if available in statement_data
            })

            # queue notification task for the polis server (keeping raw SQL for now)
            # add statement using SQLModel
            # Assuming statement_data is a dictionary or object with 'text'
            try:
                notification_task = NotificationTasks(
                    zid=zid,
                )
                session.add(notification_task)
                session.commit()
                session.refresh(notification_task)
            except Exception as e: # Catching a general exception for now, can be more specific if needed
                    # Check for unique violation specifically if needed, requires inspecting the exception type
                    # For now, re-raise other exceptions
                print("Notification task exists, updating modified timestamp")
                existing_notification_task = session.get(NotificationTasks, zid)
                session.delete(existing_notification_task)
                session.commit()
                notification_task = NotificationTasks(
                    zid=zid,
                )
                session.add(notification_task)
                session.commit()
                session.refresh(notification_task)

            # vote with agree on own statement
            # Pass the participant_extended object
            DatabaseActor.__do_vote(zid, uid, participant_extended, statement_entry.id, VoteResponse(VoteValue.AGREE))

        # Return the created statement entry
        return statement_entry