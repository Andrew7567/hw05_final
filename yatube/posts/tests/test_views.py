from yatube.settings import POSTS_ON_PAGE
from django import forms
from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse
from django.core.cache import cache

from posts.forms import PostForm
from posts.models import Group, Post, Follow

User = get_user_model()


class BaseViewsTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='Andrew1')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test-slug',
            description='Тестовое описание',
        )
        cls.post = Post.objects.create(
            text='Тестовый заголовок',
            author=cls.user,
            group=cls.group
        )
        cls.group_check = Group.objects.create(
            title='Проверочная группа',
            slug='checkslug',
            description='Проверочное описание'
        )
        cls.templates_pages_names = {
            reverse('posts:index'): 'posts/index.html',
            reverse('posts:group_list', kwargs={
                'slug': cls.group.slug
            }): 'posts/group_list.html',
            reverse('posts:profile', kwargs={
                'username': cls.user
            }): 'posts/profile.html',
            reverse('posts:post_detail', kwargs={
                'post_id': cls.post.pk
            }): 'posts/post_detail.html',
            reverse('posts:post_create'): 'posts/create_post.html',
            reverse('posts:post_edit', kwargs={
                'post_id': cls.post.pk
            }): 'posts/create_post.html',
        }

    def setUp(self):
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)


class PostPagesTests(BaseViewsTest):
    def test_pages_uses_correct_template(self):
        """URL-адрес использует соответствующий шаблон."""
        cache.clear()
        for reverse_name, template in self.templates_pages_names.items():
            with self.subTest(reverse_name=reverse_name):
                response = self.authorized_client.get(reverse_name)
                self.assertTemplateUsed(response, template)

    def test_index_page_show_correct_context(self):
        cache.clear()
        response = self.authorized_client.get(reverse('posts:index'))
        test_object = response.context['page_obj'][0]
        self.assertEqual(test_object, self.post)

    def _test_context(self):
        response = self.authorized_client.get(
            reverse(
                'posts:group_list',
                kwargs={'slug': self.group.slug}
            )
        )
        test_object = response.context['page_obj'][0]
        test_title = test_object.group.title
        test_author = test_object.author
        test_text = test_object.text
        test_group = test_object.group
        test_description = test_object.group.description
        self.assertEqual(test_object, self.post)
        self.assertEqual(test_title, test_object.group.title)
        self.assertEqual(test_author, self.user)
        self.assertEqual(test_text, test_object.text)
        self.assertEqual(test_group, self.group)
        self.assertEqual(test_description, test_object.group.description)

    def test_group_list_show_correct_context(self):
        self._test_context()

    def test_profile_show_correct_context(self):
        response = self.authorized_client.get(
            reverse('posts:profile', kwargs={'username': self.user.username})
        )
        test_object = response.context['page_obj'][0]
        test_sum_of_posts = test_object.author.posts.all().count()
        self._test_context
        self.assertEqual(test_sum_of_posts, len(self.user.posts.all()))

    def test_post_detail_show_correct_context(self):
        response = self.client.get(reverse(
            'posts:post_detail',
            kwargs={'post_id': self.post.id})
        )
        test_sum_of_posts = response.context.get(
            'post').author.posts.all().count()
        self._test_context
        self.assertEqual(test_sum_of_posts, len(self.user.posts.all()))

    def test_create_post_correct_context(self):
        response = self.authorized_client.get(reverse('posts:post_create'))
        self.assertIsInstance(response.context.get('form'), PostForm)
        form_fields = {
            'text': forms.fields.CharField,
            'group': forms.models.ModelChoiceField,
        }
        for value, expected in form_fields.items():
            with self.subTest(value=value):
                form_field = response.context.get('form').fields.get(value)
                self.assertIsInstance(form_field, expected)

    def test_post_edit_page_show_correct_context(self):
        response = (self.authorized_client.get(
            reverse('posts:post_edit', kwargs={'post_id': self.post.id}))
        )
        self.assertIsInstance(response.context.get('form'), PostForm)
        form_fields = {
            'text': forms.fields.CharField,
            'group': forms.models.ModelChoiceField,
        }
        for value, expected in form_fields.items():
            with self.subTest(value=value):
                form_field = response.context.get('form').fields.get(value)
                self.assertIsInstance(form_field, expected)
        is_edit = response.context['is_edit']
        self.assertTrue(is_edit)
        self.assertIsInstance(is_edit, bool)

    def test_post_appears_in_3_pages(self):
        """
        Проверяем, что при создании поста с группой, этот пост появляется:
        на главной странице сайта, на странице выбранной группы,
        в профайле пользователя. """
        # Проверяем, что первый элемент списка на главной странице сайта -
        # это созданный нами пост:
        cache.clear()
        response = self.authorized_client.get(reverse('posts:index'))
        object_on_main_site = response.context['page_obj'][0]
        self.assertEqual(object_on_main_site, self.post)
        # Проверяем, что первый элемент списка на странице группы -
        # это созданный нами пост:
        response = self.authorized_client.get(
            reverse('posts:group_list', kwargs={'slug': self.group.slug})
        )
        test_object = response.context['page_obj'][0]
        test_group = test_object.group
        self_post = self.post
        self_group = self.group

        # Проверяем, что первый элемент списка в профайле пользователя -
        # это созданный нами пост:
        response = self.authorized_client.get(
            reverse('posts:profile', kwargs={'username': self.user.username})
        )
        test_andrew = response.context['page_obj'][0]
        self.assertEqual(test_object, self.post)

        # Создаем словарь с элементами страницы(ключ)
        # и ожидаемым контекстом (значение):
        context_matching = {
            test_object: self_post,
            test_group: self_group,
            test_andrew: self.post
        }
        for element, names in context_matching.items():
            with self.subTest(element=element):
                self.assertEqual(element, names)

    def test_post_not_found(self):
        """ Проверяем, что пост не попал на странице группы,
        для которой он не был предназначен """
        response = self.authorized_client.get(
            reverse(
                'posts:group_list',
                kwargs={'slug': self.group_check.slug}
            )
        )
        context = response.context['page_obj'].object_list
        self.assertNotIn(self.post, context)


class PaginatorViewsTest(BaseViewsTest):
    def setUp(self):
        super().setUp()
        batch_size = 13
        posts = (Post(
            text='Пост № %s' % i,
            author=self.user,
            group=self.group) for i in range(batch_size)
        )
        Post.objects.bulk_create(posts)

    def test_six_pages_contains_records(self):
        cache.clear()
        list_pages = list(self.templates_pages_names.keys())
        have_paginator = list_pages[:3]
        all_cnt = Post.objects.count()
        for i in have_paginator:
            response = self.authorized_client.get(i)
            len_post = len(response.context['page_obj'])
            self.assertEqual(len_post, POSTS_ON_PAGE)
        for i in have_paginator:
            response = self.authorized_client.get(i + '?page=2')
            len_post = len(response.context['page_obj'])
            self.assertEqual(len_post, all_cnt - POSTS_ON_PAGE)


class CacheTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.user = User.objects.create_user(username='Nemo')
        cls.post_cache = Post.objects.create(
            author=cls.user,
            text='Тест кеш',
        )

    def setUp(self):
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)

    def test_cache_index(self):
        """Тест кеша главной страницы."""
        response = self.authorized_client.get(
            reverse('posts:index')).content
        self.post_cache.delete()
        response_cache = self.authorized_client.get(
            reverse('posts:index')).content
        self.assertEqual(response, response_cache)
        cache.clear()
        response_clear = self.authorized_client.get(
            reverse('posts:index')).content
        self.assertNotEqual(response, response_clear)


class FollowTests(TestCase):
    @classmethod
    def follow_test(self):
        first_follow = Follow.objects.first()
        follow_count = Follow.objects.count()
        self.follower = Client()
        self.follower.get(reverse('posts:profile_follow',
                                kwargs={'username': self.user}))
        Follow.objects.create(user=self.user, author=self.author)
        self.assertEqual(follow_count + 1, Follow.objects.count)
        self.assertEqual(first_follow.user, self.user)
        self.assertEqual(first_follow.author, self.author)

    def unfollow_test(self):
        follow_count = Follow.objects.count()
        self.follower = Client()
        self.follower.get(reverse('posts:profile_follow',
                                kwargs={'username': self.user}))
        self.follower.get(reverse('posts:profile_unfollow',
                                kwargs={'username': self.user}))
        self.assertFalse(Follow.objects.filter(user=self.user,
                                               author=self.author).exists())
        self.assertEqual(follow_count - 1, Follow.objects.count)

    def follow_post(self):
        Follow.objects.create(user=self.user, author=self.author)
        post = Post.objects.create(
            author=self.author,
            text='Тестовый текст'
        )
        response = self.user.get(reverse('posts:follow_index'))
        post_1 = response.context['page_obj'][0]
        self.assertEqual(post_1, post)

    def unfollow_post(self):
        Follow.objects.create(user=self.user, author=self.author)
        self.authorized_client.get(reverse('posts:profile_unfollow',
                                           kwargs={'username': self.user}))
        post = Post.objects.create(
            author=self.author,
            text='Тестовый текст'
        )
        response = self.user.get(reverse('posts:follow_index'))
        post_1 = response.context['page_obj'][0]
        self.assertNotEqual(post_1, post)
