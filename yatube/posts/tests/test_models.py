from django.contrib.auth import get_user_model
from django.test import TestCase

from ..models import Group, Post

User = get_user_model()


class PostModelTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='user')
        cls.post = Post.objects.create(
            author=cls.user,
            text='Текст',
        )
        cls.group = Group.objects.create(
            title='Тестовый заголовок',
            slug='test-slug',
            description='Тестовое описание'
        )

    def test_models_correct_object_names(self):
        """Проверка корректной работы __str__"""
        expected_group_name = self.group.title
        expected_post_name = self.post.text[:15]
        self.assertEqual(expected_group_name, str(self.group))
        self.assertEqual(expected_post_name, str(self.post))

    def test_correct_verbose_name(self):
        """Проверка verbose_name"""
        post_field_verboses = {
            'author': 'Автор',
            'group': 'Группа',
            'image': 'Картинка'
        }
        group_field_verboses = {
            'title': 'Название',
            'slug': 'Адрес страницы группы',
            'description': 'Описание'
        }
        all_verboses_fields = {
            self.post: post_field_verboses,
            self.group: group_field_verboses,
        }
        for object_model, all_verboses_field in all_verboses_fields.items():
            for field, expected_value in all_verboses_field.items():
                with self.subTest(object=object_model, field=field):
                    self.assertEqual(
                        object_model
                        ._meta
                        .get_field(field)
                        .verbose_name,
                        expected_value
                    )
