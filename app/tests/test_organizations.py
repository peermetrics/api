import datetime
import json
import uuid

import mock
from django.db import models

from ..errors import (INVALID_PARAMETERS, MAX_ORGANIZATIONS_REACHED, MISSING_PARAMETERS,
                      ORGANIZATION_NOT_FOUND, UNKNOWN_ERROR, USER_NOT_OWNER)
from ..models.organization import Organization
from ..models.subscription import Subscription
from ..models.user import User
from ..utils import JSONHttpResponse, serialize
from .classes import PMTestCase
from ..billing import Billing


class OrganizationsViewTestCase(PMTestCase):

    def test_post_no_data(self):

        user_password = 'amalgam'
        user = User.objects.create_user(
            username='Ionel1234',
            password=user_password,
            is_verified=True,
        )

        self.assertTrue(self.client.login(username=user.username, password=user_password))

        response = self.client.post(
            path='/v1/organizations',
            data={},
        )

        self.client.logout()

        self.assertTrue(isinstance(response, JSONHttpResponse))
        self.assertEqual(response.status_code, 400)
        self.assertEqual(json.loads(response.content), UNKNOWN_ERROR)


    def test_post_max_orgs_reached(self):

        user_password = 'amalgam'
        user = User.objects.create_user(
            username='Ionel1234',
            password=user_password,
            is_verified=True,
        )
        self.create_subscription(user)

        for i in range(Billing.get_user_plan(user)['max_organizations']):
            org = Organization(
                owner=user,
                name='test org {}'.format(i),
            )
            org.members.add(user)
            org.save()

        self.assertTrue(self.client.login(username=user.username, password=user_password))

        response = self.client.post(
            path='/v1/organizations',
            data={
                'name': 'name',
            },
            content_type='application/json',
        )

        self.assertTrue(isinstance(response, JSONHttpResponse))
        self.assertEqual(response.status_code, 400)
        self.assertEqual(json.loads(response.content), MAX_ORGANIZATIONS_REACHED)

        self.client.logout()

    def test_post_invalid_arguments(self):

        user_password = 'amalgam'
        user = User.objects.create_user(
            username='Ionel1234',
            password=user_password,
            is_verified=True,
        )
        self.create_subscription(user)

        self.assertTrue(self.client.login(username=user.username, password=user_password))

        invalid_names = [
            '',
            129 * 'y',
        ]

        for name in invalid_names:
            response = self.client.post(
                path='/v1/organizations',
                data={
                    'name': name,
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
            email='test@test.test',
            is_verified=True,
        )
        self.create_subscription(user)

        self.assertTrue(self.client.login(username=user.username, password=user_password))

        name = 'name'

        response = self.client.post(
            path='/v1/organizations',
            data={
                'name': 'name',
            },
            content_type='application/json',
        )

        self.assertTrue(isinstance(response, JSONHttpResponse))
        self.assertEqual(response.status_code, 200)

        response_body = json.loads(response.content.decode('utf-8'))

        created_org = Organization.objects.get(
            id=response_body['data']['id'],
            is_active=True,
        )

        self.assertEqual(created_org.owner.id, user.id)
        self.assertEqual(str(created_org.owner.id), response_body['data']['owner'])
        self.assertEqual(created_org.name, name)
        self.assertEqual(str(created_org.name), response_body['data']['name'])
        self.assertTrue(user in created_org.members.all())
        self.assertEqual(created_org.members.count(), 1)
        self.assertEqual(created_org.apps.count(), 0)

        self.client.logout()

    def test_put_no_org(self):

        user_password = 'amalgam'
        user = User.objects.create_user(
            username='Ionel1234',
            password=user_password,
            is_verified=True,
        )

        self.assertTrue(self.client.login(username=user.username, password=user_password))

        response = self.client.put(
            path='/v1/organizations/{}'.format(str(uuid.uuid4())),
            data={},
        )

        self.assertTrue(isinstance(response, JSONHttpResponse))
        self.assertEqual(response.status_code, 400)
        self.assertEqual(json.loads(response.content), ORGANIZATION_NOT_FOUND)

    def test_put_invalid_body(self):

        self.assertTrue(self.client.login(username=self.user.username, password=self.user_password))

        response = self.client.put(
            path='/v1/organizations/{}'.format(str(self.org.id)),
            data={
                'name': 'ceva',
            }
        )

        self.client.logout()

        self.assertTrue(isinstance(response, JSONHttpResponse))
        self.assertEqual(response.status_code, 400)
        self.assertEqual(json.loads(response.content), UNKNOWN_ERROR)

    def test_put_200_no_change(self):

        self.assertTrue(self.client.login(username=self.user.username, password=self.user_password))

        response = self.client.put(
            path='/v1/organizations/{}'.format(str(self.org.id)),
            data={
                'name': self.org.name,
            },
            content_type='application/json',
        )

        self.client.logout()

        self.assertTrue(isinstance(response, JSONHttpResponse))
        self.assertEqual(response.status_code, 200)

        response_body = json.loads(response.content.decode('utf-8'))

        self.assertEqual(response_body['data']['name'], self.org.name)
        self.assertEqual(response_body['data']['id'], str(self.org.id))

    def test_put_200_change(self):

        self.assertTrue(self.client.login(username=self.user.username, password=self.user_password))

        new_name = 'new_name'

        response = self.client.put(
            path='/v1/organizations/{}'.format(str(self.org.id)),
            data={
                'name': new_name,
            },
            content_type='application/json',
        )

        self.client.logout()

        self.assertTrue(isinstance(response, JSONHttpResponse))
        self.assertEqual(response.status_code, 200)

        response_body = json.loads(response.content.decode('utf-8'))

        changed_org = Organization.objects.get(
            id=self.org.id,
            is_active=True,
        )

        self.assertEqual(response_body['data']['name'], new_name)
        self.assertEqual(response_body['data']['id'], str(self.org.id))
        changed_org.name = new_name

    def test_put_invalid_org_params(self):

        self.assertTrue(self.client.login(username=self.user.username, password=self.user_password))

        initial_save = models.Model.save
        models.Model.save = mock.Mock()

        inputs = (
            (129 * 'y', ),
            ('', ),
        )

        for inp in inputs:
            response = self.client.put(
                path='/v1/organizations/{}'.format(str(self.org.id)),
                data={
                    'name': inp[0],
                },
                content_type='application/json',
            )

            self.assertTrue(isinstance(response, JSONHttpResponse))
            self.assertEqual(response.status_code, 400)
            self.assertEqual(json.loads(response.content), INVALID_PARAMETERS)

        self.assertEqual(models.Model.save.call_count, 0)
        models.Model.save = initial_save

        self.client.logout()

    def test_get_no_org(self):
        self.assertTrue(self.client.login(username=self.user.username, password=self.user_password))

        response = self.client.get(
            path='/v1/organizations/{}'.format(str(uuid.uuid4())),
        )

        self.client.logout()

        self.assertTrue(isinstance(response, JSONHttpResponse))
        self.assertEqual(response.status_code, 400)
        self.assertEqual(json.loads(response.content), ORGANIZATION_NOT_FOUND)

    def test_get_user_not_org(self):
        user_password = 'amalgam'
        user = User.objects.create_user(
            username='Ionel1234',
            password=user_password,
            is_verified=True,
        )

        self.assertTrue(self.client.login(username=user.username, password=user_password))

        response = self.client.get(
            path='/v1/organizations/{}'.format(str(self.org.id)),
        )

        self.client.logout()

        self.assertTrue(isinstance(response, JSONHttpResponse))
        self.assertEqual(response.status_code, 400)
        self.assertEqual(json.loads(response.content), ORGANIZATION_NOT_FOUND)

    def test_get_200(self):
        self.assertTrue(self.client.login(username=self.user.username, password=self.user_password))

        response = self.client.get(
            path='/v1/organizations/{}'.format(str(self.org.id)),
        )

        self.client.logout()

        self.assertTrue(isinstance(response, JSONHttpResponse))
        self.assertEqual(response.status_code, 200)

        self.assertEqual(
            json.loads(response.content.decode('utf-8')),
            serialize(
                [self.org],
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
            path='/v1/organizations',
        )

        self.client.logout()

        self.assertTrue(isinstance(response, JSONHttpResponse))
        self.assertEqual(response.status_code, 200)

        response_body = json.loads(response.content.decode('utf-8'))
        self.assertEqual(response_body['data'], [])

    def test_filter_200(self):
        self.assertTrue(self.client.login(username=self.user.username, password=self.user_password))

        response = self.client.get(
            path='/v1/organizations',
        )

        self.client.logout()

        self.assertTrue(isinstance(response, JSONHttpResponse))
        self.assertEqual(response.status_code, 200)

        apps = [self.org]

        self.assertEqual(
            json.loads(response.content.decode('utf-8')),
            serialize(
                apps,
            ),
        )

    def test_delete_no_pk(self):
        self.assertTrue(self.client.login(username=self.user.username, password=self.user_password))

        response = self.client.delete(
            path='/v1/organizations',
        )

        self.client.logout()

        self.assertTrue(isinstance(response, JSONHttpResponse))
        self.assertEqual(response.status_code, 400)
        self.assertEqual(json.loads(response.content), MISSING_PARAMETERS)

    def test_delete_no_org(self):
        self.assertTrue(self.client.login(username=self.user.username, password=self.user_password))

        response = self.client.delete(
            path='/v1/organizations/{}'.format(str(uuid.uuid4())),
        )

        self.client.logout()

        self.assertTrue(isinstance(response, JSONHttpResponse))
        self.assertEqual(response.status_code, 400)
        self.assertEqual(json.loads(response.content), ORGANIZATION_NOT_FOUND)

    def test_delete_user_not_in_org(self):
        user_password = 'amalgam'
        user = User.objects.create_user(
            username='Ionel1234',
            password=user_password,
            is_verified=True,
        )

        self.assertTrue(self.client.login(username=user.username, password=user_password))

        response = self.client.delete(
            path='/v1/organizations/{}'.format(str(self.org.id)),
        )

        self.client.logout()

        self.assertTrue(isinstance(response, JSONHttpResponse))
        self.assertEqual(response.status_code, 400)
        self.assertEqual(json.loads(response.content), ORGANIZATION_NOT_FOUND)

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

        org = Organization(
            name='testdelete',
            owner=user,
        )

        org.members.add(user)
        org.members.add(user2)

        org.save()

        self.assertTrue(self.client.login(username=user2.username, password=user2_password))

        response = self.client.delete(
            path='/v1/organizations/{}'.format(str(org.id)),
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

        org = Organization(
            name='testdelete',
            owner=user,
        )

        org.members.add(user)
        org.members.add(user2)

        org.save()

        self.assertTrue(self.client.login(username=user.username, password=user_password))

        response = self.client.delete(
            path='/v1/organizations/{}'.format(str(org.id)),
        )

        self.client.logout()

        self.assertTrue(isinstance(response, JSONHttpResponse))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(json.loads(response.content), '')

        inactive_org = Organization.objects.get(id=org.id)

        self.assertEqual(inactive_org.is_active, False)
