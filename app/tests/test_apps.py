import datetime
import json
import uuid

from ..errors import (APP_NOT_FOUND, INVALID_PARAMETERS, MAX_APPS_REACHED, MISSING_PARAMETERS,
                      ORGANIZATION_NOT_FOUND, UNKNOWN_ERROR, USER_NOT_OWNER)
from ..models.app import App
from ..models.organization import Organization
from ..models.subscription import Subscription
from ..models.user import User
from ..utils import JSONHttpResponse, serialize
from .classes import PMTestCase
from ..billing import Billing


class AppsViewTestCase(PMTestCase):

    def test_update_duration_days(self):
        app = App(
            api_key='dada5da75a944da6a0fed919cc21d13c',
            organization=self.org,
            name='test app 2',
            recording=False,
        )

        app.save()

        self.assertEqual(app.durations_days, {})

        app = App.get(id=app.id)
        self.assertEqual(len(app.durations_days.keys()), Billing.get_data_retention_days(app.owner))
        today = datetime.datetime.utcnow().date()
        for key in app.durations_days.keys():
            self.assertEqual(key, str(today))
            today = today - datetime.timedelta(days=1)

    def test_post_no_data(self):

        user_password = 'amalgam'
        user = User.objects.create_user(
            username='Ionel1234',
            password=user_password,
            is_verified=True,
        )

        self.assertTrue(self.client.login(username=user.username, password=user_password))

        response = self.client.post(
            path='/v1/apps',
            data={},
        )

        self.client.logout()

        self.assertTrue(isinstance(response, JSONHttpResponse))
        self.assertEqual(response.status_code, 400)
        self.assertEqual(json.loads(response.content), UNKNOWN_ERROR)

    def test_post_invalid_organiation_id_or_not_found(self):

        user_password = 'amalgam'
        user = User.objects.create_user(
            username='Ionel1234',
            password=user_password,
            is_verified=True,
        )

        self.assertTrue(self.client.login(username=user.username, password=user_password))

        ids = [
            'ceva',
            '1',
            uuid.uuid4(),
            123,
            json.dumps({1: 4}),
        ]

        for organization_id in ids:
            response = self.client.post(
                path='/v1/apps',
                data={
                    'organization': organization_id,
                },
                content_type='application/json',
            )

            self.assertTrue(isinstance(response, JSONHttpResponse))
            self.assertEqual(response.status_code, 400)
            self.assertEqual(json.loads(response.content), ORGANIZATION_NOT_FOUND)

        self.client.logout()

    def test_post_user_not_org_owner(self):

        user_password = 'amalgam'
        user = User.objects.create_user(
            username='Ionel1234',
            password=user_password,
            is_verified=True,
        )

        self.assertTrue(self.client.login(username=user.username, password=user_password))

        response = self.client.post(
            path='/v1/apps',
            data={
                'organization': str(self.org.id),
            },
            content_type='application/json',
        )

        self.assertTrue(isinstance(response, JSONHttpResponse))
        self.assertEqual(response.status_code, 400)
        self.assertEqual(json.loads(response.content), ORGANIZATION_NOT_FOUND)

        self.client.logout()

    def test_post_max_apps_reached(self):

        user_password = 'amalgam'
        user = User.objects.create_user(
            username='Ionel1234',
            password=user_password,
            is_verified=True,
        )

        org = Organization(
            owner=user,
            name='test org 2'
        )
        org.save()
        self.create_subscription(user)

        for _ in range(Billing.get_user_plan(user)['max_apps']):
            App(
                api_key=str(uuid.uuid4()).replace('-', ''),
                organization=org,
                name=str(uuid.uuid4()).replace('-', ''),
                domain='ceva.altceva',
                recording=True,
            ).save()

        self.assertTrue(self.client.login(username=user.username, password=user_password))

        response = self.client.post(
            path='/v1/apps',
            data={
                'organization': str(org.id),
            },
            content_type='application/json',
        )

        self.assertTrue(isinstance(response, JSONHttpResponse))
        self.assertEqual(response.status_code, 400)
        self.assertEqual(json.loads(response.content), MAX_APPS_REACHED)

        self.client.logout()

    def test_post_invalid_app_params(self):
        user_password = 'amalgam'
        user = User.objects.create_user(
            username='Ionel1234',
            password=user_password,
            is_verified=True,
        )

        org = Organization(
            owner=user,
            name='test org 2'
        )
        org.save()
        self.create_subscription(user)

        self.assertTrue(self.client.login(username=user.username, password=user_password))

        inputs = (
            ('', '', '', '',),
            ('', 'domain', 10, True,),
            ('name', 257 * 'y', 30, True,),
            (129 * 'r', 'domain', 32, True,),
        )
        for inp in inputs:
            response = self.client.post(
                path='/v1/apps',
                data={
                    'organization': str(org.id),
                    'name': inp[0],
                    'domain': inp[1],
                    'interval': inp[2],
                    'recording': inp[3],
                },
                content_type='application/json',
            )

            self.assertTrue(isinstance(response, JSONHttpResponse))
            self.assertEqual(response.status_code, 400)
            self.assertEqual(json.loads(response.content), INVALID_PARAMETERS)

        self.client.logout()

    def test_post_200(self):
        user_password = 'amalgam'
        user = User.objects.create_user(
            username='Ionel1234',
            password=user_password,
            is_verified=True,
        )

        org = Organization(
            owner=user,
            name='test org 2'
        )
        org.save()
        self.create_subscription(user)

        self.assertTrue(self.client.login(username=user.username, password=user_password))

        app_name = 'name'
        app_domain = 'appdomain.domain'
        app_interval = 33
        app_recording = False

        response = self.client.post(
            path='/v1/apps',
            data={
                'organization': str(org.id),
                'name': app_name,
                'domain': app_domain,
                'interval': app_interval,
                'recording': app_recording,
            },
            content_type='application/json',
        )

        self.assertTrue(isinstance(response, JSONHttpResponse))
        self.assertEqual(response.status_code, 200)

        response_body = json.loads(response.content.decode('utf-8'))

        app_id = response_body['data']['id']
        app_api_key = response_body['data']['api_key']

        created_app = App.objects.get(id=app_id)

        self.assertEqual(created_app.organization, org)
        self.assertEqual(created_app.name, app_name)
        self.assertEqual(created_app.domain, app_domain)
        self.assertEqual(created_app.interval, app_interval)
        self.assertEqual(created_app.recording, app_recording)
        self.assertEqual(created_app.api_key, app_api_key)

        self.assertEqual(
            json.loads(response.content.decode('utf-8')),
            serialize(
                [created_app],
                return_single_object=True,
            ),
        )

        self.client.logout()

    def test_put_no_app(self):

        user_password = 'amalgam'
        user = User.objects.create_user(
            username='Ionel1234',
            password=user_password,
            is_verified=True,
        )

        self.assertTrue(self.client.login(username=user.username, password=user_password))

        response = self.client.put(
            path='/v1/apps/{}'.format(str(uuid.uuid4())),
            data={},
        )

        self.assertTrue(isinstance(response, JSONHttpResponse))
        self.assertEqual(response.status_code, 400)
        self.assertEqual(json.loads(response.content), APP_NOT_FOUND)

    def test_put_invalid_body(self):

        self.assertTrue(self.client.login(username=self.user.username, password=self.user_password))

        response = self.client.put(
            path='/v1/apps/{}'.format(str(self.app_recording.id)),
            data={
                'name': self.app_recording.name,
                'domain': self.app_recording.domain,
                'interval': self.app_recording.interval,
                'recording': self.app_recording.recording,
            }
        )

        self.client.logout()

        self.assertTrue(isinstance(response, JSONHttpResponse))
        self.assertEqual(response.status_code, 400)
        self.assertEqual(json.loads(response.content), UNKNOWN_ERROR)

    def test_put_200_no_change(self):

        self.assertTrue(self.client.login(username=self.user.username, password=self.user_password))

        response = self.client.put(
            path='/v1/apps/{}'.format(str(self.app_recording.id)),
            data={
                'name': self.app_recording.name,
                'domain': self.app_recording.domain,
                'interval': self.app_recording.interval,
                'recording': self.app_recording.recording,
            },
            content_type='application/json',
        )

        self.client.logout()

        self.assertTrue(isinstance(response, JSONHttpResponse))
        self.assertEqual(response.status_code, 200)

        self.app_recording.refresh_from_db()

        self.assertEqual(
            json.loads(response.content.decode('utf-8')),
            serialize(
                [self.app_recording],
                return_single_object=True,
            ),
        )

    def test_put_200_change(self):

        self.assertTrue(self.client.login(username=self.user.username, password=self.user_password))

        new_name = 'new_name'
        new_domain = 'new_domain.domain'
        new_interval = 41
        new_recording = False

        response = self.client.put(
            path='/v1/apps/{}'.format(str(self.app_recording.id)),
            data={
                'name': new_name,
                'domain': new_domain,
                'interval': new_interval,
                'recording': new_recording,
            },
            content_type='application/json',
        )

        self.client.logout()

        self.assertTrue(isinstance(response, JSONHttpResponse))
        self.assertEqual(response.status_code, 200)

        response_body = json.loads(response.content.decode('utf-8'))

        self.assertEqual(response_body['data']['name'], new_name)
        self.assertEqual(response_body['data']['domain'], new_domain)
        self.assertEqual(response_body['data']['interval'], new_interval)
        self.assertEqual(response_body['data']['recording'], new_recording)

        self.assertEqual(
            json.loads(response.content.decode('utf-8')),
            serialize(
                App.filter(id=self.app_recording.id),
                return_single_object=True,
            ),
        )

    def test_put_invalid_app_params(self):

        self.assertTrue(self.client.login(username=self.user.username, password=self.user_password))

        inputs = (
            ('1', '1', '', '',),
            ('', 'domain', 10, True,),
            ('name', 257 * 'y', 30, True,),
            (129 * 'r', 'domain', 32, True,),
            ('r', 'domain', 32, True,),
        )

        for inp in inputs:
            response = self.client.put(
                path='/v1/apps/{}'.format(str(self.app_recording.id)),
                data={
                    'name': inp[0],
                    'domain': inp[1],
                    'interval': inp[2],
                    'recording': inp[3],
                },
                content_type='application/json',
            )

            self.assertTrue(isinstance(response, JSONHttpResponse))
            self.assertEqual(response.status_code, 400)
            self.assertEqual(json.loads(response.content), INVALID_PARAMETERS)

        self.client.logout()

    def test_get_no_app(self):
        self.assertTrue(self.client.login(username=self.user.username, password=self.user_password))

        response = self.client.get(
            path='/v1/apps/{}'.format(str(uuid.uuid4())),
        )

        self.client.logout()

        self.assertTrue(isinstance(response, JSONHttpResponse))
        self.assertEqual(response.status_code, 400)
        self.assertEqual(json.loads(response.content), APP_NOT_FOUND)

    def test_get_user_not_org(self):
        user_password = 'amalgam'
        user = User.objects.create_user(
            username='Ionel1234',
            password=user_password,
            is_verified=True,
        )

        self.assertTrue(self.client.login(username=user.username, password=user_password))

        response = self.client.get(
            path='/v1/apps/{}'.format(str(self.app_recording.id)),
        )

        self.client.logout()

        self.assertTrue(isinstance(response, JSONHttpResponse))
        self.assertEqual(response.status_code, 400)
        self.assertEqual(json.loads(response.content), APP_NOT_FOUND)

    def test_get_200(self):
        self.assertTrue(self.client.login(username=self.user.username, password=self.user_password))

        response = self.client.get(
            path='/v1/apps/{}'.format(str(self.app_recording.id)),
        )

        self.client.logout()

        self.assertTrue(isinstance(response, JSONHttpResponse))
        self.assertEqual(response.status_code, 200)

        self.app_recording.refresh_from_db()

        self.assertEqual(
            json.loads(response.content.decode('utf-8')),
            serialize(
                [self.app_recording],
                return_single_object=True,
            ),
        )

    def test_filter_user_not_org(self):
        user_password = 'amalgam'
        user = User.objects.create_user(
            username='Ionel1234',
            password=user_password,
            is_verified=True,
        )

        self.assertTrue(self.client.login(username=user.username, password=user_password))

        response = self.client.get(
            path='/v1/apps',
        )

        self.client.logout()

        self.assertTrue(isinstance(response, JSONHttpResponse))
        self.assertEqual(response.status_code, 200)

        response_body = json.loads(response.content.decode('utf-8'))
        self.assertEqual(response_body['data'], [])

    def test_filter_200(self):
        self.assertTrue(self.client.login(username=self.user.username, password=self.user_password))

        response = self.client.get(
            path='/v1/apps',
        )

        self.client.logout()

        self.assertTrue(isinstance(response, JSONHttpResponse))
        self.assertEqual(response.status_code, 200)

        self.app_recording.refresh_from_db()
        self.app_not_recording.refresh_from_db()

        apps = [self.app_recording, self.app_not_recording]

        self.assertEqual(
            json.loads(response.content.decode('utf-8')),
            serialize(apps),
        )

    def test_delete_no_pk(self):
        self.assertTrue(self.client.login(username=self.user.username, password=self.user_password))

        response = self.client.delete(
            path='/v1/apps',
        )

        self.client.logout()

        self.assertTrue(isinstance(response, JSONHttpResponse))
        self.assertEqual(response.status_code, 400)
        self.assertEqual(json.loads(response.content), MISSING_PARAMETERS)

    def test_delete_no_app(self):
        self.assertTrue(self.client.login(username=self.user.username, password=self.user_password))

        response = self.client.delete(
            path='/v1/apps/{}'.format(str(uuid.uuid4())),
        )

        self.client.logout()

        self.assertTrue(isinstance(response, JSONHttpResponse))
        self.assertEqual(response.status_code, 400)
        self.assertEqual(json.loads(response.content), APP_NOT_FOUND)

    def test_delete_user_not_in_org(self):
        user_password = 'amalgam'
        user = User.objects.create_user(
            username='Ionel1234',
            password=user_password,
            is_verified=True,
        )

        self.assertTrue(self.client.login(username=user.username, password=user_password))

        response = self.client.delete(
            path='/v1/apps/{}'.format(str(self.app_recording.id)),
        )

        self.client.logout()

        self.assertTrue(isinstance(response, JSONHttpResponse))
        self.assertEqual(response.status_code, 400)
        self.assertEqual(json.loads(response.content), APP_NOT_FOUND)

    def test_delete_not_owner(self):
        user_password = 'amalgam'
        user = User.objects.create_user(
            username='Ionel1234',
            password=user_password,
            is_verified=True,
        )

        user2_password = 'amalgam2'
        user2 = User.objects.create_user(
            username='Ionel12342',
            password=user2_password,
            is_verified=True,
        )
        self.create_subscription(user)
        self.create_subscription(user2)

        org = Organization(
            name='testdelete',
            owner=user,
        )

        org.members.add(user)
        org.members.add(user2)

        org.save()

        app = App(
            api_key='recb5da75a944duns0fed919cc21d13c',
            organization=org,
            name='test app 2',
            domain='l.longer',
            recording=True,
        )

        app.save()

        self.assertTrue(self.client.login(username=user2.username, password=user2_password))

        response = self.client.delete(
            path='/v1/apps/{}'.format(str(app.id)),
        )

        self.client.logout()

        self.assertTrue(isinstance(response, JSONHttpResponse))
        self.assertEqual(response.status_code, 403)
        self.assertEqual(json.loads(response.content), USER_NOT_OWNER)

    def test_delete_200(self):
        user_password = 'amalgam'
        user = User.objects.create_user(
            username='Ionel1234',
            password=user_password,
            is_verified=True,
        )

        user2_password = 'amalgam2'
        user2 = User.objects.create_user(
            username='Ionel12342',
            password=user2_password,
            is_verified=True,
        )

        self.create_subscription(user)
        self.create_subscription(user2)

        org = Organization(
            name='testdelete',
            owner=user,
        )

        org.members.add(user)
        org.members.add(user2)

        org.save()

        app = App(
            api_key='recb5da75a944duns0fed919cc21d13c',
            organization=org,
            name='test app 2',
            domain='l.longer',
            recording=True,
        )

        app.save()

        self.assertTrue(self.client.login(username=user.username, password=user_password))

        response = self.client.delete(
            path='/v1/apps/{}'.format(str(app.id)),
        )

        self.client.logout()

        self.assertTrue(isinstance(response, JSONHttpResponse))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(json.loads(response.content), '')

        inactive_app = App.objects.get(id=app.id)

        self.assertEqual(inactive_app.is_active, False)
