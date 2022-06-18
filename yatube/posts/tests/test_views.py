from django import forms
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from posts.models import Follow, Group, Post

User = get_user_model()


@override_settings()
class PostPagesTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='user')
        cls.group = Group.objects.create(
            title='Тестовый заголовок',
            slug='test-slug',
            description='Тестовое описание'
        )
        cls.group_without_posts = Group.objects.create(
            title='Тестовый заголовок',
            slug='test-slug_2',
            description='Тестовое описание'
        )
        small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x02\x00'
            b'\x01\x00\x80\x00\x00\x00\x00\x00'
            b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
            b'\x00\x00\x00\x2C\x00\x00\x00\x00'
            b'\x02\x00\x01\x00\x00\x02\x02\x0C'
            b'\x0A\x00\x3B'
        )
        uploaded = SimpleUploadedFile(
            name='small.gif',
            content=small_gif,
            content_type='image/gif'
        )
        cls.post = Post.objects.create(
            author=cls.user,
            text='Текст',
            group=cls.group,
            image=uploaded
        )

    def setUp(self):
        self.guest_client = Client()
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)

    def check_post(self, post):
        self.assertEqual(post.text, self.post.text)
        self.assertEqual(post.author, self.post.author)
        self.assertEqual(post.group, self.post.group)
        self.assertEqual(post.image, self.post.image)

    def test_index_correct_context(self):
        """Проверка корректного контекста у главной страницы"""
        response = self.authorized_client.get(reverse('posts:index'))
        self.check_post(response.context['page_obj'][0])

    def test_group_posts_correct_context(self):
        """Проверка корректного контекста у страницы с постами группы"""
        response = self.authorized_client.get(
            reverse(
                'posts:group_list',
                kwargs={'slug': self.group.slug}
            )
        )
        self.assertEqual(response.context['group'], self.group)

    def test_post_another_group(self):
        """Пост не попал в неправильную группу"""
        response = self.authorized_client.get(
            reverse(
                'posts:group_list',
                kwargs={'slug': self.group_without_posts.slug}
            )
        )
        self.assertNotIn(self.post, response.context['page_obj'])

    def test_post_detail_correct_context(self):
        """Проверка корректного контекста у страницы поста"""
        response = self.authorized_client.get(
            reverse(
                'posts:post_detail', kwargs={'post_id': self.post.id}
            )
        )
        self.check_post(response.context['post'])

    def test_post_edit_correct_context(self):
        """Проверка корректного контекста у страницы редактирования поста"""
        response = self.authorized_client.get(
            reverse(
                'posts:post_edit',
                kwargs={'post_id': self.post.id}
            )
        )
        form_fields = {
            'text': forms.fields.CharField,
            'group': forms.fields.ChoiceField
        }
        for field, expected_value in form_fields.items():
            with self.subTest(field=field):
                form_field = response.context.get('form').fields.get(field)
                self.assertIsInstance(form_field, expected_value)

    def test_post_create_correct_context(self):
        """Проверка корректного контекста у страницы создания нового поста"""
        response = self.authorized_client.get(
            reverse('posts:post_create')
        )
        form_fields = {
            'text': forms.fields.CharField,
            'group': forms.fields.ChoiceField
        }
        for field, expected_value in form_fields.items():
            with self.subTest(field=field):
                form_field = response.context.get('form').fields.get(field)
                self.assertIsInstance(form_field, expected_value)


class PaginatorViewsTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='user')
        cls.group = Group.objects.create(
            title='Тестовый заголовок',
            slug='test-slug',
            description='Тестовое описание',
        )
        Post.objects.bulk_create(
            [
                Post(
                    text=f'Тестовый пост {i}',
                    author=cls.user,
                    group=cls.group) for i in range(13)
            ]
        )

    def setUp(self):
        self.guest_client = Client()
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)

    def test_paginator(self):
        """Проверка количества постов, выводимых на одну страницу"""
        reverse_names = [
            reverse('posts:index'),
            reverse('posts:group_list', kwargs={'slug': self.group.slug}),
            reverse('posts:profile', kwargs={'username': self.user.username}),
        ]
        for name in reverse_names:
            with self.subTest(name=name):
                response = self.authorized_client.get(name)
                self.assertEqual(len(response.context['page_obj']), 10)
                response = self.authorized_client.get((name) + '?page=2')
                self.assertEqual(len(response.context['page_obj']), 3)


class FollowTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='follower')
        cls.author = User.objects.create_user(username='following')
        cls.post = Post.objects.create(
            author=cls.author,
            text='Текст'
        )
        cls.post_follow = Follow.objects.create(
            user=cls.user, author=cls.author
        )

    def setUp(self):
        self.user_follower = Client()
        self.author_following = Client()
        self.user_follower.force_login(self.user)
        self.author_following.force_login(self.author)

    def test_user_follow_author(self):
        """Пользователь может подписаться на автора поста"""
        self.user_follower.get(
            reverse('posts:profile_follow', kwargs={
                'username': self.author.username})
        )
        self.assertEqual(Follow.objects.all().count(), 1)

    def test_user_unfollow_author(self):
        """Пользователь может отписаться от автора поста"""
        self.user_follower.get(
            reverse('posts:profile_unfollow', kwargs={
                'username': self.author.username})
        )
        self.assertEqual(Follow.objects.all().count(), 0)

    def test_following_authors_posts_on_follow_page(self):
        """Новая запись автора появляется в ленте у подписчика"""
        response = self.user_follower.get(reverse('posts:index'))
        post_text = response.context['page_obj'][0]
        self.assertEqual(post_text, self.post)


class CacheTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='user')
        cls.post = Post.objects.create(
            author=cls.user,
            text='Текст'
        )

    def setUp(self):
        self.guest_client = Client()
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)

    def test_cache_index(self):
        """Проверка работы кэша"""
        first_entry = self.authorized_client.get(reverse('posts:index'))
        Post.objects.get(pk=1).save()
        second_entry = self.authorized_client.get(reverse('posts:index'))
        self.assertEqual(first_entry.content, second_entry.content)
        cache.clear()
        third_entry = self.authorized_client.get(reverse('posts:index'))
        self.assertNotEqual(first_entry.content, third_entry.content)
        cache.clear()
