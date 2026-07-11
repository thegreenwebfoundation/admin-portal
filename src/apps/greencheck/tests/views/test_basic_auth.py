import pytest
import base64


class TestBasicAuth:
    def test_challenge_presented_when_basicauth_active(self, db, settings, client):
        """
        Check that when we want basicauth on, it keeps away prying eyes
        """
        settings.BASICAUTH_DISABLE = False
        response = client.get("/", follow=True)
        assert response.status_code == 401

    def test_challenge_not_presented_when_basicauth_disabled(
        self, db, settings, client
    ):
        """
        Check that when we want basicauth off, it lets requests through
        """
        settings.BASICAUTH_DISABLE = True
        response = client.get("/", follow=True)
        assert response.status_code == 200

    def test_getting_past_with_correct_credentials(self, db, settings, client):
        """
        Check that we can get past the basicauth challenge if we
        have correct credentials
        """
        settings.BASICAUTH_DISABLE = False
        headers = {
            "HTTP_AUTHORIZATION": "Basic "
            + base64.b64encode(b"staging_user:strong_password").decode("ascii")
        }
        response = client.get("/", follow=True, **headers)
        assert response.status_code == 200
