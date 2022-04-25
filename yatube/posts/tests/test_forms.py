from http import HTTPStatus

import shutil
import tempfile
from django.contrib.auth import get_user_model
from django.conf import settings
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile

from posts.models import Group, Post, Comment

TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)
User = get_user_model()


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostFormTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='TestUser')
        cls.author = User.objects.create_user(username='Andrew')
        cls.group = Group.objects.create(
            title='Тестовое название группы',
            slug='testslug'
        )
        cls.post = Post.objects.create(
            text='Тестовый пост',
            author=cls.author,
            group=cls.group,
        )

    def setUp(self):
        self.guest_client = Client()
        self.authorized_client = Client()
        self.authorized_client.force_login(self.author)

    def test_create_post(self):
        """Валидная форма создает запись в БД."""
        cache.clear()
        small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x02\x00'
            b'\x01\x00\x80\x00\x00\x00\x00\x00'
            b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
            b'\x00\x00\x00\x2C\x00\x00\x00\x00'
            b'\x02\x00\x01\x00\x00\x02\x02\x0C'
            b'\x0A\x00\x3B'
        )

        # загружаем изображение
        uploaded = SimpleUploadedFile(
            name='posts/small.gif',
            content=small_gif,
            content_type='image/gif'
        )
        posts_count = Post.objects.count()
        form_data = {
            'group': self.group.id,
            'text': self.post.text,
            'image': uploaded
        }
        response = self.authorized_client.post(
            reverse('posts:post_create'),
            data=form_data,
            follow=True
        )
        self.assertRedirects(
            response, reverse(
                'posts:profile',
                kwargs={'username': self.author.username})
        )
        first_post = Post.objects.first()
        self.assertEqual(Post.objects.count(), posts_count + 1)
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(first_post.group.id, form_data['group'])
        self.assertEqual(first_post.text, form_data['text'])
        self.assertEqual(first_post.author, self.author)
        self.assertEqual(str(first_post.image), 'posts/small.gif')

    def test_unauthorised_user_post(self):
        posts_count = Post.objects.count()
        response = self.guest_client.post(
            reverse('posts:post_create'))
        self.assertRedirects(
            response, reverse('users:login') + '?next=' + reverse
            ('posts:post_create'),)
        self.assertEqual(Post.objects.count(), posts_count)

    def test_edit(self):
        posts_count = Post.objects.count()
        small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x02\x00'
            b'\x01\x00\x80\x00\x00\x00\x00\x00'
            b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
            b'\x00\x00\x00\x2C\x00\x00\x00\x00'
            b'\x02\x00\x01\x00\x00\x02\x02\x0C'
            b'\x0A\x00\x3B'
        )

        # загружаем изображение
        uploaded = SimpleUploadedFile(
            name='posts/small1.gif',
            content=small_gif,
            content_type='image/gif'
        )
        form_data = {
            'text': self.post.text,
            'group': self.group.id,
            'image': uploaded
        }
        response = self.authorized_client.post(
            reverse('posts:post_edit', kwargs={'post_id': self.post.pk}),
            data=form_data,
            follow=True
        )
        self.assertEqual(Post.objects.count(), posts_count)
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertRedirects(
            response, reverse(
                'posts:post_detail',
                kwargs={'post_id': self.post.pk})
        )
        post = Post.objects.latest('id')
        self.assertEqual(post.text, form_data['text'])
        self.assertEqual(post.group.id, form_data['group'])

    def test_post_page_show_correct_context(self):
        """Проверка передачи через context поста с image для post_detail."""
        small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x02\x00'
            b'\x01\x00\x80\x00\x00\x00\x00\x00'
            b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
            b'\x00\x00\x00\x2C\x00\x00\x00\x00'
            b'\x02\x00\x01\x00\x00\x02\x02\x0C'
            b'\x0A\x00\x3B'
        )

        # загружаем изображение
        uploaded = SimpleUploadedFile(
            name='posts/small2.gif',
            content=small_gif,
            content_type='image/gif'
        )
        form_data = {
            'text': self.post.text,
            'group': self.group.id,
            'image': uploaded
        }
        response = self.authorized_client.post(
            reverse('posts:post_edit', kwargs={'post_id': self.post.pk}),
            data=form_data,
            follow=True
        )
        url = reverse('posts:post_detail', kwargs={'post_id': self.post.pk})
        response = self.authorized_client.get(url)
        context = response.context['post'].image
        self.assertEqual(context, 'posts/small2.gif')

    def test_create_comment(self):
        """Валидная форма создает запись в БД."""
        comments_count = Comment.objects.count()
        form_data = {
            'text': 'Текст',
        }
        response = self.authorized_client.post(
            reverse('posts:add_comment', kwargs={'post_id': self.post.pk}),
            data=form_data,
            follow=True
        )
        self.assertRedirects(
            response, reverse(
                'posts:post_detail',
                kwargs={'post_id': self.post.pk})
        )
        first_comment = Comment.objects.first()
        self.assertEqual(Comment.objects.count(), comments_count + 1)
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(first_comment.text, form_data['text'])
        self.assertEqual(first_comment.author, self.author)

    def test_unauthorised_user_comment(self):
        comments_count = Comment.objects.count()
        response = self.guest_client.post(
            reverse('posts:add_comment', kwargs={'post_id': self.post.id}))
        self.assertRedirects(
            response, reverse('users:login') + '?next=' + reverse
            ('posts:add_comment', kwargs={'post_id': self.post.id}),)
        self.assertEqual(Comment.objects.count(), comments_count)

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)
