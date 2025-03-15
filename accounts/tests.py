import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status
from accounts.models import AdultProfile, ChildProfile, User
from django.urls import reverse
from rest_framework_simplejwt.tokens import RefreshToken

User = get_user_model()

# pytest-django uses a temporary database for the tests

# fixtures - used by the tests to setup objects for them to use
# they are runed before the tests if they are in its parameters
@pytest.fixture
def api_client():
    return APIClient()

@pytest.fixture
def create_adult_user(db):
    user = User.objects.create_user(username="adult", password="test", role=User.Role.ADULT)
    adult_profile = AdultProfile.objects.create(user=user)
    return user, adult_profile

@pytest.fixture
def create_child_user(db, create_adult_user):
    adult_user, adult_profile = create_adult_user
    user = User.objects.create_user(username="child", password="test", role=User.Role.CHILD)
    child_profile = ChildProfile.objects.create(user=user, guiding_adult=adult_profile)
    return user, child_profile

# pytest.mark.django_db - allow the test to use the database
@pytest.mark.django_db
def test_adult_register(api_client):
    url = reverse("adult-register")
    data = {"username": "new_adult", "password": "test", "role": User.Role.ADULT}
    
    response = api_client.post(url, data, format="json")
    
    # assert - make sure that the response is what we expect
    assert response.status_code == status.HTTP_201_CREATED
    assert User.objects.filter(username="new_adult").exists()


@pytest.mark.django_db
def test_child_register(api_client, create_adult_user):
    adult_user, _ = create_adult_user
    api_client.force_authenticate(user=adult_user)

    url = reverse("children-list") 
    data = {"user": {"username": "child2", "password": "testpass"}, "exercise_language": "en"}

    response = api_client.post(url, data, format="json")

    assert response.status_code == status.HTTP_201_CREATED
    assert User.objects.filter(username="child2").exists()


@pytest.mark.django_db
def test_logout(api_client, create_adult_user):
    user, _ = create_adult_user
    refresh = RefreshToken.for_user(user)

    api_client.force_authenticate(user=user)
    url = reverse("logout")  # Adjust the URL name
    data = {"refresh_token": str(refresh)}

    response = api_client.post(url, data, format="json")

    assert response.status_code == status.HTTP_205_RESET_CONTENT

@pytest.mark.django_db
def test_get_children_list(api_client, create_adult_user):
    adult_user, _ = create_adult_user
    api_client.force_authenticate(user=adult_user)

    url = reverse("children-list")  # Adjust the URL name
    response = api_client.get(url)

    assert response.status_code == status.HTTP_200_OK
    assert len(response.data) == 1
    assert response.data[0]["user"]["username"] == "child1"



@pytest.mark.django_db
def test_child_cannot_access_children_list(api_client, create_child_user):
    """Test that a child user cannot view the list of children"""
    child_user, _ = create_child_user
    api_client.force_authenticate(user=child_user)

    url = reverse("children-list")  # Adjust the URL name
    response = api_client.get(url)

    assert response.status_code == status.HTTP_403_FORBIDDEN
