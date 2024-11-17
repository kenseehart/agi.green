from datetime import datetime, timezone
import re
import bcrypt
import secrets
from agi_green.agi_db import get_collection
from agi_green.dispatcher import Protocol, protocol_handler

re_session_id = re.compile(r'^[0-9a-f]{8}-([0-9a-f]{4}-){3}[0-9a-f]{12}$')

login_form = '''```form-yaml
id: login
schema:
  h2:
    type: static
    tag: h3
    content: ARIA Login
  user:
    type: text
    label: Screen Name or Email
  password:
    type: text
    inputType: password
    label: Password
  submit:
    type: button
    buttonLabel: Login
    submits: true
```'''

reg_form = '''```form-yaml
id: regform
schema:
  h2:
    type: static
    tag: h3
    content: ARIA Registration
  screen_name:
    type: text
    label: Screen Name
  email:
    type: text
    label: Email
  password:
    type: text
    inputType: password
    label: Password
  confirm:
    type: text
    inputType: password
    label: Confirm Password
  submit:
    type: button
    buttonLabel: Register
    submits: true
```'''

class UserProtocol(Protocol):
    protocol_id = "user"

    def __init__(self, parent:Protocol):
        self.is_authenticated = False
        super().__init__(parent)

    async def create_confirmed_user(self, email: str, screen_name: str, password: str) -> str:
        'create a new user and authenticate them'
        result = await self.create_user(email, screen_name, password)
        if result == 'created':
            # Set email as confirmed
            users_collection = get_collection("users")
            await users_collection.update_one(
                {"email": email}, 
                {"$set": {"email_confirmed": True}}
            )
        return result   

    async def create_user(self, email: str, screen_name: str, password: str) -> str:
        '''create a new user, return status:
        "created": new unconfirmed user created
        "updated": existing unconfirmed user updated
        "exists": not created because of an existing confirmed user with same email or screen_name
        '''
        users_collection = get_collection("users")
        hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
        confirmation_code = secrets.token_urlsafe()
        new_user = {
            "email": email,
            "screen_name": screen_name,
            "password": hashed_password,
            "email_confirmed": False,
            "confirmation_code": confirmation_code,
            "session_id": self.context.session_id,
            "created_at": datetime.utcnow().isoformat(),  # Current timestamp in ISO 8601 format
            "last_login": None,  # You can update this field when the user logs in
            "roles": ["user"],  # This could be useful for role-based access control (RBAC)
            "profile": {
                "avatar_url": None,
                "bio": None,
                "location": None,
            },
            "status": "active"  # Could be "active", "inactive", "suspended", etc.
        }

        # Check for existing users with the same email or screen_name
        existing_user = await users_collection.find_one({
            "$or": [
                {"email": email},
                {"screen_name": screen_name}
            ]
        })

        if existing_user:
            if existing_user['email_confirmed']:
                # If there's an existing confirmed user with the same email or screen_name, raise an error
                return 'exists'
            else:
                # If there's an existing unconfirmed user, replace it with the new unconfirmed user details
                await users_collection.replace_one({
                    "_id": existing_user['_id']
                }, new_user)
                result = 'updated'
        else:
            # If no existing user matches, create a new unconfirmed user document
            await users_collection.insert_one(new_user)
            result = 'created'

        # Common code for sending confirmation email, executed for both new and replaced unconfirmed users
        conf_email = self.config.conf_email.copy()
        conf_email.update(self.config.email)
        sender = conf_email.pop("sender")  # sender must be first arg (as cmd)

        # Send confirmation email
        await self.send('email', sender, recipient=email, to_name=screen_name,
                        code=confirmation_code, email=email, **conf_email)

        self._confirmation_passwd = password # save password for later
        self._confirmation_user = screen_name

        return result

    async def validate_password(self, password: str) -> bool:
        'validate password against password policy'
        if len(password) < 8:
            await self.send('ws', 'append_chat', author='info', content="Password must be at least 8 characters long.")
            return False
        return True

        # TODO: Use an agent to validate password

    @protocol_handler
    async def on_mq_confirm_user(self):
        'user has confirmed email, automatically log in user'

        if hasattr(self, '_confirmation_passwd'):
            await self.send('ws', 'append_chat', author='info', content=f"Email confirmed successfully. Logging in...")
            success = await self.authenticate(self._confirmation_user, self._confirmation_passwd)
            del self._confirmation_passwd

            if success:
                if not self.is_authenticated:
                    self.is_authenticated = True
                    await self.send('user', 'auth', success=True)

            else:
                await self.send('ws', 'append_chat', author='info', content=f"Automatic login failed. Please log in.\n{login_form}")
        else:
            await self.send('ws', 'append_chat', author='info', content=f"Email confirmed successfully. Please log in.\n{login_form}")


    async def authenticate(self, email_or_name: str, password: str) -> bool:
        '''
        authenticate user by email_or_name and password
        return True if authenticated, False otherwise

        Note that this method immediately returns True if the user is already logged in.
        '''
        # if already logged in, return True
        if (email_or_name == self.context.user.screen_name or
            email_or_name == self.context.user.email or
            email_or_name == self.context.user.session_id):

            if not self.is_authenticated:
                self.is_authenticated = success
                await self.send('user', 'auth', success=True)

            return True

        users_collection = get_collection("users")
        sessions_collection = get_collection("sessions")

        if re_session_id.match(email_or_name):
            user = await users_collection.find_one({"session_id": email_or_name})
            if user:
                if not user.get("email_confirmed", False):
                    return False

                # migrate session_id to user_id, removing obsolete session_id
                sessions_collection.update_one({"session_id": email_or_name}, {
                    "$set": {
                        "last_login": datetime.now(timezone.utc).isoformat(),
                        "user_id": user["_id"]
                    },
                    "$inc": {"logins": 1}
                }, upsert=True)
                await self.send('ws', 'append_chat', author='info', content=f'Welcome back {user["screen_name"]}')
                success = True
            else:
                session = await sessions_collection.find_one({"session_id": email_or_name})
                if session:
                    user = await users_collection.find_one({"_id": session["user_id"]})
                    success = True
                    await self.send('ws', 'append_chat', author='info', content=f'Welcome back {user["screen_name"]}')
                else:
                    return False # session_id not found, so return False silently
        else:
            # user can be either email or screen_name
            if "@" in email_or_name:
                user = await users_collection.find_one({"email": email_or_name})
            else:
                user = await users_collection.find_one({"screen_name": email_or_name})

                if user and not user['email_confirmed'] == True:
                    await self.send('ws', 'append_chat', author='info', content="Please confirm your email before logging in.")
                
                return False

            if user and bcrypt.checkpw(password.encode('utf-8'), user["password"]):
                success = True
                await self.send('ws', 'append_chat', author='info', content=f'Login successful. Welcome {user["screen_name"]}')

                # add the session to the session collection
                sessions_collection.update_one({"session_id": self.context.session_id}, {
                    "$set": {
                        "last_login": datetime.now(timezone.utc).isoformat(),
                        "user_id": user["_id"]
                    },
                    "$inc": {"logins": 1}
                }, upsert=True)

            else:
                success = False
                await self.send('ws', 'append_chat', author='info', content="Login failed. Please check your credentials and try again.")

        if success:
            if not self.is_authenticated:
                self.is_authenticated = success
                await self.send('user', 'auth', success=success)

            uc = self.context.user
            uc.is_authenticated = True
            uc._deep_update(user)
            await self.send('ws', 'set_user_data', uid=uc.screen_name, name=uc.screen_name)

        else:
            uc = self.context.user
            uc.is_authenticated = False

        return success

    @protocol_handler
    async def on_ws_connect(self):
        'authenticate using session_id'

        #TODO: user opt-in for this feature (not on shared computers)

        # check if session_id is already logged in
        success = await self.authenticate(self.context.session_id, "")
        if success:
            if not self.is_authenticated:
                self.is_authenticated = True
                await self.send('user', 'auth', success=True)
        else:
            await self.send('ws', 'append_chat', author='info', content=f"Please log in.\n{login_form}")

    @protocol_handler
    async def on_cmd_regform(self) -> str:
        '[cmd:regform()] -> form content'
        return reg_form

    @protocol_handler
    async def on_cmd_login(self) -> str:
        '[cmd:login()] -> form content'

        return login_form

    async def confirm_email(self, email: str, confirmation_code: str) -> bool:
        'user clicked on email confirmation link: check code and confirm email'
        users_collection = get_collection("users")
        user = await users_collection.find_one({"email": email, "confirmation_code": confirmation_code})
        if user:
            await users_collection.update_one({"email": email}, {"$set": {"email_confirmed": True}})
            await self.send('mq', 'confirm_user', channel=f'session.'+user['session_id'])
            return True
        return False

    @protocol_handler
    async def on_form_regform(self, email:str, screen_name:str, password:str, confirm:str) -> bool:
        'ws:register?email={email}&screen_name={screen_name}&password={password}'

        if password != confirm:
            await self.send('ws', 'append_chat', author='info', content="Passwords do not match.")
            return False

        if await self.validate_password(password):
            result = await self.create_user(email, screen_name, password)
            if result == 'created':
                await self.get_protocol('mq').subscribe('user.'+screen_name)
                mesg = f"Thank you. To complete your registration, please check your email ({email}) for a confirmation link. If you can't find it, check your spam folder."
            elif result == 'updated':
                await self.get_protocol('mq').subscribe('user.'+screen_name)
                mesg = f"Registration updated. Please check your email ({email}) for a confirmation link. If you can't find it, check your spam folder."
            else:
                mesg = f"A user with the same email or screen name already exists."

            await self.send('mq', 'chat', channel=f'user.{screen_name}', author='info', content=mesg)

            return result
        else:
            return False

    @protocol_handler
    async def on_http_confirm(self, email:str, code:str) -> str:
        'agi.green/confirm?email={email}&code={code}'
        http = self.get_protocol("http")
        success = await self.confirm_email(email, code)
        if success:
            return 'Registration email confirmed.'
        else:
            return 'Registration email failed.'

    @protocol_handler
    async def on_form_login(self, user:str, password:str) -> bool:
        success = await self.authenticate(user, password)
        if success:
            await self.send('ws', 'set_user_data', uid=self.context.user.screen_name, name=self.context.user.screen_name)
            await self.send('ws', 'append_chat', author='info',
                            message=f'Login successful. Welcome {self.context.user.screen_name}')

            if not self.is_authenticated:
                self.is_authenticated = True
                await self.send('user', 'auth', success=True)

        return success
