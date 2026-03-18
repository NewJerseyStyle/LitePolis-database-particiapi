from litepolis_database_particiapi import DatabaseActor
import pytest


import pytest
from unittest.mock import MagicMock

@pytest.fixture
def mock_render_markdown(mocker):
    # Path to your render_markdown function
    return mocker.patch('litepolis_database_particiapi.render_markdown', return_value="<p>mocked html</p>")

@pytest.fixture
def mock_now_as_millis(mocker):
    # Path to your now_as_millis function
    return mocker.patch('litepolis_database_particiapi.now_as_millis', return_value=1234567890000)

# Make data models and errors available to tests
@pytest.fixture
def M(): # A "module" of test models and errors
    class ModelsAndErrors:
        Statement = Statement
        Conversation = Conversation
        Notifications = Notifications
        Participant = Participant
        Result = Result
        Results = Results
        GroupResults = GroupResults
        Vote = Vote
        VoteValue = VoteValue
        ConversationNotFoundError = ConversationNotFoundError
        ResultsNotAvailableError = ResultsNotAvailableError
        ConversationInactiveError = ConversationInactiveError
        StatementsNotAllowedError = StatementsNotAllowedError
        EmailAddressMissingError = EmailAddressMissingError
        NotificationsNotAvailableError = NotificationsNotAvailableError
        StatementNotFoundError = StatementNotFoundError
        VotingNotAllowedError = VotingNotAllowedError
        StatementExistsError = StatementExistsError
        # Add psycopg errors if you need to mock them specifically
        # For example, if psycopg is imported in litepolis_database_particiapi
        class MockPsycopgError(Exception): pass
        class MockPsycopgUniqueViolation(MockPsycopgError): pass

        psycopg = MagicMock()
        psycopg.Error = MockPsycopgError
        psycopg.errors = MagicMock()
        psycopg.errors.UniqueViolation = MockPsycopgUniqueViolation
    return ModelsAndErrors()


from unittest.mock import patch, ANY
# Assuming DatabaseActor is in 'litepolis_database_particiapi.py'
from litepolis_database_particiapi import DatabaseActor, MIN_VOTES_COUNT

# For psycopg.sql objects if used
# from psycopg import sql


# --- User related tests ---
def test_create_uid_success(mock_db_cursor):
    mock_db_cursor.fetchone.return_value = 123 # Example UID
    assert DatabaseActor.create_uid() == 123
    mock_db_cursor.execute.assert_called_once_with(
        """INSERT INTO public.users VALUES(DEFAULT) RETURNING uid"""
    )

def test_create_uid_db_error(mock_db_cursor, M):
    mock_db_cursor.execute.side_effect = M.psycopg.Error("DB Error")
    with pytest.raises(M.psycopg.Error, match="DB Error"):
        DatabaseActor.create_uid()

def test_get_or_create_uid_new_issuer_new_user(mock_db_cursor):
    mock_db_cursor.fetchone.side_effect = [1, 101] # issid, then uid
    uid = DatabaseActor.get_or_create_uid("new_issuer", "new_subject")
    assert uid == 101
    assert mock_db_cursor.execute.call_count == 3
    # Further assertions on SQL calls as in the original thought process
    # e.g., mock_db_cursor.execute.assert_any_call(expected_sql_for_issuer, {"issuer": "new_issuer"})

# --- Conversation Core (zid, pid, internal flags) ---
def test_get_zid_from_conversation_id_success(mock_db_cursor):
    mock_db_cursor.fetchone.return_value = "test_zid_123"
    zid = DatabaseActor._get_zid_from_conversation_id("conv_abc")
    assert zid == "test_zid_123"
    mock_db_cursor.execute.assert_called_once_with(ANY, {"conversation_id": "conv_abc"})

def test_get_zid_from_conversation_id_not_found(mock_db_cursor, M):
    mock_db_cursor.fetchone.return_value = None
    with pytest.raises(M.ConversationNotFoundError):
        DatabaseActor._get_zid_from_conversation_id("conv_xyz")

@pytest.mark.parametrize("method_to_patch, mock_return_val, expected_result, sql_substring", [
    ("_is_active", True, True, "SELECT is_active"),
    ("_is_active", False, False, "SELECT is_active"),
    ("_statements_allowed", True, True, "SELECT CAST(write_type AS BOOLEAN)"),
    # Add other internal flag methods here
    ("_results_available", True, True, "SELECT vis_type <> 0"),
    ("_strict_moderation", False, False, "SELECT strict_moderation")
])
def test_internal_flag_methods(mock_db_cursor, method_to_patch, mock_return_val, expected_result, sql_substring):
    mock_db_cursor.fetchone.return_value = mock_return_val
    # Get the actual method from DatabaseActor to test
    method = getattr(DatabaseActor, method_to_patch)
    assert method("test_zid") == expected_result
    executed_sql = mock_db_cursor.execute.call_args[0][0]
    assert sql_substring in executed_sql
    assert mock_db_cursor.execute.call_args[1] == {"zid": "test_zid"}


def test_get_allowed_origin_success_https(mock_db_cursor):
    mock_db_cursor.fetchone.return_value = "https://example.com/path"
    assert DatabaseActor.get_allowed_origin("test_zid") == "https://example.com"

def test_get_allowed_origin_parent_url_none_raises_error(mock_db_cursor, M):
    mock_db_cursor.fetchone.return_value = None
    with pytest.raises(M.ConversationNotFoundError): # Assuming ConversationNotFoundError if parent_url is None
        DatabaseActor.get_allowed_origin("test_zid")

# --- Results and Statements ---

# Patch MIN_VOTES_COUNT for this test if it's a module global
@patch('litepolis_database_particiapi.MIN_VOTES_COUNT', 5)
def test_get_results_success_with_data(mock_db_cursor, mock_class_row, M):
    # Mock _results_available if get_results calls it internally
    with patch.object(DatabaseActor, '_results_available', return_value=True):
        math_data = {
            "consensus": {"agree": [{"tid": "s1", "n-trials": 10, "n-success": 8}]},
            "repness": {"0": [{"tid": "s3", "repful-for": "agree", "n-trials": 12, "n-success": 9}]}
        }
        # Side effect for fetchone (math_data) then fetchall (comments)
        mock_db_cursor.fetchone.return_value = math_data
        # Mock for the comments query (assuming class_row is active)
        mock_db_cursor.fetchall.return_value = [
            {"tid": "s1", "txt": "Statement 1 text"},
            {"tid": "s3", "txt": "Statement 3 text"}
        ]

        results_obj = DatabaseActor.get_results("test_zid")

        assert len(results_obj.majority.agree) == 1
        assert results_obj.majority.agree[0].statement_id == "s1"
        assert results_obj.majority.agree[0].value == 0.8
        assert results_obj.majority.agree[0].statement_text == "Statement 1 text"
        # ... other assertions for groups etc. ...
        # Assert that _results_available was called
        DatabaseActor._results_available.assert_called_once_with("test_zid")


def test_get_results_not_available(M):
    with patch.object(DatabaseActor, '_results_available', return_value=False):
        with pytest.raises(M.ResultsNotAvailableError):
            DatabaseActor.get_results("test_zid")

def test_get_statements_base_case(mock_db_cursor, mock_class_row, M):
    # This tests get_statements calling __get_statements
    # __get_statements will call _strict_moderation
    with patch.object(DatabaseActor, '_strict_moderation', return_value=False) as mock_strict_mod:
        # Mock the return of the database query for statements
        # Assuming class_row(Statement) is used
        stmt1_data = {'id': 's1', 'text': 'text1', 'is_meta': False, 'is_seed': False, 'last_modified': 'ts1'}
        stmt2_data = {'id': 's2', 'text': 'text2', 'is_meta': False, 'is_seed': True, 'last_modified': 'ts2'}

        # The cursor.execute in __get_statements will be an iterable
        # If row_factory=class_row(Statement) is used, then execute might yield Statement objects
        # For simplicity, let's assume execute yields dicts and class_row is mocked to handle it
        mock_db_cursor.execute.return_value = [M.Statement(**stmt1_data), M.Statement(**stmt2_data)]

        statements = DatabaseActor.get_statements("test_zid")

        mock_strict_mod.assert_called_once_with("test_zid")
        assert len(statements) == 2
        assert statements['s1'].text == 'text1'
        # Check SQL for "mod >= 0"
        executed_sql_query_obj = mock_db_cursor.execute.call_args[0][0]
        # Convert psycopg.sql object to string for assertion if necessary
        # rendered_sql = executed_sql_query_obj.as_string(mock_db_cursor) # Need a connection for context
        # For now, assume SQL object contains the right components
        # This assertion is a bit tricky without seeing the exact SQL object structure
        assert "mod >= 0" in str(executed_sql_query_obj) # Simple string check


def test_get_conversation_success(mock_db_cursor, mock_class_row, mock_render_markdown, M):
    conv_data = {"topic": "Test Topic", "description": "Test Desc", "is_active": True} # etc.
    seed_stmt_data = {'id': 'seed1', 'text': 'Seed statement'}

    # Mock _strict_moderation because __get_statements (called for seeds) will use it
    with patch.object(DatabaseActor, '_strict_moderation', return_value=False):
        # Side effect for cursor: 1. Conversation data, 2. Seed statements
        # This needs careful handling of how curs.execute().fetchone() and curs.execute() (iterable) are used.
        # If get_conversation makes two separate cursor calls:
        mock_conv_obj = M.Conversation(**conv_data)
        mock_seed_stmt_obj = M.Statement(**seed_stmt_data)

        # Mock the chain of calls for get_conversation
        # 1. Fetch conversation details
        mock_db_cursor.fetchone.return_value = mock_conv_obj # First fetchone call
        # 2. Fetch seed statements (via __get_statements)
        #    The execute inside __get_statements for seeds
        mock_execute_for_seeds = MagicMock(return_value=[mock_seed_stmt_obj])
        # If get_conversation uses the same cursor, this gets complicated.
        # If it gets a new cursor for seeds, then it's simpler.
        # Let's assume get_conversation's structure where `__get_statements` is called.
        # We can patch `__get_statements` directly for simplicity here.
        with patch.object(DatabaseActor, '_DatabaseActor__get_statements', return_value={'seed1': mock_seed_stmt_obj}) as mock_get_priv_stmts:
            conversation = DatabaseActor.get_conversation("test_zid")

            assert conversation.topic == "Test Topic"
            assert conversation.description_html == "<p>mocked html</p>" # From mock_render_markdown
            mock_render_markdown.assert_called_once_with("Test Desc")
            assert 'seed1' in conversation.seed_statements
            mock_get_priv_stmts.assert_called_once_with(zid="test_zid", only_pid=None, only_seeds=True)


# --- Interactions (Notifications, Participant, Votes, Add Statements) ---
def test_set_notifications_success(mock_db_cursor, mock_now_as_millis, M):
    notifications_obj_to_set = M.Notifications(enabled=True, email="new@example.com")
    final_notifications_state = M.Notifications(enabled=True, email="new@example.com") # What get_notifications returns

    # Mock the sequence of internal checks and operations
    with patch.object(DatabaseActor, '_is_active', return_value=True) as mock_is_active, \
         patch.object(DatabaseActor, '_notifications_available', return_value=True) as mock_notif_avail, \
         patch.object(DatabaseActor, '_ensure_pid', return_value="mock_pid") as mock_ensure_pid, \
         patch.object(DatabaseActor, 'get_notifications', return_value=final_notifications_state) as mock_get_notif:

        # Mock the fetchone calls for the three UPDATE statements
        mock_db_cursor.fetchone.side_effect = [
            "new@example.com",  # After UPDATE users
            "new@example.com",  # After UPDATE participants_extended
            True                # After UPDATE participants (subscribed)
        ]

        result = DatabaseActor.set_notifications("test_zid", "user1", notifications_obj_to_set)

        mock_is_active.assert_called_once_with("test_zid")
        mock_notif_avail.assert_called_once_with("test_zid")
        mock_ensure_pid.assert_called_once_with("test_zid", "user1")
        assert mock_db_cursor.execute.call_count == 3 # For the 3 UPDATEs
        # Add assertions for the parameters of each UPDATE call
        mock_get_notif.assert_called_once_with("test_zid", "user1")
        assert result == final_notifications_state

def test_set_notifications_inactive_conversation(M):
    with patch.object(DatabaseActor, '_is_active', return_value=False):
        with pytest.raises(M.ConversationInactiveError):
            DatabaseActor.set_notifications("test_zid", "user1", M.Notifications(email="test@test.com"))

def test_add_vote_success(mock_db_cursor, mock_now_as_millis, M):
    vote_to_add = M.Vote(M.VoteValue.AGREE)
    # Mock internal checks and operations
    with patch.object(DatabaseActor, '_is_active', return_value=True) as mock_is_active, \
         patch.object(DatabaseActor, '_ensure_pid', return_value="mock_pid") as mock_ensure_pid, \
         patch.object(DatabaseActor, '_DatabaseActor__do_vote', return_value=vote_to_add) as mock_do_vote: # Mock the internal __do_vote

        # Mock fetchone for the statement author check
        mock_db_cursor.fetchone.return_value = "author_uid_different_from_user1" # Author check

        result = DatabaseActor.add_vote("test_zid", "user1", "tid1", vote_to_add)

        mock_is_active.assert_called_once_with("test_zid")
        mock_ensure_pid.assert_called_once_with("test_zid", "user1")
        # Assert the statement author check SQL was called
        mock_db_cursor.execute.assert_any_call(ANY, {"tid": "tid1", "zid": "test_zid"})
        mock_do_vote.assert_called_once_with("test_zid", "user1", "mock_pid", "tid1", vote_to_add)
        assert result == vote_to_add

def test_add_vote_on_own_statement(mock_db_cursor, M):
    with patch.object(DatabaseActor, '_is_active', return_value=True), \
         patch.object(DatabaseActor, '_ensure_pid', return_value="mock_pid"):
        mock_db_cursor.fetchone.return_value = "user1" # Statement author is the voter
        with pytest.raises(M.VotingNotAllowedError):
            DatabaseActor.add_vote("test_zid", "user1", "tid1", M.Vote(M.VoteValue.AGREE))


def test_add_statement_success(mock_db_cursor, mock_class_row, mock_now_as_millis, M):
    statement_to_add = M.Statement(text="A new statement")
    returned_statement_obj = M.Statement(id="new_stmt_id", text="A new statement") # After INSERT...RETURNING

    with patch.object(DatabaseActor, '_is_active', return_value=True) as mock_is_active, \
         patch.object(DatabaseActor, '_statements_allowed', return_value=True) as mock_stmts_allowed, \
         patch.object(DatabaseActor, '_ensure_pid', return_value="mock_pid") as mock_ensure_pid, \
         patch.object(DatabaseActor, '_DatabaseActor__do_vote') as mock_do_vote: # To check call to vote on own statement

        # Mock fetchone for the INSERT...RETURNING statement
        mock_db_cursor.fetchone.return_value = returned_statement_obj # Mocking the class_row behavior

        result = DatabaseActor.add_statement("test_zid", "user1", statement_to_add)

        mock_is_active.assert_called_once_with("test_zid")
        mock_stmts_allowed.assert_called_once_with("test_zid")
        mock_ensure_pid.assert_called_once_with("test_zid", "user1")

        # Assert INSERT comments SQL
        insert_comment_call = None
        insert_notification_call = None
        for call_args in mock_db_cursor.execute.call_args_list:
            sql_query = call_args[0][0]
            if "INSERT INTO public.comments" in sql_query:
                insert_comment_call = call_args
            elif "INSERT INTO public.notification_tasks" in sql_query:
                insert_notification_call = call_args

        assert insert_comment_call is not None
        assert insert_comment_call[1] == {
            "zid": "test_zid", "pid": "mock_pid", "uid": "user1", "txt": "A new statement"
        }
        assert insert_notification_call is not None
        assert insert_notification_call[1] == {"zid": "test_zid"}

        # Assert __do_vote was called for agreeing on own statement
        mock_do_vote.assert_called_once()
        args, _ = mock_do_vote.call_args
        assert args[0] == "test_zid"
        assert args[1] == "user1" # uid
        assert args[2] == "mock_pid" # pid
        assert args[3] == "new_stmt_id" # tid of new statement
        assert args[4].value == M.VoteValue.AGREE # Vote object

        assert result == returned_statement_obj

def test_add_statement_exists(mock_db_cursor, M):
     with patch.object(DatabaseActor, '_is_active', return_value=True), \
          patch.object(DatabaseActor, '_statements_allowed', return_value=True), \
          patch.object(DatabaseActor, '_ensure_pid', return_value="mock_pid"):
        # Make the INSERT comments call raise UniqueViolation
        def mock_execute_side_effect(query, params):
            if "INSERT INTO public.comments" in query:
                raise M.psycopg.errors.UniqueViolation("duplicate key")
            return MagicMock() # For other execute calls like notification_tasks

        mock_db_cursor.execute.side_effect = mock_execute_side_effect
        with pytest.raises(M.StatementExistsError):
            DatabaseActor.add_statement("test_zid", "user1", M.Statement(text="Existing text"))