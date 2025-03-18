from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase
from rest_framework import status
from accounts.models import AdultProfile, ChildProfile, User
from django.urls import reverse
from rest_framework_simplejwt.tokens import RefreshToken

User = get_user_model()

class UserTests(APITestCase):
    # setUp - runs before each test
    # tests - have to start with test_
    def setUp(self):
        self.adult_user = User.objects.create_user(username="adult", password="test", first_name="Jodsfhn", last_name="Dfsoe", email="sdsa@dfds.com", role=User.Role.ADULT)
        self.adult_profile = AdultProfile.objects.create(user=self.adult_user)
        
        self.child_user = User.objects.create_user(username="child", password="test", first_name="kid", last_name="kiddfsdf", role=User.Role.CHILD)
        self.child_profile = ChildProfile.objects.create(user=self.child_user, guiding_adult=self.adult_profile)
        
        # to be used in the logout test
        self.refresh = RefreshToken.for_user(self.adult_user)

        self.client = self.client_class()

    # test new adult registration
    def test_adult_register(self):
        # reverse - get the url from the name of the view
        url = reverse("adult_register")
        data = {"username": "adult2", "password": "test12345", "first_name": "John", "last_name": "Doe", 
                "email": "ofdf@gffdf.com"}
        response = self.client.post(url, data, format="json")
        
        # assert - check if the response is what we expect
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(User.objects.filter(username="adult2").exists())

    # test new child registration - registered by the adult
    def test_child_register(self):
        # note ModelViewSet - gives default names for each of the urls
        url = reverse("child-list")
        data = {"username": "child2", "password": "test12345", "first_name": "kid", "last_name": "kids"}
        # to authenticate the user
        self.client.force_authenticate(user=self.adult_user)
        response = self.client.post(url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(User.objects.filter(username="child2").exists())

    # test login
    def test_login(self):
        url = reverse("login")
        data = {"username": "adult", "password": "test"}
        response = self.client.post(url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # make sure the response has the access and refresh tokens
        self.assertTrue("access" in response.data)
        self.assertTrue("refresh" in response.data)

    # test logout
    def test_logout(self):
        url = reverse("logout")
        data = {"refresh_token": str(self.refresh)}

        self.client.force_authenticate(user=self.adult_user)
        response = self.client.post(url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_205_RESET_CONTENT)

    # test getting the list of children of an adult
    def test_get_children_list(self):
        url = reverse("child-list")
        
        self.client.force_authenticate(user=self.adult_user)
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # that adult has only one child
        self.assertEqual(len(response.data), 1)
        # that child is the one we created in setUp named "child"
        self.assertEqual(response.data[0]["user"]["username"], "child")

    # test permissions - a child cannot its own list of children
    def test_child_cannot_access_children_list(self):
        url = reverse("child-list")
        
        self.client.force_authenticate(user=self.child_user)
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
