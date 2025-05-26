from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from accounts.tests import BaseTestCase
from .models import Exercise, Article


class ChildExerciseTests(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.exercise = Exercise.objects.create(
            child=self.child_profile,
            requested_text="test"
        )

    def test_exercise_generation(self):
        url = reverse("exercise_generation")
        self.client.force_authenticate(user=self.child_user)
        response = self.client.post(url, format="json")
        # it already has an exercise - it should return 200 OK with the same exercise
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # check if the response has the same exercise id as the one created
        self.assertEqual(response.data["id"], self.exercise.id)
    
    def test_exercise_refresh(self):
        url = reverse("exercise_retrieve_delete", args=[self.exercise.id])
        self.client.force_authenticate(user=self.child_user)
        # delete the current exercise
        response = self.client.delete(url, format="json")
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        # check if the exercise is deleted
        self.assertFalse(Exercise.objects.filter(id=self.exercise.id).exists())
        # request a new exercise
        url = reverse("exercise_generation")
        response = self.client.post(url, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        # check if the new exercise is created
        self.assertTrue(Exercise.objects.filter(id=response.data["id"]).exists())
        # check if the new exercise is not the same as the old one
        self.assertNotEqual(response.data["id"], self.exercise.id)

class AdultExerciseReviewTests(BaseTestCase):
    def setUp(self):
        super().setUp() 
        self.submitted_exercise = Exercise.objects.create(
            child=self.child_profile,
            requested_text="submitted_exercise",
            submission_date = timezone.now()
        )
        self.unsubmitted_exercise = Exercise.objects.create(
            child=self.child_profile,
            requested_text="unsubmitted_exercise",
            submission_date = None
        )


    def test_submissions_list(self):
        url = reverse("submission_list_of_child", args=[self.child_user.id])
        self.client.force_authenticate(user=self.adult_user)
        response = self.client.get(url, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["id"], self.submitted_exercise.id)

    def test_get_exercise(self):
        url = reverse("exercise_retrieve_delete", args=[self.unsubmitted_exercise.id])
        self.client.force_authenticate(user=self.adult_user)
        response = self.client.get(url, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["id"], self.unsubmitted_exercise.id)

class ArticleTests(BaseTestCase):
    def setUp(self):
        super().setUp()  # call the parent setUp method to initialize the base test case
        self.article = Article.objects.create(title="Test Article", description="Test Description", link="http://test.com")

    def test_article_list(self):
        url = reverse("articles_list")
        self.client.force_authenticate(user=self.adult_user)
        response = self.client.get(url, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

