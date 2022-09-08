import graphene

from graphql_jwt.shortcuts import create_refresh_token, get_refresh_token
from graphql_jwt.utils import get_payload

from ..context_managers import back_to_the_future, refresh_expired
from ..decorators import override_jwt_settings


class RefreshTokenMutationMixin:

    @override_jwt_settings(JWT_LONG_RUNNING_REFRESH_TOKEN=True)
    def setUp(self):
        self.Mutation = type('jwt', (graphene.ObjectType,), {
            name: mutation.Field() for name, mutation in
            self.refresh_token_mutations.items()
        })
        super().setUp()


class TokenAuthMixin(RefreshTokenMutationMixin):

    @override_jwt_settings(JWT_LONG_RUNNING_REFRESH_TOKEN=True)
    def test_token_auth(self):
        response = self.execute({
            self.user.USERNAME_FIELD: self.user.get_username(),
            'password': 'dolphins',
        })

        data = response.data['tokenAuth']
        payload = get_payload(data['token'])
        refresh_token = get_refresh_token(data['refreshToken'])

        self.assertUsernameIn(payload)
        self.assertEqual(refresh_token.user, self.user)


class RefreshTokenMixin:

    def setUp(self):
        super().setUp()
        self.refresh_token = create_refresh_token(self.user)


class RefreshMixin(RefreshTokenMutationMixin, RefreshTokenMixin):

    def test_refresh_token(self):
        with back_to_the_future(seconds=1):
            response = self.execute({
                'refreshToken': self.refresh_token.token,
            })

        data = response.data['refreshToken']
        token = data['token']
        refresh_token = get_refresh_token(data['refreshToken'])
        payload = get_payload(token)

        self.assertUsernameIn(payload)
        self.assertNotEqual(token, self.token)
        self.assertGreater(payload['exp'], self.payload['exp'])

        self.assertNotEqual(refresh_token.token, self.refresh_token.token)
        self.assertEqual(refresh_token.user, self.user)
        self.assertGreater(refresh_token.created, self.refresh_token.created)

    def test_refresh_token_expired(self):
        with refresh_expired():
            response = self.execute({
                'refreshToken': self.refresh_token.token,
            })

        self.assertIsNotNone(response.errors)


class RevokeMixin(RefreshTokenMixin):

    def test_revoke(self):
        response = self.execute({
            'refreshToken': self.refresh_token.token,
        })

        self.refresh_token.refresh_from_db()

        self.assertIsNotNone(self.refresh_token.revoked)
        self.assertIsNotNone(response.data['revokeToken']['revoked'])
