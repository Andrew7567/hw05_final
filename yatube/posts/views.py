from django.shortcuts import render, get_object_or_404, redirect
from django.core.paginator import Paginator
from django.contrib.auth.decorators import login_required
from django.views.decorators.cache import cache_page

from yatube.settings import POSTS_ON_PAGE
from .models import get_user_model
from .models import Group
from .models import User
from .models import Post
from .models import Follow
from .forms import PostForm, CommentForm


def paginate(request, post_list):
    paginator = Paginator(post_list, POSTS_ON_PAGE)
    page_number = request.GET.get('page')
    return paginator.get_page(page_number)


@cache_page(60 * 15)
def index(request):
    post_list = Post.objects.order_by('-pub_date')
    page_obj = paginate(request, post_list)
    template = 'posts/index.html'
    context = {
        'page_obj': page_obj,
        'posts': page_obj.object_list
    }
    return render(request, template, context)


def group_posts(request, slug):
    template = 'posts/group_list.html'
    group = get_object_or_404(Group, slug=slug)
    post_list = group.posts.all()
    page_obj = paginate(request, post_list)
    context = {
        'group': group,
        'posts': page_obj.object_list,
        'page_obj': page_obj
    }
    return render(request, template, context)


def profile(request, username):
    template = 'posts/profile.html'
    author = get_user_model()
    user = get_object_or_404(author, username=username)
    posts = user.posts.all()
    page_obj = paginate(request, posts)
    count_posts = posts.count()
    follows = Follow.objects.filter(user=request.user, author=user).exists()
    # Здесь код запроса к модели и создание словаря контекста
    context = {
        'author': user,
        'posts': page_obj.object_list,
        'page_obj': page_obj,
        'count_posts': count_posts,
        'following': follows
    }
    return render(request, template, context)


def post_detail(request, post_id):
    template = 'posts/post_detail.html'
    post = get_object_or_404(Post, pk=post_id)
    form = CommentForm(request.POST or None)
    comments = post.comments.all()
    if request.method == 'POST':
        return redirect('posts: add_comment')
    author = post.author
    author_posts = author.posts
    count_posts = author_posts.count()
    context = {
        'author': author,
        'title': post.text,
        'post': post,
        'count_posts': count_posts,
        'form': form,
        'comments': comments,
    }
    return render(request, template, context)


@login_required()
def post_create(request):
    is_edit = False
    template = 'posts/create_post.html'
    form = PostForm(request.POST or None, files=request.FILES or None)
    if form.is_valid():
        post = form.save(commit=False)
        post.author = request.user
        post.save()
        return redirect('posts:profile', username=request.user.username)
    context = {
        'form': form,
        'is_edit': is_edit
    }
    return render(request, template, context)


@login_required()
def post_edit(request, post_id):
    post = get_object_or_404(Post, pk=post_id)
    is_edit = True
    template = 'posts/create_post.html'
    if request.user == post.author:
        form = PostForm(
            request.POST or None, files=request.FILES or None, instance=post
        )
        if form.is_valid():
            form.save()
            return redirect('posts:post_detail', post_id=post_id)
    context = {
        'post_id': post_id,
        'form': form,
        'is_edit': is_edit
    }
    return render(request, template, context)


@login_required
def add_comment(request, post_id):
    # Получите пост
    form = CommentForm(request.POST or None)
    if form.is_valid():
        comment = form.save(commit=False)
        comment.author = request.user
        comment.post = get_object_or_404(Post, pk=post_id)
        comment.save()
    return redirect('posts:post_detail', post_id=post_id)


@login_required
def follow_index(request):
    posts = Post.objects.filter(author__following__user=request.user)
    page_obj = paginate(request, posts)
    context = {
        'page_obj': page_obj,
        'posts': posts
    }
    return render(request, 'posts/follow.html', context)


@login_required
def profile_follow(request, username):
    user = request.user
    author = get_object_or_404(User, username=username)
    if author != user:
        Follow.objects.get_or_create(user=user, author=author)
    return redirect('posts:follow_index')


@login_required
def profile_unfollow(request, username):
    user = request.user
    Follow.objects.get(user=user, author__username=username).delete()
    return redirect('posts:follow_index')
