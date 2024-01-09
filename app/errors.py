MISSING_PARAMETERS = {
    'error_code': 'missing_parameters',
    'message': 'Some parameters are missing from the request.',
}
INVALID_SESSION_ID = {
    'error_code': 'invalid_session_id',
    'message': 'Invalid session ID.',
}
EXPIRED_TOKEN = {
    'error_code': 'expired_token',
    'message': 'Expired token.',
}
INVALID_TOKEN = {
    'error_code': 'invalid_token',
    'message': 'Invalid token.',
}
MISSING_TOKEN = {
    'error_code': 'missing_token',
    'message': 'No token supplied.',
}
INVALID_PARAMETERS = {
    'error_code': 'invalid_parameters',
    'message': 'Some supplied parameters are not valid.',
}
MAX_APPS_REACHED = {
    'error_code': 'max_apps_reached',
    'message': 'Too many apps for current plan.',
}
MAX_ORGANIZATIONS_REACHED = {
    'error_code': 'max_organizations_reached',
    'message': 'Too many organizations for current plan.',
}
MAX_MEMBERS_REACHED = {
    'error_code': 'max_members_reached',
    'message': 'Too many members in this organization for current plan.',
}
ORGANIZATION_NOT_FOUND = {
    'error_code': 'organization_not_found',
    'message': 'The requested organization does not exist.',
}
APP_NOT_FOUND = {
    'error_code': 'app_not_found',
    'message': 'The requested app does not exist.',
}
APP_NOT_RECORDING = {
    'error_code': 'app_not_recording',
    'message': 'The requested app is not recording.',
}
CONFERENCE_NOT_FOUND = {
    'error_code': 'conference_not_found',
    'message': 'The requested conference does not exist.',
}
PARTICIPANT_NOT_FOUND = {
    'error_code': 'participant_not_found',
    'message': 'The requested participant does not exist.',
}
PARTICIPANT_EQUAL_PEER = {
    'error_code': 'participant_equal_peer',
    'message': 'The participant and peer can\'t be the same for an event.',
}
CONNECTION_NOT_FOUND = {
    'error_code': 'connection_not_found',
    'message': 'The requested connection does not exist.',
}
CONNECTION_ENDED = {
    'error_code': 'connection_ended',
    'message': 'This connection has ended and we are no longer listening for events.',
}
TRACK_NOT_FOUND = {
    'error_code': 'track_not_found',
    'message': 'The requested track does not exist.',
}
ISSUE_NOT_FOUND = {
    'error_code': 'issue_not_found',
    'message': 'The requested issue does not exist.',
}
SUBSCRIPTION_NOT_FOUND = {
    'error_code': 'subscription_not_found',
    'message': 'The requested subscription does not exist.',
}
PLAN_NOT_FOUND = {
    'error_code': 'plan_not_found',
    'message': 'The requested plan does not exist.',
}
INVALID_API_KEY = {
    'error_code': 'invalid_api_key',
    'message': 'Invalid api key.',
}
USER_NOT_OWNER = {
    'error_code': 'user_not_owner',
    'message': 'The user is not the owner of the organization.',
}
USER_NOT_FOUND = {
    'error_code': 'user_not_found',
    'message': 'We could not find this user.',
}
QUOTA_EXCEEDED = {
    'error_code': 'quota_exceeded',
    'message': 'Quota exceeded.',
}
USER_ALREADY_MEMBER = {
    'error_code': 'user_already_member',
    'message': 'User already member.',
}
INVALID_META = {
    'error_code': 'invalid_meta',
    'message': 'Invalid meta.',
}
INVALID_EMAIL = {
    'error_code': 'invalid_email',
    'message': 'Invalid email.',
}
DOMAIN_NOT_ALLOWED = {
    'error_code': 'domain_not_allowed',
    'message': 'The app does not allow this domain.',
}
METHOD_NOT_ALLOWED = {
    'error_code': 'method_not_allowed',
    'message': 'Method not allowed.',
}
UNKNOWN_ERROR = {
    'error_code': 'unknown_error',
    'message': '',
}


class PMError(Exception):
    """
    Class used for exceptions.
    """
    def __init__(self, status=500, app_error=None):
        self.status = status
        self.app_error = app_error or UNKNOWN_ERROR
